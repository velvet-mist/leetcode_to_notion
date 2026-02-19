"""
Data models for Notion API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class NotionPage:
    """Represents a Notion page."""
    page_id: str
    created_time: str = ""
    last_edited_time: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> "NotionPage":
        return cls(
            page_id=data.get("id", ""),
            created_time=data.get("created_time", ""),
            last_edited_time=data.get("last_edited_time", ""),
            properties=data.get("properties", {})
        )


@dataclass
class NotionDatabase:
    """Represents a Notion database."""
    database_id: str
    title: str = ""
    created_time: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> "NotionDatabase":
        return cls(
            database_id=data.get("id", ""),
            title=data.get("title", [{}])[0].get("text", {}).get("content", ""),
            created_time=data.get("created_time", ""),
            properties=data.get("properties", {})
        )


@dataclass
class NotionProperty:
    """Represents a Notion property configuration."""
    name: str
    property_type: str
    options: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def title(cls, name: str) -> "NotionProperty":
        return cls(name=name, property_type="title")
    
    @classmethod
    def number(cls, name: str) -> "NotionProperty":
        return cls(name=name, property_type="number")
    
    @classmethod
    def url(cls, name: str) -> "NotionProperty":
        return cls(name=name, property_type="url")
    
    @classmethod
    def date(cls, name: str) -> "NotionProperty":
        return cls(name=name, property_type="date")
    
    @classmethod
    def select(cls, name: str, options: List[str]) -> "NotionProperty":
        return cls(
            name=name,
            property_type="select",
            options=[{"name": opt} for opt in options]
        )
    
    @classmethod
    def multi_select(cls, name: str, options: List[str]) -> "NotionProperty":
        return cls(
            name=name,
            property_type="multi_select",
            options=[{"name": opt} for opt in options]
        )


# Default database schema for LeetCode problems
DEFAULT_DATABASE_PROPERTIES = {
    "Name": {"title": {}},
    "Link": {"url": {}},
    "Question ID": {"number": {}},
    "Difficulty Level": {
        "select": {
            "options": [
                {"name": "Easy", "color": "green"},
                {"name": "Medium", "color": "yellow"},
                {"name": "Hard", "color": "red"}
            ]
        }
    },
    "Topic": {"multi_select": {}},
    "Last Solved": {"date": {}},
}


# Field mapping from internal names to Notion property names
FIELD_MAPPING = {
    "no": "No.",
    "name": "Name",
    "link": "Link",
    "difficulty": "Difficulty Level",
    "topics": "Topic",
    "question_id": "Question ID",
    "last_solved": "Last Solved"
}

