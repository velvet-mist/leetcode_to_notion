
# 🚀 LeetCode → Notion Sync

Automatically sync your solved LeetCode problems into a structured Notion database — including metadata like difficulty, tags, date solved, and problem link.

Built for developers who want structured tracking beyond LeetCode’s UI.

---

## 📌 Features

* ✅ Fetch solved problems from LeetCode
* ✅ Extract:

  * Title
  * Difficulty
  * Topics
  * URL
  * Date solved
* ✅ Automatically create a Notion database (if not exists)
* ✅ Insert problems into Notion
* ✅ Prevent duplicate entries
* ✅ Clean, structured schema

---

## 🏗 Architecture

```
LeetCode Session (CSRF + Cookie)
        ↓
GraphQL Fetch
        ↓
Python Processing Layer
        ↓
Notion API (Database + Pages)
```

Tech stack:

* Python 3.10+
* `requests`
* Notion API
* LeetCode GraphQL endpoint

---

## 🔐 Required Credentials

You need:

### 1️⃣ LeetCode

* `LEETCODE_SESSION`
* `csrftoken`

Extract from browser → DevTools → Application → Cookies.

---

### 2️⃣ Notion

* Internal Integration Token
* Parent Page ID

Create integration:
Settings → Connections → Develop your own integration

Then:
Share your parent page with the integration.

---

## ⚙️ Setup

### 1️⃣ Clone

```bash
git clone https://github.com/yourusername/leetcode_to_notion.git
cd leetcode_to_notion
```

---

### 2️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Create `.env`

```
NOTION_TOKEN=your_notion_token
NOTION_PAGE_ID=your_parent_page_id
LEETCODE_SESSION=your_session_cookie
LEETCODE_CSRF_TOKEN=your_csrf_token
```

---

## ▶️ Run

```bash
python3 main.py
```

---

## 🗂 Notion Database Schema

| Property    | Type         |
| ----------- | ------------ |
| Name        | Title        |
| Difficulty  | Select       |
| Topics      | Multi-select |
| Date Solved | Date         |
| URL         | URL          |
| Status      | Select       |

---

## 🛠 Common Errors

### 404 object_not_found

Page not shared with integration.

Fix:
Share parent page via Notion → Share → Connections.

---

### 401 Unauthorized

Token invalid or expired.

Regenerate integration token.

---

### Duplicate Problems

Handled internally by checking title before insertion.

---

## Automatic Background Sync (macOS)

You can run the sync automatically in the background using macOS's built-in `launchd` service. This will keep your Notion database up-to-date without manual intervention.

### Quick Setup

```bash
# Make the setup script executable
chmod +x setup_launchd.sh

# Install and start the background service
./setup_launchd.sh install
```

### Managing the Service

```bash
# Check if the service is running
./setup_launchd.sh status

# View live logs (shows when problems are synced)
./setup_launchd.sh logs

# Run sync manually once (useful for testing)
./setup_launchd.sh run

# Stop the background service
./setup_launchd.sh stop

# Start the background service again
./setup_launchd.sh start

# Uninstall the background service
./setup_launchd.sh uninstall
```

### Configuration

The service is configured to run every **30 minutes** by default. To change this interval:

1. Edit `com.user.leetcode_notion_sync.plist`
2. Change the `StartInterval` value:
   - `900` = 15 minutes
   - `1800` = 30 minutes (default)
   - `3600` = 1 hour
   - `86400` = 1 day
3. Reload the service:
   ```bash
   ./setup_launchd.sh uninstall
   ./setup_launchd.sh install
   ```

### Logs

- **Success logs**: `~/Library/Logs/leetcode_notion_sync.log`
- **Error logs**: `~/Library/Logs/leetcode_notion_sync.err`

View live logs:
```bash
tail -f ~/Library/Logs/leetcode_notion_sync.log
```

### Benefits

✅ Runs automatically in the background  
✅ Starts on login/reboot  
✅ Uses minimal resources  
✅ Only syncs new submissions (efficient)  
✅ All output logged for troubleshooting

---

## 🧠 Why This Exists

LeetCode tracks problem stats.
Notion tracks systems.

This bridges both.

* Better analytics
* Custom dashboards
* Topic-wise filtering
* Long-term progress visualization

---

## 📈 Future Improvements

* [ ] Auto-sync via cron
* [ ] Tag normalization
* [ ] Topic analytics
* [ ] Difficulty distribution chart
* [ ] Sync submission runtime & memory
* [ ] Docker support
* [ ] CLI arguments

---

## 🧑‍💻 Author

Sneha Sinha
AI/ML | Systems | Applied Automation
