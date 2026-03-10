"""
LeetCode API client with retry logic and rate limiting.
"""

import re
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
    PROBLEMS_ALL_API = f"{BASE_URL}/api/problems/all/"
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

    USER_STATUS_QUERY = """
    query globalData {
      userStatus {
        isSignedIn
        username
      }
    }
    """

    SUBMISSION_LIST_QUERY = """
    query submissionList($offset: Int!, $limit: Int!) {
      submissionList(offset: $offset, limit: $limit) {
        hasNext
        submissions {
          titleSlug
          statusDisplay
          timestamp
        }
      }
    }
    """
    
    def __init__(
        self,
        session_cookie: str,
        csrf_token: str,
        cookie_header: Optional[str] = None,
    ):
        """
        Initialize LeetCode client.
        
        Args:
            session_cookie: LeetCode session cookie
            csrf_token: LeetCode CSRF token
            cookie_header: Raw browser Cookie header (optional)
        """
        self.session = requests.Session()
        self._setup_headers(session_cookie, csrf_token, cookie_header)
        self._bootstrap_auth_context()
        self._validated = False
    
    def _setup_headers(
        self,
        session_cookie: str,
        csrf_token: str,
        cookie_header: Optional[str] = None,
    ) -> None:
        """Setup request headers."""
        cookie = cookie_header.strip() if cookie_header else ""
        if cookie.lower().startswith("cookie:"):
            cookie = cookie.split(":", 1)[1].strip()
        if not cookie:
            cookie = f"LEETCODE_SESSION={session_cookie}; csrftoken={csrf_token}"

        # Keep explicit csrf header for requests that enforce CSRF checks.
        if not csrf_token:
            match = re.search(r"(?:^|;\s*)csrftoken=([^;]+)", cookie)
            if match:
                csrf_token = match.group(1)

        # Populate cookie jar so requests can manage additional cookies dynamically.
        for part in cookie.split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            self.session.cookies.set(key.strip(), value.strip(), domain="leetcode.com")

        self.session.headers.update({
            "x-csrftoken": csrf_token,
            "Referer": self.BASE_URL,
            "Origin": self.BASE_URL,
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        })

    def _bootstrap_auth_context(self) -> None:
        """
        Prime session cookies from LeetCode home page.

        This helps when anti-bot/session middleware expects additional cookies
        beyond LEETCODE_SESSION/csrftoken.
        """
        try:
            response = self.session.get(self.BASE_URL, timeout=self.REQUEST_TIMEOUT)
            if response.status_code < 400:
                csrf_cookie = self.session.cookies.get("csrftoken")
                if csrf_cookie:
                    self.session.headers["x-csrftoken"] = csrf_cookie
        except requests.exceptions.RequestException as e:
            logger.debug(f"Auth bootstrap skipped due to request error: {e}")
    
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
            # GraphQL validation first (more stable than /api/submissions for some accounts).
            payload = {"query": self.USER_STATUS_QUERY, "variables": {}}
            response = self._request_with_retry("POST", self.GRAPHQL_URL, json=payload)
            user_status = response.json().get("data", {}).get("userStatus", {})
            if user_status.get("isSignedIn"):
                self._validated = True
                logger.info(
                    "LeetCode session validated via GraphQL"
                    f" (user: {user_status.get('username', 'unknown')})"
                )
                return True

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
        logger.info(f"Fetching submissions since timestamp {last_timestamp}")

        # Full resync mode: use complete solved list, then enrich with timestamps
        # from recent submissions when available.
        if last_timestamp == 0:
            try:
                all_solved, _ = self._fetch_solved_from_problems_all(0)
                try:
                    recent_solved, newest_ts = self._fetch_accepted_submissions_since_rest(0)
                except LeetCodeError:
                    recent_solved, newest_ts = self._fetch_accepted_submissions_since_graphql(0)

                merged = dict(all_solved)
                merged.update(recent_solved)
                logger.info(
                    f"Resync assembled {len(merged)} solved problems "
                    f"({len(recent_solved)} with timestamps)"
                )
                return merged, newest_ts
            except LeetCodeError:
                # Fall through to original strategy.
                pass

        try:
            return self._fetch_accepted_submissions_since_rest(last_timestamp)
        except LeetCodeError as e:
            if "403" in str(e):
                logger.warning(
                    "REST submissions endpoint returned 403; "
                    "falling back to GraphQL submissionList."
                )
                submissions, newest_ts = self._fetch_accepted_submissions_since_graphql(last_timestamp)
                if submissions and not (last_timestamp == 0 and len(submissions) <= 20):
                    return submissions, newest_ts

                logger.warning(
                    "GraphQL submissions are unavailable or limited; "
                    "falling back to /api/problems/all/ solved list."
                )
                return self._fetch_solved_from_problems_all(last_timestamp)
            raise

    def _fetch_accepted_submissions_since_rest(
        self,
        last_timestamp: int,
    ) -> Tuple[Dict[str, int], int]:
        """Fetch accepted submissions using /api/submissions endpoint."""
        submissions: Dict[str, int] = {}
        max_timestamp = last_timestamp
        last_key = ""

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

                if ts <= last_timestamp:
                    logger.info(f"Reached submissions up to timestamp {last_timestamp}")
                    return submissions, max_timestamp

                if item.get("status_display") == "Accepted":
                    slug = item.get("title_slug")
                    if slug:
                        submissions[slug] = max(submissions.get(slug, 0), ts)
                        if ts > max_timestamp:
                            max_timestamp = ts

            if not data.get("has_next"):
                break

            last_key = data.get("last_key") or ""
            if not last_key:
                break

        logger.info(f"Found {len(submissions)} new accepted submissions")
        return submissions, max_timestamp

    def _fetch_accepted_submissions_since_graphql(
        self,
        last_timestamp: int,
    ) -> Tuple[Dict[str, int], int]:
        """Fetch accepted submissions using GraphQL submissionList endpoint."""
        submissions: Dict[str, int] = {}
        max_timestamp = last_timestamp
        offset = 0
        limit = 100

        page = 0
        while True:
            payload = {
                "query": self.SUBMISSION_LIST_QUERY,
                "variables": {"offset": offset, "limit": limit},
            }
            response = self._request_with_retry("POST", self.GRAPHQL_URL, json=payload)
            data = response.json().get("data", {}).get("submissionList", {})
            submissions_list = data.get("submissions", [])
            page += 1

            if not submissions_list:
                break

            for item in submissions_list:
                try:
                    ts = int(item.get("timestamp", 0))
                except (TypeError, ValueError):
                    ts = 0

                if ts <= last_timestamp:
                    logger.info(f"Reached submissions up to timestamp {last_timestamp}")
                    return submissions, max_timestamp

                if item.get("statusDisplay") == "Accepted":
                    slug = item.get("titleSlug")
                    if slug:
                        submissions[slug] = max(submissions.get(slug, 0), ts)
                        if ts > max_timestamp:
                            max_timestamp = ts

            if not data.get("hasNext"):
                break

            offset += limit
            # LeetCode may report hasNext=true but still only expose first page.
            if page >= 1 and len(submissions_list) < limit:
                break

        logger.info(f"Found {len(submissions)} new accepted submissions (GraphQL)")
        return submissions, max_timestamp

    def _fetch_solved_from_problems_all(
        self,
        last_timestamp: int,
    ) -> Tuple[Dict[str, int], int]:
        """
        Fetch solved problems from /api/problems/all/.

        Note: This endpoint does not provide solve timestamps, so incremental
        sync from a non-zero last_timestamp is not supported.
        """
        if last_timestamp > 0:
            logger.warning(
                "/api/problems/all/ fallback has no timestamps; "
                "cannot safely do incremental sync. Returning no new submissions."
            )
            return {}, last_timestamp

        response = self._request_with_retry("GET", self.PROBLEMS_ALL_API)
        data = response.json()
        pairs = data.get("stat_status_pairs", [])

        submissions: Dict[str, int] = {}
        for item in pairs:
            if item.get("status") != "ac":
                continue
            stat = item.get("stat", {})
            slug = stat.get("question__title_slug")
            if slug:
                submissions[slug] = 0

        logger.info(
            f"Found {len(submissions)} solved problems via /api/problems/all/ fallback"
        )
        return submissions, 0
    
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
