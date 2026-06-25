import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.agent import Agent

client = TestClient(app)

def test_api():
    print("Testing GET /")
    res = client.get("/")
    print("Health Check:", res.status_code, res.json())
    
    print("\nTesting GET /api/agents/ without auth")
    res = client.get("/api/agents/")
    print("Agents status:", res.status_code)
    try:
        print("Agents response:", res.json())
    except:
        print("Agents response:", res.text)

if __name__ == '__main__':
    test_api()
