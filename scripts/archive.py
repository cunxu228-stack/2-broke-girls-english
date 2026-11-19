"""Append one validated lesson to the static archive."""
import json
import re
import sys
from pathlib import Path

FIELDS = ("term", "category", "meaning", "context", "example")
START = '<script id="weekly-lessons" type="application/json">'
END = '</script>'


def archive(page, raw):
    if len(raw) > 30000:
        raise ValueError("Lesson exceeds 30,000 bytes")
    lesson = json.loads(raw)
    if not isinstance(lesson, dict) or set(lesson) != {"episode", "title", "cards"}:
        raise ValueError("Expected episode, title and cards")
    episode, title, cards = (lesson[key] for key in ("episode", "title", "cards"))
    if not isinstance(episode, str) or not re.fullmatch(r"S0[1-6]E(?:0[1-9]|1[0-9]|2[0-4])", episode):
        raise ValueError("Invalid episode")
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError("Invalid title")
    if not isinstance(cards, list) or not 1 <= len(cards) <= 40:
        raise ValueError("Expected 1 to 40 cards")
    terms = set()
    for card in cards:
        if not isinstance(card, dict) or set(card) != set(FIELDS):
            raise ValueError("Invalid card fields")
        if any(not isinstance(card[key], str) or not card[key].strip() or
               len(card[key]) > (160 if key in ("term", "category") else 1200) for key in FIELDS):
            raise ValueError("Invalid card text")
        term = card["term"].strip().casefold()
        if term in terms:
            raise ValueError("Duplicate term in lesson")
        terms.add(term)
    prefix, payload = page.split(START, 1)
    previous, suffix = payload.split(END, 1)
    lessons = json.loads(previous)
    if episode == "S01E01":
        raise ValueError("Pilot is already archived")
    for existing in lessons:
        if existing["episode"] == episode:
            if existing == lesson:
                return page
            raise ValueError("Episode already exists with different content")
    lessons.append(lesson)
    lessons.sort(key=lambda item: item["episode"])
    safe_json = json.dumps(lessons, ensure_ascii=False, indent=2).replace("<", r"\u003c")
    return prefix + START + "\n" + safe_json + "\n" + END + suffix


if __name__ == "__main__":
    page_path = Path(__file__).resolve().parents[1] / "index.html"
    try:
        page = page_path.read_text(encoding="utf-8")
        updated = archive(page, sys.stdin.buffer.read(30001))
    except (ValueError, RecursionError):
        sys.exit("Lesson rejected. Check the JSON structure, lengths and episode number.")
    if updated != page:
        page_path.write_text(updated, encoding="utf-8")
