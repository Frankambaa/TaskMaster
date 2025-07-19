#!/usr/bin/env python3
"""
Test script for webhook integration functionality
Tests both incoming and outgoing webhook flows
"""

import requests
import json
import time
from datetime import datetime

# Configuration
CHATBOT_BASE_URL = "http://localhost:5000"  # Change to your deployment URL
WEBHOOK_SECRET = "your_webhook_secret_here"  # Change to your actual secret

def test_webhook_config():
    """Test webhook configuration management"""
    print("🔧 Testing webhook configuration...")
    
    # Create webhook configuration
    config_data = {
        "name": "Test Integration",
        "provider": "freshchat",
        "outgoing_webhook_url": "https://httpbin.org/post",  # Test endpoint
        "auth_token": "test_bearer_token",
        "custom_headers": {
            "X-API-Key": "test_api_key",
            "X-Platform": "freshchat"
        },
        "timeout_seconds": 30,
        "retry_attempts": 3,
        "is_active": True
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/config",
        json=config_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print("✅ Webhook configuration created successfully")
        return response.json()['config']['id']
    else:
        print(f"❌ Failed to create webhook config: {response.text}")
        return None

def test_incoming_webhook():
    """Test incoming webhook message processing"""
    print("\n📨 Testing incoming webhook...")
    
    # Sample webhook data from third-party platform
    webhook_data = {
        "user_id": "test_user_123",
        "username": "John Test",
        "message": "Hello, I need help with my account",
        "platform": "freshchat",
        "conversation_id": "conv_test_456",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "channel": "web",
            "user_agent": "Mozilla/5.0 Test Browser",
            "custom_fields": {
                "priority": "high",
                "department": "support"
            }
        }
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json=webhook_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_SECRET}"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Incoming webhook processed successfully")
        print(f"📝 Response: {result['response']['answer'][:100]}...")
        print(f"🆔 Message ID: {result['message_id']}")
        return result
    else:
        print(f"❌ Failed to process incoming webhook: {response.text}")
        return None

def test_live_chat_transfer():
    """Test live chat transfer functionality"""
    print("\n👥 Testing live chat transfer...")
    
    # Message requesting live chat
    webhook_data = {
        "user_id": "test_user_456",
        "username": "Jane Support",
        "message": "I want to talk to a live agent please",
        "platform": "freshchat",
        "conversation_id": "conv_live_789",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "channel": "web",
            "priority": "urgent"
        }
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json=webhook_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_SECRET}"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Live chat transfer request processed")
        print(f"📝 Response: {result['response']['answer']}")
        
        # Check if live chat was triggered
        if "agent" in result['response']['answer'].lower() or "transfer" in result['response']['answer'].lower():
            print("🎯 Live chat transfer detected in response")
        
        return result
    else:
        print(f"❌ Failed to process live chat transfer: {response.text}")
        return None

def test_webhook_messages_api():
    """Test webhook messages retrieval"""
    print("\n📋 Testing webhook messages API...")
    
    response = requests.get(
        f"{CHATBOT_BASE_URL}/api/webhook/messages",
        params={
            "platform": "freshchat",
            "per_page": 10
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Retrieved {len(result['messages'])} webhook messages")
        print(f"📊 Total messages: {result['total']}")
        
        # Show recent messages
        for msg in result['messages'][:3]:
            print(f"   📨 {msg['message_type']}: {msg['message_content'][:50]}...")
        
        return result
    else:
        print(f"❌ Failed to retrieve webhook messages: {response.text}")
        return None

def test_api_tool_integration():
    """Test API tool integration through webhook"""
    print("\n🛠️ Testing API tool integration...")
    
    # Message that should trigger API tool
    webhook_data = {
        "user_id": "test_user_789",
        "username": "API Test User",
        "message": "What is my current credit balance?",
        "platform": "freshchat",
        "conversation_id": "conv_api_test",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "channel": "api_test"
        }
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json=webhook_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_SECRET}"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ API tool integration test completed")
        print(f"📝 Response: {result['response']['answer']}")
        print(f"🏷️ Response Type: {result['response'].get('response_type', 'unknown')}")
        return result
    else:
        print(f"❌ Failed to test API tool integration: {response.text}")
        return None

def test_rag_knowledge_base():
    """Test RAG knowledge base through webhook"""
    print("\n📚 Testing RAG knowledge base...")
    
    # Message that should use knowledge base
    webhook_data = {
        "user_id": "test_user_101",
        "username": "Knowledge Test User",
        "message": "How do I reset my password?",
        "platform": "freshchat",
        "conversation_id": "conv_knowledge_test",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "channel": "knowledge_test"
        }
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json=webhook_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_SECRET}"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ RAG knowledge base test completed")
        print(f"📝 Response: {result['response']['answer'][:100]}...")
        print(f"🏷️ Response Type: {result['response'].get('response_type', 'unknown')}")
        return result
    else:
        print(f"❌ Failed to test RAG knowledge base: {response.text}")
        return None

def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n🚫 Testing error handling...")
    
    # Test with missing required fields
    invalid_data = {
        "message": "This is missing required fields"
    }
    
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json=invalid_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 400:
        print("✅ Error handling works correctly for invalid requests")
        print(f"📝 Error response: {response.json()['error']}")
    else:
        print(f"❌ Expected 400 error, got {response.status_code}: {response.text}")
    
    # Test with empty payload
    response = requests.post(
        f"{CHATBOT_BASE_URL}/api/webhook/incoming",
        json={},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 400:
        print("✅ Empty payload handling works correctly")
    else:
        print(f"❌ Expected 400 error for empty payload, got {response.status_code}")

def run_performance_test():
    """Test webhook performance with multiple requests"""
    print("\n⚡ Running performance test...")
    
    start_time = time.time()
    success_count = 0
    total_requests = 10
    
    for i in range(total_requests):
        webhook_data = {
            "user_id": f"perf_test_user_{i}",
            "username": f"Performance Test User {i}",
            "message": f"Performance test message {i}",
            "platform": "performance_test",
            "conversation_id": f"conv_perf_{i}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(
            f"{CHATBOT_BASE_URL}/api/webhook/incoming",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            success_count += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Performance test completed:")
    print(f"   📊 Successful requests: {success_count}/{total_requests}")
    print(f"   ⏱️ Total time: {duration:.2f} seconds")
    print(f"   🚀 Average response time: {duration/total_requests:.2f} seconds")

def main():
    """Run all webhook integration tests"""
    print("🧪 Starting Webhook Integration Test Suite")
    print("=" * 50)
    
    try:
        # Test webhook configuration
        config_id = test_webhook_config()
        
        # Test basic functionality
        test_incoming_webhook()
        test_live_chat_transfer()
        test_webhook_messages_api()
        
        # Test AI functionality
        test_api_tool_integration()
        test_rag_knowledge_base()
        
        # Test error handling
        test_error_handling()
        
        # Performance test
        run_performance_test()
        
        print("\n🎉 All webhook integration tests completed!")
        print("Check the admin panel for webhook message history and logs.")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {CHATBOT_BASE_URL}")
        print("   Please ensure the application is running and accessible.")
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")

if __name__ == "__main__":
    main()