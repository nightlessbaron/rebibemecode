#!/usr/bin/env python3
"""
Simple test script to demonstrate streaming output from the Cursor CLI agent.
"""

from classes.cursor_cli_agent import CursorCLIAgent

def test_streaming():
    """Test the streaming functionality with a simple prompt."""
    print("Initializing Cursor CLI Agent...")
    agent = CursorCLIAgent()
    
    print("\n" + "="*80)
    print("Testing streaming output:")
    print("="*80 + "\n")
    
    # Simple test prompt
    prompt = "Write a short poem about coding in Python (4 lines max)."
    
    try:
        response = agent.run_prompt(prompt, timeout=120)
        print("\n" + "="*80)
        print("Full response received:")
        print("="*80)
        print(response)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_streaming()

