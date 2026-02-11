#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import requests

BASE_DIR = Path(__file__).resolve().parents[0]
STATE_PATH = BASE_DIR / "state.json"
DB_ID_PATH = BASE_DIR / ".notion_db_id"
ENV_PATH = BASE_DIR / ".env"

NOTION_VERSION = "2022-06-28"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def read_state() -> Dict:
    if not STATE_PATH.exists():
        return {"last_seen_ts": 0}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"last_seen_ts": 0}


def write_state(state: Dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def normalize_notion_id(value: str) -> str:
    return value.replace("-", "").strip()


def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def ensure_database(token: str, parent_page_id: str) -> str:
    env_db_id = os.environ.get("NOTION_DB_ID", "").strip()
    if env_db_id:
        return env_db_id
    if DB_ID_PATH.exists():
        saved = DB_ID_PATH.read_text().strip()
        if saved:
            return saved

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "LeetCode Solves"}}],
        "properties": {
            "No.": {"number": {}},
            "Name": {"title": {}},
            "Link": {"url": {}},
            "Difficulty Level": {"select": {"options": [
                {"name": "Easy"},
                {"name": "Medium"},
                {"name": "Hard"},
            ]}},
            "Topic": {"multi_select": {}},
            "Question ID": {"number": {}},
            "Last Solved": {"date": {}},
        },
    }

    resp = requests.post(
        "https://api.notion.com/v1/databases",
        headers=notion_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"Failed to create database: {resp.status_code} {resp.text}")

    db_id = resp.json().get("id")
    if not db_id:
        raise SystemExit("Notion did not return a database id")

    DB_ID_PATH.write_text(db_id)
    return db_id


def notion_query_page_by_question_id(token: str, db_id: str, question_id: int):
    payload = {
        "filter": {
            "property": "Question ID",
            "number": {"equals": question_id},
        }
    }
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=notion_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"Notion query failed: {resp.status_code} {resp.text}")
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    return results[0]["id"]


def notion_create_page(token: str, db_id: str, properties: Dict):
    payload = {"parent": {"database_id": db_id}, "properties": properties}
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"Notion create failed: {resp.status_code} {resp.text}")


def notion_update_page(token: str, page_id: str, properties: Dict):
    payload = {"properties": properties}
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=notion_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 300:
        raise SystemExit(f"Notion update failed: {resp.status_code} {resp.text}")


def lc_session_headers(session_cookie: str, csrf_token: str) -> Dict[str, str]:
    cookie = f"LEETCODE_SESSION={session_cookie}; csrftoken={csrf_token}"
    return {
        "Cookie": cookie,
        "x-csrftoken": csrf_token,
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0",
    }


def fetch_accepted_submissions_since(
    session: requests.Session, last_ts: int
) -> Tuple[Dict[str, int], int]:
    slugs: Dict[str, int] = {}
    max_ts = last_ts
    last_key = ""
    while True:
        url = f"https://leetcode.com/api/submissions/?offset=0&limit=100&lastkey={last_key}"
        resp = session.get(url, timeout=30)
        if resp.status_code >= 300:
            raise SystemExit(f"LeetCode submissions failed: {resp.status_code} {resp.text}")
        data = resp.json()
        for item in data.get("submissions_dump", []):
            try:
                ts = int(item.get("timestamp", 0))
            except Exception:
                ts = 0
            if ts <= last_ts:
                return slugs, max_ts
            if item.get("status_display") == "Accepted":
                slug = item.get("title_slug")
                if slug:
                    slugs[slug] = max(slugs.get(slug, 0), ts)
                    if ts > max_ts:
                        max_ts = ts
        if not data.get("has_next"):
            break
        last_key = data.get("last_key") or ""
        if not last_key:
            break
    return slugs, max_ts


def fetch_question_data(session: requests.Session, slug: str) -> Dict:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
        titleSlug
        difficulty
        topicTags { name slug }
      }
    }
    """
    payload = {"query": query, "variables": {"titleSlug": slug}}
    resp = session.post("https://leetcode.com/graphql", json=payload, timeout=30)
    if resp.status_code >= 300:
        raise SystemExit(f"LeetCode question query failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return data.get("data", {}).get("question") or {}


def build_notion_properties(question: Dict, last_solved_ts: int) -> Dict:
    title = question.get("title") or question.get("titleSlug") or ""
    slug = question.get("titleSlug") or ""
    question_id = int(question.get("questionId") or 0)
    difficulty = question.get("difficulty") or ""
    topics = [t.get("name") for t in question.get("topicTags", []) if t.get("name")]
    url = f"https://leetcode.com/problems/{slug}/" if slug else ""

    props = {
        "No.": {"number": question_id},
        "Name": {"title": [{"text": {"content": title}}]},
        "Link": {"url": url},
        "Difficulty Level": {"select": {"name": difficulty}} if difficulty else {"select": None},
        "Topic": {"multi_select": [{"name": t} for t in topics]},
        "Question ID": {"number": question_id},
    }
    if last_solved_ts:
        dt = datetime.fromtimestamp(last_solved_ts, tz=timezone.utc)
        props["Last Solved"] = {"date": {"start": dt.isoformat()}}
    return props


def main() -> None:
    load_env_file(ENV_PATH)

    notion_token = require_env("NOTION_TOKEN")
    parent_page_id = normalize_notion_id(require_env("NOTION_PARENT_PAGE_ID"))
    session_cookie = require_env("LEETCODE_SESSION")
    csrf_token = require_env("LEETCODE_CSRF")

    db_id = ensure_database(notion_token, parent_page_id)

    state = read_state()
    last_seen = int(state.get("last_seen_ts", 0))

    session = requests.Session()
    session.headers.update(lc_session_headers(session_cookie, csrf_token))

    slugs, newest_ts = fetch_accepted_submissions_since(session, last_seen)
    if not slugs:
        print("No new accepted submissions.")
        return

    print(f"Found {len(slugs)} new solved problems.")

    for slug, solved_ts in slugs.items():
        question = fetch_question_data(session, slug)
        if not question:
            print(f"Skipping {slug}: no question data")
            continue
        props = build_notion_properties(question, solved_ts)
        qid = int(question.get("questionId") or 0)
        if not qid:
            print(f"Skipping {slug}: missing question id")
            continue

        page_id = notion_query_page_by_question_id(notion_token, db_id, qid)
        if page_id:
            notion_update_page(notion_token, page_id, props)
            print(f"Updated {question.get('title')}")
        else:
            notion_create_page(notion_token, db_id, props)
            print(f"Created {question.get('title')}")

    if newest_ts > last_seen:
        state["last_seen_ts"] = newest_ts
        write_state(state)


if __name__ == "__main__":
    main()

