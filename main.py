#!/usr/bin/env python3
"""
LeetCode to Notion Sync - Main Entry Point

Syncs your LeetCode accepted submissions to a Notion database.

Usage:
    python main.py                    # Run sync
    python main.py --dry-run          # Preview changes without saving
    python main.py --verbose          # Enable verbose logging
    python main.py --skip-hard        # Skip Hard difficulty problems
    python main.py --skip-topics "DP,Array"  # Skip specific topics
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from leetcode.client import LeetCodeClient
from leetcode.models import Question
from notion.client import NotionClient
from utils.logger import get_logger, setup_logger
from utils.validators import ValidationError, validate_env_vars

logger = get_logger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state.json"
DB_ID_PATH = BASE_DIR / ".notion_db_id"
ENV_PATH = BASE_DIR / ".env"


def load_state() -> Dict[str, Any]:
    """Load state from state.json file."""
    if not STATE_PATH.exists():
        return {"last_seen_ts": 0, "total_synced": 0}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"last_seen_ts": 0, "total_synced": 0}


def save_state(state: Dict[str, Any]) -> None:
    """Save state to state.json file (atomic write)."""
    temp_path = STATE_PATH.with_suffix('.json.tmp')
    temp_path.write_text(json.dumps(state, indent=2))
    temp_path.rename(STATE_PATH)


def build_notion_properties(question: Question, last_solved_ts: int) -> Dict[str, Any]:
    """Build Notion properties from a Question object."""
    props = {
        "Question ID": {"number": int(question.question_id)},
        "Name": {"title": [{"text": {"content": question.title}}]},
        "Link": {"url": question.link},
        "Difficulty Level": {"select": {"name": question.difficulty}},
        "Topic": {"multi_select": [{"name": t} for t in question.topics]},
    }
    
    if last_solved_ts:
        dt = datetime.fromtimestamp(last_solved_ts, tz=timezone.utc)
        props["Last Solved"] = {"date": {"start": dt.isoformat()}}
    
    return props


def parse_comma_separated(value: str) -> List[str]:
    """Parse comma-separated string into list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def sync_submissions(
    lc_client: LeetCodeClient,
    notion_client: NotionClient,
    db_id: str,
    last_timestamp: int,
    dry_run: bool = False,
    skip_difficulty: Optional[List[str]] = None,
    skip_topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sync LeetCode submissions to Notion."""
    stats = {
        "total_found": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    submissions, newest_ts = lc_client.fetch_accepted_submissions_since(last_timestamp)
    stats["total_found"] = len(submissions)
    
    if not submissions:
        logger.info("No new accepted submissions found.")
        return stats
    
    logger.info(f"Found {len(submissions)} new solved problems")
    
    for slug, solved_ts in submissions.items():
        try:
            question = lc_client.fetch_question_data(slug)
            
            if not question:
                logger.warning(f"Skipping {slug}: no question data")
                stats["skipped"] += 1
                continue
            
            if skip_difficulty and question.difficulty in skip_difficulty:
                logger.info(f"Skipping {question.title} ({question.difficulty} - filtered)")
                stats["skipped"] += 1
                continue
            
            if skip_topics:
                question_topics = set(t.lower() for t in question.topics)
                skip_topics_lower = set(t.lower() for t in skip_topics)
                if question_topics & skip_topics_lower:
                    logger.info(f"Skipping {question.title} (filtered topic: {question.topics})")
                    stats["skipped"] += 1
                    continue
            
            props = build_notion_properties(question, solved_ts)
            qid = int(question.question_id)
            page_id = notion_client.find_page_by_question_id(db_id, qid)
            
            if dry_run:
                action = "Would update" if page_id else "Would create"
                logger.info(f"[DRY-RUN] {action}: {question.title} (ID: {qid})")
            else:
                if page_id:
                    notion_client.update_page(page_id, props)
                    logger.info(f"Updated: {question.title}")
                    stats["updated"] += 1
                else:
                    notion_client.create_page(db_id, props)
                    logger.info(f"Created: {question.title}")
                    stats["created"] += 1
            
        except Exception as e:
            logger.error(f"Error processing {slug}: {e}")
            stats["errors"] += 1
    
    return stats, newest_ts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync LeetCode solutions to Notion database")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--skip-difficulty", type=parse_comma_separated, default=[], help="Skip difficulties")
    parser.add_argument("--skip-topics", type=parse_comma_separated, default=[], help="Skip topics")
    parser.add_argument("--force-recreate", action="store_true", help="Force recreate database")
    parser.add_argument("--resync", action="store_true", help="Resync from scratch")
    args = parser.parse_args()
    
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)
    
    logger.info("=" * 50)
    logger.info("LeetCode to Notion Sync")
    logger.info("=" * 50)
    
    if args.dry_run:
        logger.info("Running in DRY-RUN mode (no changes will be made)")
    
    load_dotenv(ENV_PATH)
    
    try:
        env = validate_env_vars()
    except ValidationError as e:
        logger.error(f"Configuration error:\n{e}")
        sys.exit(1)
    
    lc_client = LeetCodeClient(session_cookie=env["LEETCODE_SESSION"], csrf_token=env["LEETCODE_CSRF"])
    notion_client = NotionClient(token=env["NOTION_TOKEN"])
    
    logger.info("Validating LeetCode session...")
    if not lc_client.validate_session():
        logger.error("Invalid LeetCode session. Please check your cookies.")
        sys.exit(1)
    
    state = load_state()
    last_timestamp = 0 if args.resync else state.get("last_seen_ts", 0)
    
    if args.resync:
        logger.info("Resync mode: starting from scratch")
    else:
        logger.info(f"Last sync: {datetime.fromtimestamp(last_timestamp, tz=timezone.utc)}")
    
    db_id = notion_client.ensure_database(
        parent_page_id=env["NOTION_PARENT_PAGE_ID"],
        db_id_path=DB_ID_PATH,
        force_create=args.force_recreate
    )
    logger.info(f"Using database: {db_id}")
    
    try:
        result = sync_submissions(
            lc_client=lc_client,
            notion_client=notion_client,
            db_id=db_id,
            last_timestamp=last_timestamp,
            dry_run=args.dry_run,
            skip_difficulty=args.skip_difficulty,
            skip_topics=args.skip_topics,
        )
        
        stats, newest_ts = result if isinstance(result, tuple) else (result, 0)
        
        if not args.dry_run and newest_ts > last_timestamp:
            state["last_seen_ts"] = newest_ts
            state["total_synced"] = state.get("total_synced", 0) + stats["created"]
            save_state(state)
        
        logger.info("=" * 50)
        logger.info("Sync Complete!")
        logger.info(f"  Found:     {stats['total_found']}")
        if not args.dry_run:
            logger.info(f"  Created:   {stats['created']}")
            logger.info(f"  Updated:   {stats['updated']}")
        logger.info(f"  Skipped:   {stats['skipped']}")
        logger.info(f"  Errors:    {stats['errors']}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()

