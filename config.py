import os
from typing import Dict, List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")
LEETCODE_SESSION = os.getenv("LEETCODE_SESSION")
LEETCODE_CSRF = os.getenv("LEETCODE_CSRF")

# Notion database properties schema
NOTION_PROPERTIES = {
    "No.": {"type": "number", "format": "number"},
    "Name": {"type": "title"},
    "Link": {"type": "url"},
    "Difficulty Level": {
        "type": "select",
        "options": [
            {"name": "Easy", "color": "green"},
            {"name": "Medium", "color": "yellow"},
            {"name": "Hard", "color": "red"}
        ]
    },
    "Topic": {"type": "multi_select"},
    "Question ID": {"type": "number", "format": "number"},
    "Last Solved": {"type": "date"}
}

# Field mapping from internal names to Notion property names
NOTION_FIELD_MAPPING = {
    "no": "No.",
    "name": "Name",
    "link": "Link",
    "difficulty": "Difficulty Level",
    "topics": "Topic",
    "question_id": "Question ID",
    "last_solved": "Last Solved"
}

# Difficulty level mapping
DIFFICULTY_MAP = {
    "Easy": "Easy",
    "Medium": "Medium",
    "Hard": "Hard"
}

