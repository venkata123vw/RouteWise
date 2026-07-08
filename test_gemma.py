import requests
import os
from dotenv import load_dotenv
load_dotenv()

fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
fireworks_url = "https://api.fireworks.ai/inference/v1/chat/completions"
fireworks_headers = {
    "Authorization": f"Bearer {fireworks_api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "accounts/fireworks/models/gemma-4-26b-a4b-it",
    "messages": [
        {
            "role": "system",
            "content": "Classify the query as simple or complex. Reply with one word only: simple or complex."
        },
        {"role": "user", "content": "What is 2+2?"}
    ],
    "max_tokens": 10
}

response = requests.post(fireworks_url, headers=fireworks_headers, json=data)
result = response.json()
print("Full response:")
print(result)