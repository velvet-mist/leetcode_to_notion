import requests

from config import NOTION_PARENT_PAGE_ID, NOTION_TOKEN

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
}

res = requests.get(
    f"https://api.notion.com/v1/pages/{NOTION_PARENT_PAGE_ID}",
    headers=headers
)

print(res.status_code)
print(res.text)
