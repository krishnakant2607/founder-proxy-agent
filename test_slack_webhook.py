import requests

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

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
