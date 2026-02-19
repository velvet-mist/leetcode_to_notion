"""
Data models for LeetCode API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class TopicTag:
    """Represents a topic tag for a LeetCode problem."""
    name: str
    slug: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "TopicTag":
        return cls(
            name=data.get("name", ""),
            slug=data.get("slug", "")
        )


@dataclass
class Question:
    """Represents a LeetCode question/problem."""
    question_id: str
    title: str
    title_slug: str
    difficulty: str
    topic_tags: List[TopicTag] = field(default_factory=list)
    link: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        topic_tags = [
            TopicTag.from_dict(t) 
            for t in data.get("topicTags", [])
            if t.get("name")
        ]
        
        slug = data.get("titleSlug", "")
        link = f"https://leetcode.com/problems/{slug}/" if slug else ""
        
        return cls(
            question_id=str(data.get("questionId", "")),
            title=data.get("title", ""),
            title_slug=slug,
            difficulty=data.get("difficulty", ""),
            topic_tags=topic_tags,
            link=link
        )
    
    @property
    def difficulty_level(self) -> str:
        """Return difficulty in consistent format."""
        return self.difficulty
    
    @property
    def topics(self) -> List[str]:
        """Return list of topic names."""
        return [tag.name for tag in self.topic_tags]


@dataclass
class Submission:
    """Represents a LeetCode submission."""
    slug: str
    timestamp: int
    status: str = "Accepted"
    lang: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "Submission":
        return cls(
            slug=data.get("title_slug", ""),
            timestamp=int(data.get("timestamp", 0)),
            status=data.get("status_display", ""),
            lang=data.get("lang", "")
        )
    
    @property
    def solved_at(self) -> datetime:
        """Return datetime of when problem was solved."""
        return datetime.fromtimestamp(self.timestamp)


@dataclass 
class SubmissionResult:
    """Result of processing a submission."""
    slug: str
    question: Optional[Question] = None
    last_solved_ts: int = 0
    status: str = "pending"  # pending, success, skipped, error
    message: str = ""
    
    def is_success(self) -> bool:
        return self.status == "success"
    
    def is_skipped(self) -> bool:
        return self.status == "skipped"
    
    def is_error(self) -> bool:
        return self.status == "error"

