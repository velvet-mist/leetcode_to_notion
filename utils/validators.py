"""
Environment variable validation utilities.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


# Required environment variables
REQUIRED_ENV_VARS = [
    "NOTION_TOKEN",
    "NOTION_PARENT_PAGE_ID",
    "LEETCODE_SESSION",
    "LEETCODE_CSRF",
]

# Optional environment variables
OPTIONAL_ENV_VARS = [
    "NOTION_DB_ID",
    "LOG_LEVEL",
    "LOG_FILE",
    "DRY_RUN",
    "VERBOSE",
]

# Notion ID pattern (32 hex characters)
NOTION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

# LeetCode CSRF token pattern
CSRF_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_notion_id(value: str, field_name: str = "Notion ID") -> str:
    """
    Validate a Notion ID format.
    
    Args:
        value: The ID to validate
        field_name: Field name for error message
        
    Returns:
        Normalized ID (with hyphens removed)
        
    Raises:
        ValidationError: If ID is invalid
    """
    if not value:
        raise ValidationError(f"{field_name} cannot be empty")
    
    # Remove hyphens and whitespace
    normalized = value.replace("-", "").strip()
    
    if len(normalized) != 32:
        raise ValidationError(
            f"{field_name} must be 32 characters (got {len(normalized)}). "
            f"Make sure you're using the full ID from the URL."
        )
    
    if not NOTION_ID_PATTERN.match(normalized):
        raise ValidationError(
            f"{field_name} contains invalid characters. "
            f"Expected: 32 hex characters (a-f, 0-9)"
        )
    
    return normalized


def validate_csrf_token(value: str) -> str:
    """
    Validate LeetCode CSRF token.
    
    Args:
        value: The CSRF token to validate
        
    Returns:
        The token
        
    Raises:
        ValidationError: If token is invalid
    """
    if not value:
        raise ValidationError("LEETCODE_CSRF cannot be empty")
    
    if len(value) < 10:
        raise ValidationError(
            f"LEETCODE_CSRF seems too short (got {len(value)} chars). "
            f"Make sure you're using the correct CSRF token."
        )
    
    return value.strip()


def validate_notion_token(value: str) -> str:
    """
    Validate Notion API token.
    
    Args:
        value: The token to validate
        
    Returns:
        The token
        
    Raises:
        ValidationError: If token is invalid
    """
    if not value:
        raise ValidationError("NOTION_TOKEN cannot be empty")
    
    # if not value.startswith("secret_"):
    #     raise ValidationError(
    #         "NOTION_TOKEN should start with 'secret_'. "
    #         "Get it from https://www.notion.so/my-integrations"
    #     )
    
    return value.strip()


def validate_session_cookie(value: str) -> str:
    """
    Validate LeetCode session cookie.
    
    Args:
        value: The session cookie to validate
        
    Returns:
        The cookie
        
    Raises:
        ValidationError: If cookie is invalid
    """
    if not value:
        raise ValidationError("LEETCODE_SESSION cannot be empty")
    
    if len(value) < 20:
        raise ValidationError(
            f"LEETCODE_SESSION seems too short (got {len(value)} chars). "
            f"Make sure you're using the correct session cookie."
        )
    
    return value.strip()


def validate_env_vars(env_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Validate all required environment variables.
    
    Args:
        env_vars: Optional dict of env vars (defaults to os.environ)
        
    Returns:
        Dict of validated environment variables
        
    Raises:
        ValidationError: If any required variable is missing or invalid
    """
    if env_vars is None:
        env_vars = dict(os.environ)
    
    errors: List[str] = []
    validated: Dict[str, str] = {}
    
    # Check required variables
    for var_name in REQUIRED_ENV_VARS:
        value = env_vars.get(var_name, "").strip()
        
        if not value:
            errors.append(f"Missing required env var: {var_name}")
            continue
        
        # Validate specific variables
        try:
            if var_name == "NOTION_TOKEN":
                validated[var_name] = validate_notion_token(value)
            elif var_name == "NOTION_PARENT_PAGE_ID":
                validated[var_name] = validate_notion_id(value, "NOTION_PARENT_PAGE_ID")
            elif var_name == "LEETCODE_SESSION":
                validated[var_name] = validate_session_cookie(value)
            elif var_name == "LEETCODE_CSRF":
                validated[var_name] = validate_csrf_token(value)
            else:
                validated[var_name] = value
        except ValidationError as e:
            errors.append(str(e))
    
    # Add optional variables if present
    for var_name in OPTIONAL_ENV_VARS:
        value = env_vars.get(var_name, "").strip()
        if value:
            validated[var_name] = value
    
    if errors:
        raise ValidationError("\n".join(errors))
    
    return validated


def check_env_file(env_path: Path) -> None:
    """
    Check if .env file exists and suggest creation if missing.
    
    Args:
        env_path: Path to .env file
    """
    if not env_path.exists():
        print(f"Warning: {env_path} not found.")
        print("Create a .env file with the following variables:")
        print("  NOTION_TOKEN=your_notion_token")
        print("  NOTION_PARENT_PAGE_ID=your_page_id")
        print("  LEETCODE_SESSION=your_session_cookie")
        print("  LEETCODE_CSRF=your_csrf_token")

