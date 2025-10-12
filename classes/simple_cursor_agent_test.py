#!/usr/bin/env python3
"""
python3 classes/simple_cursor_agent_test.py
"""

from cursor_cli_agent import CursorCLIAgent

def test_summarize_project():
    """Simple test to summarize this project using CursorCLIAgent."""
    
    print("Testing CursorCLIAgent with 'summarize this project' command...")
    print("-" * 60)
    
    try:
        # Initialize the agent
        agent = CursorCLIAgent()
        print(f"✓ CursorCLIAgent initialized with model: {agent.get_model()}")
        
        # Simple test prompt
        prompt = "Summarize this project"
        print(f"Sending prompt: '{prompt}'")
        print("-" * 60)
        
        # Run the prompt
        response = agent.run_prompt(prompt)
        
        print("Response:")
        print(response)
        print("-" * 60)
        print("✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_summarize_project()
    if not success:
        print("\nNote: Make sure Cursor CLI is installed:")
        print("curl https://cursor.com/install -fsS | bash")
