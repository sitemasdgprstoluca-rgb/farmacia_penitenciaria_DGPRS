#!/usr/bin/env python
"""Test login endpoint."""
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

url = 'http://127.0.0.1:8000/api/token/'
data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
headers = {'Content-Type': 'application/json'}

print(f"Testing POST {url}")
print(f"Data: {data.decode()}")

try:
    req = Request(url, data=data, headers=headers)
    response = urlopen(req, timeout=10)
    result = json.loads(response.read().decode())
    print(f"\nStatus: {response.status}")
    print(f"Access Token: {result.get('access', 'N/A')[:50]}...")
    print(f"Refresh Token: {result.get('refresh', 'N/A')[:50]}...")
except HTTPError as e:
    print(f"\nHTTP Error {e.code}: {e.reason}")
    print(f"Response: {e.read().decode()}")
except URLError as e:
    print(f"\nURL Error: {e.reason}")
except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
