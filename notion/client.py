"""
Notion API client with retry logic and rate limiting.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from notion.models import DEFAULT_DATABASE_PROPERTIES, NotionDatabase, NotionPage

from utils.logger import get_logger

logger = get_logger(__name__)


class NotionError(Exception):
    """Custom exception for Notion API errors."""
    pass


class NotionClient:
    """Client for interacting with Notion API."""
    
    # API configuration
    BASE_URL = "https://api.notion.com/v1"
    VERSION = "2022-06-28"
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    REQUEST_TIMEOUT = 30
    
    def __init__(self, token: str, database_id: Optional[str] = None):
        """
        Initialize Notion client.
        
        Args:
            token: Notion API token (starts with secret_)
            database_id: Optional existing database ID
        """
        self.token = token
        self.database_id = database_id
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": self.VERSION,
            "Content-Type": "application/json",
        }
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            NotionError: If all retries fail
        """
        kwargs.setdefault("timeout", self.REQUEST_TIMEOUT)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.request(method, url, headers=self._headers, **kwargs)
                
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
                error_msg = f"Request failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', response.text[:200])}"
                except Exception:
                    error_msg += f" - {response.text[:200]}"
                
                raise NotionError(error_msg)
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout. Retry {attempt + 1}/{self.MAX_RETRIES}")
                time.sleep(self.RETRY_DELAY)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error: {e}. Retry {attempt + 1}/{self.MAX_RETRIES}")
                time.sleep(self.RETRY_DELAY)
        
        raise NotionError(f"Failed after {self.MAX_RETRIES} retries")
    
    def create_database(
        self,
        parent_page_id: str,
        title: str = "LeetCode Solves",
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new Notion database.
        
        Args:
            parent_page_id: ID of the parent page
            title: Database title
            properties: Database schema (uses default if not provided)
            
        Returns:
            Database ID
            
        Raises:
            NotionError: If creation fails
        """
        if properties is None:
            properties = DEFAULT_DATABASE_PROPERTIES
        
        payload = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        
        logger.info(f"Creating database '{title}' in page {parent_page_id}")
        
        response = self._request_with_retry(
            "POST",
            f"{self.BASE_URL}/databases",
            json=payload
        )
        
        if response.status_code >= 300:
            raise NotionError(f"Failed to create database: {response.text}")
        
        data = response.json()
        db_id = data.get("id")
        
        if not db_id:
            raise NotionError("Notion did not return a database id")
        
        logger.info(f"Created database: {db_id}")
        return db_id
    
    def get_database(self, database_id: str) -> NotionDatabase:
        """
        Get database information.
        
        Args:
            database_id: Database ID
            
        Returns:
            NotionDatabase object
            
        Raises:
            NotionError: If query fails
        """
        response = self._request_with_retry(
            "GET",
            f"{self.BASE_URL}/databases/{database_id}"
        )
        
        if response.status_code >= 300:
            raise NotionError(f"Failed to get database: {response.text}")
        
        return NotionDatabase.from_dict(response.json())
    
    def query_database(
        self,
        database_id: str,
        filter_props: Optional[Dict[str, Any]] = None
    ) -> List[NotionPage]:
        """
        Query pages in a database.
        
        Args:
            database_id: Database ID
            filter_props: Optional filter properties
            
        Returns:
            List of NotionPage objects
        """
        payload = {}
        if filter_props:
            payload["filter"] = filter_props
        
        pages: List[NotionPage] = []
        
        while True:
            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/databases/{database_id}/query",
                json=payload
            )
            
            if response.status_code >= 300:
                raise NotionError(f"Query failed: {response.text}")
            
            data = response.json()
            for result in data.get("results", []):
                pages.append(NotionPage.from_dict(result))
            
            # Check for pagination
            if not data.get("has_more"):
                break
            
            payload["start_cursor"] = data.get("next_cursor")
        
        return pages
    
    def find_page_by_question_id(
        self,
        database_id: str,
        question_id: int
    ) -> Optional[str]:
        """
        Find a page in the database by question ID.
        
        Args:
            database_id: Database ID
            question_id: LeetCode question ID
            
        Returns:
            Page ID if found, None otherwise
        """
        filter_props = {
            "property": "Question ID",
            "number": {"equals": question_id},
        }
        
        pages = self.query_database(database_id, filter_props)
        
        if pages:
            return pages[0].page_id
        return None
    
    def create_page(
        self,
        database_id: str,
        properties: Dict[str, Any]
    ) -> str:
        """
        Create a new page in the database.
        
        Args:
            database_id: Database ID
            properties: Page properties
            
        Returns:
            Created page ID
            
        Raises:
            NotionError: If creation fails
        """
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        
        logger.debug(f"Creating page in database {database_id}")
        
        response = self._request_with_retry(
            "POST",
            f"{self.BASE_URL}/pages",
            json=payload
        )
        
        if response.status_code >= 300:
            raise NotionError(f"Failed to create page: {response.text}")
        
        data = response.json()
        page_id = data.get("id")
        
        if not page_id:
            raise NotionError("Notion did not return a page id")
        
        logger.debug(f"Created page: {page_id}")
        return page_id
    
    def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> None:
        """
        Update an existing page.
        
        Args:
            page_id: Page ID
            properties: Updated properties
            
        Raises:
            NotionError: If update fails
        """
        payload = {"properties": properties}
        
        logger.debug(f"Updating page {page_id}")
        
        response = self._request_with_retry(
            "PATCH",
            f"{self.BASE_URL}/pages/{page_id}",
            json=payload
        )
        
        if response.status_code >= 300:
            raise NotionError(f"Failed to update page: {response.text}")
        
        logger.debug(f"Updated page: {page_id}")
    
    def ensure_database(
        self,
        parent_page_id: str,
        db_id_path: Path,
        force_create: bool = False
    ) -> str:
        """
        Ensure a database exists, creating if necessary.
        
        Args:
            parent_page_id: Parent page ID
            db_id_path: Path to cache database ID
            force_create: Force creation of new database
            
        Returns:
            Database ID
        """
        # Check for environment variable override
        import os
        env_db_id = os.environ.get("NOTION_DB_ID", "").strip()
        if env_db_id:
            logger.info(f"Using database from NOTION_DB_ID: {env_db_id}")
            return env_db_id.replace("-", "")
        
        # Check cached ID
        if not force_create and db_id_path.exists():
            cached = db_id_path.read_text().strip()
            if cached:
                logger.info(f"Using cached database ID: {cached}")
                return cached
        
        # Create new database
        db_id = self.create_database(parent_page_id)
        
        # Cache the ID
        db_id_path.parent.mkdir(parents=True, exist_ok=True)
        db_id_path.write_text(db_id)
        
        return db_id

