#!/usr/bin/env python3
"""
Helper script to extract Notion IDs from Notion page URLs.

Instructions:
1. Go to your Notion page/database in your browser
2. Copy the URL from your browser address bar
3. Run this script with the URL as input

Example URL formats:
- https://www.notion.so/Your-Workspace/Page-Name-1234567890abcdef1234567890abcdef
- https://notion.so/Page-Name-1234567890abcdef1234567890abcdef?v=xxx
"""

import re
import sys

def extract_notion_id(url: str) -> str:
    """Extract the 32-character Notion ID from a URL."""
    # Pattern 1: URL with ID at the end (with hyphens)
    pattern1 = r'notion\.so/[a-zA-Z0-9-]+-([a-f0-9]{32})'
    # Pattern 2: URL with just the ID
    pattern2 = r'notion\.so/([a-f0-9]{32})'
    # Pattern 3: Workspace URL
    pattern3 = r'/([a-f0-9]{32})'

    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None

def main():
    if len(sys.argv) > 1:
        # URL provided as argument
        url = sys.argv[1]
    else:
        # Prompt user for URL
        print("Notion ID Extractor")
        print("=" * 50)
        print("\nPaste your Notion page/database URL below:")
        print("(The URL should look like: https://www.notion.so/Page-Name-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)")
        url = input("\nURL: ").strip()

    notion_id = extract_notion_id(url)

    if notion_id:
        print(f"\n✓ Extracted Notion ID:")
        print(f"  {notion_id}")
        print(f"\nAdd this to your .env file as:")
        print(f"  NOTION_DB_ID={notion_id}")
        print(f"  (or NOTION_PARENT_PAGE_ID={notion_id} for parent page)")
    else:
        print("\n✗ Could not extract Notion ID from URL.")
        print("Make sure your URL looks like:")
        print("  https://www.notion.so/Your-Workspace/Page-Name-1234567890abcdef1234567890abcdef")

if __name__ == "__main__":
    main()

