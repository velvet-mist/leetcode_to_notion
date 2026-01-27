import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

CSRF = os.getenv("LEETCODE_CSRF")
SESSION = os.getenv("LEETCODE_SESSION")

URL = "https://leetcode.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "Origin": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0"
}

COOKIES = {
    "csrftoken": CSRF,
    "LEETCODE_SESSION": SESSION
}

QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    title
    titleSlug
    timestamp
  }
}
"""

payload = {
    "query": QUERY,
    "variables": {
        "username": "SnehaSinha05",
        "limit": 10
    }
}

res = requests.post(URL, json=payload, headers=HEADERS, cookies=COOKIES)

if res.status_code != 200:
    raise Exception(res.text)

data = res.json()["data"]["recentAcSubmissionList"]

for p in data:
    date = datetime.fromtimestamp(int(p["timestamp"])).date()
    print(f"{p['title']} | {date} | https://leetcode.com/problems/{p['titleSlug']}/")
