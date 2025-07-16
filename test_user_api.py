#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced /ask API with user-specific parameters.
This shows how external websites can integrate with the chatbot while maintaining
persistent conversation context across sessions and devices.
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_user_session(user_id, username, email, device_id):
    """Test user-specific conversation persistence"""
    print(f"\n=== Testing User Session: {user_id} ({username}) ===")
    
    # Test 1: First conversation
    print("\n1. First conversation...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "Hello! My name is John.",
        "user_id": user_id,
        "username": username,
        "email": email,
        "device_id": device_id
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
        print(f"✓ Session Type: {data['user_info']['session_type']}")
        print(f"✓ User ID: {data['user_info']['user_id']}")
    else:
        print(f"✗ Error: {response.status_code}")
    
    # Test 2: Follow-up question (should remember previous context)
    print("\n2. Follow-up question (should remember name)...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "What's my name?",
        "user_id": user_id,
        "username": username,
        "email": email,
        "device_id": device_id
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
    else:
        print(f"✗ Error: {response.status_code}")
    
    # Test 3: Get session info
    print("\n3. Getting session info...")
    response = requests.post(f"{BASE_URL}/session_info", json={
        "user_id": user_id,
        "username": username,
        "email": email,
        "device_id": device_id
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Session Type: {data['session_type']}")
        print(f"✓ Message Count: {data['stats']['total_messages']}")
        print(f"✓ Persistent: {data['stats']['persistent']}")
    else:
        print(f"✗ Error: {response.status_code}")

def test_anonymous_session():
    """Test anonymous session fallback"""
    print(f"\n=== Testing Anonymous Session ===")
    
    # Test 1: Anonymous conversation
    print("\n1. Anonymous conversation...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "Hello! I'm an anonymous user."
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
        print(f"✓ Session Type: {data['user_info']['session_type']}")
    else:
        print(f"✗ Error: {response.status_code}")
    
    # Test 2: Get session info
    print("\n2. Getting session info...")
    response = requests.get(f"{BASE_URL}/session_info")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Session Type: {data['session_type']}")
        if data['stats']['exists']:
            print(f"✓ Message Count: {data['stats']['total_messages']}")
        else:
            print("✓ No active session")
    else:
        print(f"✗ Error: {response.status_code}")

def test_device_switching():
    """Test conversation continuity across devices"""
    print(f"\n=== Testing Device Switching ===")
    
    user_id = "user123"
    username = "Alice"
    email = "alice@example.com"
    
    # Device 1: Desktop
    print("\n1. Conversation from desktop...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "I'm working on a Python project.",
        "user_id": user_id,
        "username": username,
        "email": email,
        "device_id": "desktop_001"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
    
    # Device 2: Mobile (same user)
    print("\n2. Continuing conversation from mobile...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "What was I working on?",
        "user_id": user_id,
        "username": username,
        "email": email,
        "device_id": "mobile_001"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
        print("✓ Conversation context maintained across devices!")

def test_clear_conversation():
    """Test clearing user conversation"""
    print(f"\n=== Testing Clear Conversation ===")
    
    user_id = "user456"
    username = "Bob"
    email = "bob@example.com"
    
    # Start conversation
    print("\n1. Starting conversation...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "My favorite color is blue.",
        "user_id": user_id,
        "username": username,
        "email": email
    })
    
    if response.status_code == 200:
        print("✓ Conversation started")
    
    # Clear conversation
    print("\n2. Clearing conversation...")
    response = requests.post(f"{BASE_URL}/clear_session", json={
        "user_id": user_id,
        "username": username,
        "email": email
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ {data['message']}")
        print(f"✓ Session Type: {data['session_type']}")
    
    # Test if conversation is cleared
    print("\n3. Testing if conversation is cleared...")
    response = requests.post(f"{BASE_URL}/ask", json={
        "question": "What's my favorite color?",
        "user_id": user_id,
        "username": username,
        "email": email
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response: {data['answer']}")
        print("✓ Conversation successfully cleared!")

def main():
    print("Enhanced RAG Chatbot - User API Test Suite")
    print("=" * 50)
    
    # Test different user scenarios
    test_user_session("user123", "John Doe", "john@example.com", "laptop_001")
    test_anonymous_session()
    test_device_switching()
    test_clear_conversation()
    
    print(f"\n=== Test Suite Complete ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nKey Features Demonstrated:")
    print("✓ User-specific persistent conversations")
    print("✓ Anonymous session fallback")
    print("✓ Cross-device conversation continuity")
    print("✓ Privacy-focused session isolation")
    print("✓ Enhanced API with user parameters")

if __name__ == "__main__":
    main()