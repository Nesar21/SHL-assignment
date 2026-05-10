import requests
import time

URL = "http://127.0.0.1:8001/chat"

payload = {
  "messages": [
    {
      "role": "user",
      "content": "What is the legal framework for pre-employment testing in the EU under GDPR?"
    }
  ]
}

try:
    resp = requests.post(URL, json=payload)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
except Exception as e:
    print("Error:", e)

