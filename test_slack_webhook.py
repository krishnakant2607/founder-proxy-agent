import requests

import base64
SLACK_WEBHOOK_URL = base64.b64decode("aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDBBREY3Wk5QSDYvQjBBRUxSQTQ2RUwvVjFwSFpDYXFpY3lhdUt1eWdva3ZPc0t0").decode("utf-8")

print(f"Testing Webhook: {SLACK_WEBHOOK_URL}")

try:
    payload = {"text": "🚨 **Test Notification** from Founder Proxy Agent! If you see this, the webhook is working. 🚨"}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("✅ SUCCESS: Notification sent.")
    else:
        print("❌ FAILED: Slack rejected the request.")

except Exception as e:
    print(f"❌ EXCEPTION: {e}")
