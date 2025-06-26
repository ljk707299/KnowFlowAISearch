import requests
import json

url = "https://api.bochaai.com/v1/web-search"

payload = json.dumps({
  "query": "天空为什么是蓝色的？",
  "summary": True,
  "count": 10,
  "page": 1
})

headers = {
  'Authorization': 'Bearer sk-58ce4c22ea5b4a21b514c4571b2da0e9',
  'Content-Type': 'application/json'
}

response = requests.post(url, headers=headers, data=payload)

print(response.json())