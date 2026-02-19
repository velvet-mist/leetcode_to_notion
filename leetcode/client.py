"""
LeetCode API client with retry logic and rate limiting.
"""

import time
from typing import Dict, List, Optional, Tuple

import requests

from leetcode.models import Question, Submission, SubmissionResult

from utils.logger import get_logger

logger = get_logger(__name__)


class LeetCodeError(Exception):
    """Custom exception for LeetCode API errors."""
    pass


class LeetCodeClient:
    """Client for interacting with LeetCode API."""
    
    # API endpoints
    BASE_URL = "https://leetcode.com"
    SUBMISSIONS_API = f"{BASE_URL}/api/submissions/"
    GRAPHQL_URL = f"{BASE_URL}/graphql"
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    REQUEST_TIMEOUT = 30
    
    # Question query
    QUESTION_QUERY = """
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
    
    def __init__(self, session_cookie: str, csrf_token: str):
        """
        Initialize LeetCode client.
        
        Args:
            session_cookie: LeetCode session cookie
            csrf_token: LeetCode CSRF token
        """
        self.session = requests.Session()
        self._setup_headers(session_cookie, csrf_token)
        self._validated = False
    
    def _setup_headers(self, session_cookie: str, csrf_token: str) -> None:
        """Setup request headers."""
        cookie = f"LEETCODE_SESSION={session_cookie}; csrftoken={csrf_token}"
        self.session.headers.update({
            "Cookie": cookie,
            "x-csrftoken": csrf_token,
            "Referer": self.BASE_URL,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        })
    
    def _request_with_retry(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            LeetCodeError: If all retries fail
        """
        kwargs.setdefault("timeout", self.REQUEST_TIMEOUT)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                # Check for success
                if response.status_code < 400:
                    return response
                    
                # Server error - retry
                if response.status_code >= 500:
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    logger.warning(
                        f"Server error {response.status_code}. "
                        f"Retry {attempt + 1}/{self.MAX_RETRIES} in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                    
                # Client error - don't retry
                raise LeetCodeError(
                    f"Request failed: {response.status_code} {response.text}"
                )
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout. Retry {attempt + 1}/{self.MAX_RETRIES}")
                time.sleep(self.RETRY_DELAY)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error: {e}. Retry {attempt + 1}/{self.MAX_RETRIES}")
                time.sleep(self.RETRY_DELAY)
        
        raise LeetCodeError(f"Failed after {self.MAX_RETRIES} retries")
    
    def validate_session(self) -> bool:
        """
        Validate that the session is authenticated.
        
        Returns:
            True if session is valid, False otherwise
        """
        if self._validated:
            return True
            
        try:
            # Try to fetch submissions - this will fail if not authenticated
            response = self._request_with_retry("GET", self.SUBMISSIONS_API)
            data = response.json()
            
            # Check if we got valid data
            if "user_name" in data or "submissions_dump" in data:
                self._validated = True
                logger.info("LeetCode session validated successfully")
                return True
            
            logger.warning("LeetCode session may not be authenticated")
            return False
            
        except LeetCodeError as e:
            logger.error(f"Failed to validate session: {e}")
            return False
    
    def fetch_accepted_submissions_since(
        self, 
        last_timestamp: int = 0
    ) -> Tuple[Dict[str, int], int]:
        """
        Fetch all accepted submissions since the given timestamp.
        
        Args:
            last_timestamp: Only fetch submissions after this timestamp
            
        Returns:
            Tuple of (slug -> latest timestamp dict, newest timestamp)
        """
        submissions: Dict[str, int] = {}
        max_timestamp = last_timestamp
        last_key = ""
        
        logger.info(f"Fetching submissions since timestamp {last_timestamp}")
        
        while True:
            url = f"{self.SUBMISSIONS_API}?offset=0&limit=100&lastkey={last_key}"
            response = self._request_with_retry("GET", url)
            data = response.json()
            
            submissions_dump = data.get("submissions_dump", [])
            
            if not submissions_dump:
                break
                
            for item in submissions_dump:
                try:
                    ts = int(item.get("timestamp", 0))
                except (TypeError, ValueError):
                    ts = 0
                
                # Stop if we've reached old submissions
                if ts <= last_timestamp:
                    logger.info(f"Reached submissions up to timestamp {last_timestamp}")
                    return submissions, max_timestamp
                
                # Only process accepted submissions
                if item.get("status_display") == "Accepted":
                    slug = item.get("title_slug")
                    if slug:
                        # Keep the latest timestamp for each problem
                        submissions[slug] = max(submissions.get(slug, 0), ts)
                        if ts > max_timestamp:
                            max_timestamp = ts
            
            # Check if there are more pages
            if not data.get("has_next"):
                break
                
            last_key = data.get("last_key") or ""
            if not last_key:
                break
        
        logger.info(f"Found {len(submissions)} new accepted submissions")
        return submissions, max_timestamp
    
    def fetch_question_data(self, slug: str) -> Optional[Question]:
        """
        Fetch question metadata from LeetCode GraphQL API.
        
        Args:
            slug: Question slug (e.g., "two-sum")
            
        Returns:
            Question object or None if not found
        """
        payload = {
            "query": self.QUESTION_QUERY,
            "variables": {"titleSlug": slug}
        }
        
        response = self._request_with_retry("POST", self.GRAPHQL_URL, json=payload)
        data = response.json()
        
        question_data = data.get("data", {}).get("question")
        
        if not question_data:
            logger.warning(f"No question data found for slug: {slug}")
            return None
        
        return Question.from_dict(question_data)
    
    def process_submissions(
        self, 
        submissions: Dict[str, int],
        skip_difficulty: Optional[List[str]] = None,
        skip_topics: Optional[List[str]] = None,
    ) -> List[SubmissionResult]:
        """
        Process a batch of submissions and fetch question data.
        
        Args:
            submissions: Dict of slug -> timestamp
            skip_difficulty: List of difficulties to skip
            skip_topics: List of topics to skip
            
        Returns:
            List of submission results
        """
        results: List[SubmissionResult] = []
        skip_difficulty = skip_difficulty or []
        skip_topics = skip_topics or []
        
        for slug, solved_ts in submissions.items():
            result = SubmissionResult(slug=slug, last_solved_ts=solved_ts)
            
            try:
                question = self.fetch_question_data(slug)
                
                if not question:
                    result.status = "skipped"
                    result.message = "No question data found"
                    logger.warning(f"Skipping {slug}: no question data")
                    continue
                
                # Check difficulty filter
                if question.difficulty in skip_difficulty:
                    result.status = "skipped"
                    result.message = f"Skipped difficulty: {question.difficulty}"
                    logger.info(f"Skipping {question.title} ({question.difficulty})")
                    continue
                
                # Check topic filter
                if skip_topics:
                    question_topics = set(t.lower() for t in question.topics)
                    skip_topics_lower = set(t.lower() for t in skip_topics)
                    if question_topics & skip_topics_lower:  # intersection
                        result.status = "skipped"
                        result.message = f"Skipped topic: {question.topics}"
                        logger.info(f"Skipping {question.title} (filtered topic)")
                        continue
                
                result.question = question
                result.status = "success"
                
            except LeetCodeError as e:
                result.status = "error"
                result.message = str(e)
                logger.error(f"Error processing {slug}: {e}")
            
            results.append(result)
        
        return results
