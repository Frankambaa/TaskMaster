#!/usr/bin/env python3
"""
Test the AI tool clarification system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_tool_executor import AIToolExecutor

def test_clarification_system():
    """Test the AI tool clarification system with various questions"""
    
    # Initialize the executor
    executor = AIToolExecutor()
    
    # Test questions
    test_cases = [
        ("credits", "Should ask for clarification - could mean balance, purchase, or info"),
        ("account", "Should ask for clarification - could mean details, balance, settings"),
        ("What is my current credit balance?", "Should be clear - specific request"),
        ("How do I purchase more credits?", "Should be clear - specific action"),
        ("status", "Should ask for clarification - could mean multiple things"),
        ("show me my account", "Should be clear - specific request"),
        ("token", "Should ask for clarification - could mean balance or info"),
        ("balance", "Should ask for clarification - could mean credit balance or account balance"),
    ]
    
    print("Testing AI Tool Clarification System")
    print("=" * 50)
    
    for question, expected_behavior in test_cases:
        print(f"\nQuestion: '{question}'")
        print(f"Expected: {expected_behavior}")
        
        try:
            # Test the tool selection
            should_use, tool_name, tool_args, clarification = executor.should_use_tools(question)
            
            if clarification:
                print(f"✓ Clarification needed: {clarification}")
            elif should_use:
                print(f"✓ Tool selected: {tool_name} with args: {tool_args}")
            else:
                print("✓ No tools needed - will use general knowledge")
                
        except Exception as e:
            print(f"✗ Error: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_clarification_system()