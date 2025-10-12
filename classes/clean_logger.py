import json
import sys
from typing import Optional, Dict, Any, Callable, Generator
from collections import deque
import weave

def stream_json_output(process_or_lines, stream_callback=None, cache_size=15):
    """
    Streams assistant messages from JSON-line output.
    Keeps last few printed texts; if a new line matches the suffix of buffer, 
    prints only a newline instead of repeating content.
    """

    # Accept either process with stdout or list of JSON lines
    if hasattr(process_or_lines, "stdout"):
        lines = process_or_lines.stdout
    else:
        lines = process_or_lines

    last_prints = deque(maxlen=cache_size)
    buffer = ""
    
    # Stats tracking
    tool_call_count = 0
    token_count = 0
    full_response = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        full_response = full_response + line

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "assistant":
            message = data.get("message", {})
            content = message.get("content", [])
            if not content:
                continue

            text = content[0].get("text", "")
            if not text:
                continue

            # If new text contains our accumulated buffer as prefix → treat as final message
            if buffer and text.startswith(buffer):
                # This is the complete message, skip printing since we already printed the parts
                print()
                if stream_callback:
                    stream_callback("\n")
                # Reset buffer since we got the complete message
                buffer = ""
            else:
                print(text, end="", flush=True)
                if stream_callback:
                    stream_callback(text)
                last_prints.append(text)
                buffer += text
        
        elif data.get("type") == "tool_call":
            # Display tool call messages in a readable format
            subtype = data.get("subtype", "")
            tool_call = data.get("tool_call", {})
            
            if subtype == "started":
                # Count the tool call
                tool_call_count += 1
                
                # Extract tool information
                tool_info = format_tool_call(tool_call)
                if tool_info:
                    msg = f"🔧 {tool_info}"
                    print(msg, flush=True)
                    if stream_callback:
                        stream_callback(msg)
        else:
            msg = f"🔧 {data.get('message', '')}"
            print(msg, flush=True)
            if stream_callback:
                stream_callback(msg)
        
        # Track token usage if provided
        usage = data.get("usage", {})
        if "total_tokens" in usage:
            token_count = usage["total_tokens"]
        elif "completion_tokens" in usage:
            token_count += usage.get("completion_tokens", 0)

    # Done streaming, ensure newline
    print(flush=True)
    
    # Estimate tokens if not provided by the stream
    if token_count == 0 and full_response:
        # Rough estimate: ~4 characters per token (common heuristic)
        token_count = len(full_response) // 4
    
    # Display stats
    stats_msg = f"\n📊 Usage Stats: {tool_call_count} tool calls | ~{token_count} tokens\n"
    print(stats_msg)
    if stream_callback:
        stream_callback(stats_msg)
    
    # Return stats for further processing if needed
    return {
        "tool_calls": tool_call_count,
        "tokens": token_count,
        "full_response": full_response
    }

@weave.op()
def format_tool_call(tool_call: Dict[str, Any]) -> Optional[str]:
    """
    Format a tool call into a human-readable string.

    Args:
        tool_call: The tool call dictionary from the JSON stream

    Returns:
        Formatted string describing the tool call, or None if not relevant
    """
    # Check for different tool types
    if "readToolCall" in tool_call:
        path = tool_call["readToolCall"].get("args", {}).get("path", "")
        with weave.attributes({"tool_type": "read", "path": path}):
            return f"Reading file: {path}"

    elif "editToolCall" in tool_call:
        path = tool_call["editToolCall"].get("args", {}).get("path", "")
        with weave.attributes({"tool_type": "edit", "path": path}):
            return f"Editing file: {path}"

    elif "writeToolCall" in tool_call:
        path = tool_call["writeToolCall"].get("args", {}).get("path", "")
        with weave.attributes({"tool_type": "write", "path": path}):
            return f"Writing file: {path}"

    elif "shellToolCall" in tool_call:
        cmd = tool_call["shellToolCall"].get("args", {}).get("command", "")
        # Truncate long commands
        cmd_display = cmd
        with weave.attributes({"tool_type": "shell", "command": cmd}):
            return f"Running command: {cmd_display}"

    elif "lsToolCall" in tool_call:
        path = tool_call["lsToolCall"].get("args", {}).get("path", "")
        with weave.attributes({"tool_type": "ls", "path": path}):
            return f"Listing directory: {path}"

    elif "grepToolCall" in tool_call:
        pattern = tool_call["grepToolCall"].get("args", {}).get("pattern", "")
        with weave.attributes({"tool_type": "grep", "pattern": pattern}):
            return f"Searching for: {pattern}"

    elif "codebaseSearchToolCall" in tool_call:
        query = tool_call["codebaseSearchToolCall"].get("args", {}).get("query", "")
        query_display = query
        with weave.attributes({"tool_type": "codebase_search", "query": query}):
            return f"Searching codebase: {query_display}"

    # Return None for other tool types we don't want to display
    with weave.attributes({"tool_type": "unknown", "tool_call": str(tool_call)}):
        return None

if __name__ == "__main__":
    # Test input lines
    lines = [
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I\'ll help you analyze"}]},"session_id":"c67742c5"}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":" the R_base repository ("}]},"session_id":"c67742c5"}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"stable-baselines3) and set"}]},"session_id":"c67742c5"}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":" up the necessary environment. Let me start by exploring"}]},"session_id":"c67742c5"}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":" the repository structure and understanding what it\'s about."}]},"session_id":"c67742c5"}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I\'ll help you analyze the R_base repository (stable-baselines3) and set up the necessary environment. Let me start by exploring the repository structure and understanding what it\'s about."}]},"session_id":"c67742c5"}'

        # Some tools calls
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"codebaseSearchToolCall","args":{"query":"stable-baselines3"}}}',
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"lsToolCall","args":{"path":"."}}}',
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"readToolCall","args":{"path":"README.md"}}}',
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"readToolCall","args":{"path":"LICENSE"}}}',
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"readToolCall","args":{"path":"CONTRIBUTING.md"}}}',
        '{"type":"tool_call","subtype":"started","tool_call":{"name":"readToolCall","args":{"path":"CODE_OF_CONDUCT.md"}}}',
    ]

    print("=== Stream JSON Output Test ===")
    stream_json_output(lines)