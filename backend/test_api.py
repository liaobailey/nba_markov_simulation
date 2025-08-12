#!/usr/bin/env python3
"""
Test script for the NBA Transition Matrix Adjustments API
"""

import requests
import json

# Base URL for local testing
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_teams():
    """Test the teams endpoint"""
    print("\n🏀 Testing teams endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/teams")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            teams = response.json()
            print(f"Found {len(teams['teams'])} teams")
            print(f"Sample teams: {teams['teams'][:5]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_generate_adjustments():
    """Test the generate adjustments endpoint"""
    print("\n📊 Testing generate adjustments endpoint...")
    try:
        payload = {
            "team": "LAC",
            "season": "2024-25",
            "adjustment_percentage": 5.0
        }
        response = requests.post(f"{BASE_URL}/generate-adjustments", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Successfully generated adjustments CSV")
            # Save the CSV
            with open("test_adjustments.csv", "wb") as f:
                f.write(response.content)
            print("💾 Saved as test_adjustments.csv")
        else:
            print(f"Error response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing NBA Transition Matrix Adjustments API")
    print("=" * 50)
    
    tests = [
        test_health,
        test_teams,
        test_generate_adjustments
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    for i, result in enumerate(results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"Test {i+1}: {status}")
    
    if all(results):
        print("\n🎉 All tests passed! API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
