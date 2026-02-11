# LeetCode to Notion Integration

Automated tool to sync your LeetCode problem solutions to a Notion database.

## Features

- Automatically fetches accepted submissions from LeetCode
- Creates/updates pages in Notion with problem details
- Tracks all your solved problems with rich metadata

## Notion Database Fields

The integration creates a Notion database with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| **No.** | Number | LeetCode Question ID (e.g., 1, 2, 3...) |
| **Name** | Title | Problem name |
| **Topic** | Multi-select | Related topics/tags |
| **Difficulty Level** | Select | Easy/Medium/Hard |
| **Link** | URL | Link to LeetCode problem |
| **Question ID** | Number | LeetCode question identifier |
| **Last Solved** | Date | Date when the problem was solved |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with the following:

```env
# Notion API Token (get from https://www.notion.so/my-integrations)
NOTION_TOKEN=your_notion_integration_token

# Parent Page ID where the database will be created
# Copy this from the URL of your Notion page
NOTION_PARENT_PAGE_ID=your_parent_page_id

# LeetCode Session Cookie
# 1. Go to https://leetcode.com and log in
# 2. Open Developer Tools (F12) → Application → Cookies
# 3. Copy the value of LEETCODE_SESSION
LEETCODE_SESSION=your_leetcode_session_cookie

# LeetCode CSRF Token
# Found in the same cookies section as above
LEETCODE_CSRF=your_csrf_token
```

### 3. Run the Integration

```bash
python main.py
```

## How It Works

1. **Fetch Submissions**: Retrieves all accepted submissions since the last run
2. **Get Question Data**: Fetches detailed information for each problem from LeetCode GraphQL API
3. **Sync to Notion**: Creates new pages or updates existing ones in your Notion database

## Project Structure

```
leetcode_to_notion/
├── main.py                    # Main entry point
├── config.py                  # Configuration and field mappings
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
├── .notion_db_id             # Cached database ID (auto-generated)
├── state.json                # Last seen timestamp (auto-generated)
├── leetcode/
│   ├── fetch_submissions.py  # LeetCode API interactions
│   └── metadata.py           # Question metadata processing
└── notion/
    ├── create_page.py        # Notion page creation
    └── update_page.py        # Notion page updates
```

## First Run

On the first run, the tool will:
1. Create a new database called "LeetCode Solves" in your specified Notion page
2. Add all your accepted LeetCode submissions to the database
3. Save the database ID for future runs

## Subsequent Runs

On subsequent runs, the tool will:
1. Only fetch submissions since the last run
2. Update existing pages if you've solved a problem again
3. Create new pages for new problems

## Troubleshooting

### Missing submissions
- Make sure your LeetCode session cookie is valid
- Check that you have accepted submissions in your LeetCode profile

### Notion API errors
- Verify your Notion integration token has correct permissions
- Ensure the parent page exists and is accessible

### No new submissions found
- This likely means you've already synced all your accepted submissions
- The tool only processes "Accepted" submissions

