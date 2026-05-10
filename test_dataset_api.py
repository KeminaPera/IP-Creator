import requests
import json

BASE_URL = "http://localhost:8000"

# Login
print("=== Testing Dataset API ===\n")
login_res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
token = login_res.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Login successful\n")

# Test 1: List datasets
print("Test 1: GET /api/v1/datasets")
try:
    res = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Response: {json.dumps(res.json(), indent=2, ensure_ascii=False)}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test 2: Get IP list (to get IP asset ID)
print("Test 2: GET /api/v1/ip/list")
try:
    res = requests.get(f"{BASE_URL}/api/v1/ip/list", headers=headers)
    print(f"Status: {res.status_code}")
    ips = res.json()["data"]["items"]
    if ips:
        ip_id = ips[0]["id"]
        print(f"Using IP asset ID: {ip_id} ({ips[0]['name']})\n")
    else:
        print("No IP assets found, cannot continue tests\n")
        ip_id = None
except Exception as e:
    print(f"Error: {e}\n")
    ip_id = None

# Test 3: Create dataset (if we have IP)
if ip_id:
    print("Test 3: POST /api/v1/datasets")
    try:
        res = requests.post(f"{BASE_URL}/api/v1/datasets", headers=headers, json={
            "ip_asset_id": ip_id,
            "name": "测试数据集 v1",
            "description": "用于测试的数据集"
        })
        print(f"Status: {res.status_code}")
        print(f"Response: {json.dumps(res.json(), indent=2, ensure_ascii=False)}\n")
        
        if res.status_code == 201:
            dataset_id = res.json()["data"]["id"]
            
            # Test 4: Get dataset detail
            print("Test 4: GET /api/v1/datasets/{id}")
            res = requests.get(f"{BASE_URL}/api/v1/datasets/{dataset_id}", headers=headers)
            print(f"Status: {res.status_code}")
            print(f"Response: {json.dumps(res.json(), indent=2, ensure_ascii=False)}\n")
            
            # Test 5: Get stats
            print("Test 5: GET /api/v1/datasets/{id}/stats")
            res = requests.get(f"{BASE_URL}/api/v1/datasets/{dataset_id}/stats", headers=headers)
            print(f"Status: {res.status_code}")
            print(f"Response: {json.dumps(res.json(), indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

print("=== Tests Complete ===")
