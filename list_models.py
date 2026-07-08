import requests
import os
from dotenv import load_dotenv
load_dotenv()

fireworks_api_key = os.getenv("FIREWORKS_API_KEY")

response = requests.get(
    "https://api.fireworks.ai/inference/v1/models",
    headers={"Authorization": f"Bearer {fireworks_api_key}"}
)
result = response.json()

print("Status:", response.status_code)
print("\nAvailable models:")
if "data" in result:
    for model in result["data"]:
        if "gemma" in model["id"].lower():
            print(" GEMMA:", model["id"])
    print("\nAll models:")
    for model in result["data"]:
        print(" ", model["id"])
else:
    print(result)
