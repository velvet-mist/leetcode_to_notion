import requests

url = "https://leetcode.com/graphql"

headers = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "Origin": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0"
}

cookies = {
    "csrftoken": "PASTE_FROM_BROWSER",
    "LEETCODE_SESSION": "PASTE_FROM_BROWSER"
}

payload = {
    "query": """
    query recentAcSubmissions($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        title
        titleSlug
        timestamp
      }
    }
    """,
    "variables": {
        "username": "SnehaSinha05",
        "limit": 10
    }
}

res = requests.post(url, json=payload, headers=headers, cookies=cookies)
print(res.json())
