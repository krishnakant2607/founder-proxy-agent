import requests
import json

OPENROUTER_API_KEY = "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"

print("Sending request to OpenRouter...")

try:
    response = requests.post(
      url="https://openrouter.ai/api/v1/chat/completions",
      headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501", 
        "X-Title": "Figr Hiring Agent", 
      },
      data=json.dumps({
        "model": "liquid/lfm-2.5-1.2b-thinking:free",
        "messages": [
          {
            "role": "user",
            "content": "What is the capital of France? Answer in one word."
          }
        ]
      })
    )

    if response.status_code == 200:
        print("Success! Response:")
        print(response.json())
    else:
        print(f"Error {response.status_code}:")
        print(response.text)

except Exception as e:
    print(f"Exception occurred: {e}")
