import requests
import json

# Your N8N webhook URL
url = "http://localhost:5678/webhook/keyword-research"

# Input data
data = {
    "seed_keyword": "global internship",
    "max_keywords": 50
}

print("🚀 Triggering N8N workflow...")
print(f"URL: {url}")
print(f"Input: {json.dumps(data, indent=2)}\n")

try:
    response = requests.post(url, json=data, timeout=300)
    result = response.json()
    
    print("✅ Success!\n")
    print(json.dumps(result, indent=2))
    
    # Save results
    with open('workflow_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n💾 Results saved to: workflow_results.json")
    
except Exception as e:
    print(f"❌ Error: {e}")