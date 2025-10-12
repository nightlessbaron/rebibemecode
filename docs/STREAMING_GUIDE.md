# Streaming Output Guide

## Overview

The Revive Agent now supports **real-time streaming output** both in the terminal and in the web interface. This provides a much better user experience by showing the agent's response as it's being generated.

## Key Features

### 1. **Pretty Terminal Output**
- Parses streaming JSON responses from the Cursor CLI
- Extracts and displays only the text content (`content[0].text`)
- Clean, readable output without raw JSON noise

### 2. **Web Interface Streaming**
- Real-time streaming using Server-Sent Events (SSE)
- Live updates visible in the web interface
- Auto-scrolling to show the latest output
- Beautiful terminal-style display

### 3. **Callback Support**
- Optional callback function for custom handling of streaming text
- Can be used for logging, monitoring, or custom UI updates

## How It Works

### Terminal Streaming

The `ReviveAgent.run_prompt()` method now:

1. Uses `subprocess.Popen` instead of `subprocess.run` to capture streaming output
2. Reads output line by line in real-time
3. Parses each JSON line to extract the text content
4. Prints the text immediately to the console
5. Optionally calls a callback function with each text chunk

**Example:**
```python
from classes.revive_agent import ReviveAgent

agent = ReviveAgent()
response = agent.run_prompt("Write a Python function to calculate factorial")

# Output will stream to console in real-time as it's generated
```

### Web Interface Streaming

The web app now includes:

1. **Streaming Queue**: Each job has a queue to buffer streaming text
2. **SSE Endpoint** (`/stream/<job_id>`): Serves streaming output using Server-Sent Events
3. **Live Display**: The results page connects to the SSE endpoint and displays output in real-time

**How to use:**

1. Start the Flask app:
   ```bash
   python app.py
   ```

2. Submit a job through the web interface

3. View the results page - you'll see live streaming output in the "Live Agent Output" section

## API Changes

### `ReviveAgent.run_prompt()`

**New signature:**
```python
def run_prompt(
    self, 
    prompt: str, 
    timeout: int = 600, 
    stream_callback: Optional[Callable[[str], None]] = None
) -> str:
```

**Parameters:**
- `prompt` (str): The input prompt
- `timeout` (int): Maximum time in seconds (default: 600)
- `stream_callback` (callable, optional): Callback function to receive text chunks

**Returns:**
- `str`: The complete response text

**Example with callback:**
```python
def my_callback(text):
    print(f"[CALLBACK] {text}", end='', flush=True)

agent = ReviveAgent()
response = agent.run_prompt(
    "Explain Python generators", 
    stream_callback=my_callback
)
```

### Utils Functions

All functions in `utils.py` that call `agent.run_prompt()` now accept an optional `stream_callback` parameter:

- `setup_r_base_environment(agent, workdir, GLOBAL_CONTEXT, stream_callback=None)`
- `setup_r_old_environment(agent, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None)`
- `resolve_dependencies(agent, r_base, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None)`
- `verify_complete_integration(agent, r_base, r_old, workdir, GLOBAL_CONTEXT, stream_callback=None)`

## Web Interface Details

### Server-Sent Events Endpoint

**Endpoint:** `GET /stream/<job_id>`

**Response format:** Server-Sent Events (text/event-stream)

**Event types:**
- Regular text chunks: `data: <escaped_text>\n\n`
- Completion signal: `data: [DONE]\n\n`
- Heartbeat: `: heartbeat\n\n` (keeps connection alive)

**Example client code:**
```javascript
const eventSource = new EventSource('/stream/job-id-here');

eventSource.onmessage = function(event) {
    const data = event.data;
    
    if (data === '[DONE]') {
        console.log('Streaming completed');
        eventSource.close();
        return;
    }
    
    // Unescape newlines
    const text = data.replace(/\\n/g, '\n');
    console.log(text);
};
```

### HTML/CSS for Streaming Display

The streaming output is displayed in a terminal-style box with:
- Dark theme (`#1e1e1e` background)
- Monospace font (Courier New)
- Auto-scrolling
- Max height with overflow scroll
- Custom scrollbar styling

## Testing

### Test Streaming in Terminal

Run the test script:
```bash
python test_streaming.py
```

This will send a simple prompt and display the streaming output in the terminal.

### Test Streaming in Web Interface

1. Start the Flask app:
   ```bash
   python app.py
   ```

2. Open browser to `http://localhost:5000`

3. Submit a test job with any GitHub repositories

4. View the results page and watch the live streaming output

## Technical Details

### JSON Parsing

The streaming JSON format from Cursor CLI:
```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "The actual response text here"
      }
    ]
  }
}
```

The parser extracts `message.content[0].text` from each JSON line.

### Queue Management

- Each job gets a `Queue` instance in the `streaming_queues` dictionary
- The agent's callback puts text chunks into the queue
- The SSE endpoint reads from the queue and sends to the client
- `None` is used as a sentinel value to signal the end of streaming

### Error Handling

- JSON parsing errors are caught and ignored (invalid lines skipped)
- Queue errors are caught silently to prevent crashes
- SSE connection errors are handled gracefully in the client

## Troubleshooting

### No streaming output in terminal

**Possible causes:**
- Cursor CLI not installed or not in PATH
- Wrong model specified
- Network issues

**Solution:**
```bash
# Verify Cursor CLI installation
cursor-agent --version

# Test with a simple prompt
python test_streaming.py
```

### No streaming in web interface

**Possible causes:**
- Browser doesn't support Server-Sent Events
- Job not started properly
- Queue not created

**Solution:**
- Use a modern browser (Chrome, Firefox, Safari, Edge)
- Check browser console for errors
- Verify the job is in "running" status

### Streaming stops mid-response

**Possible causes:**
- Timeout exceeded
- Process crashed
- Network interruption

**Solution:**
- Increase timeout value
- Check server logs for errors
- Ensure stable network connection

## Performance Considerations

- **Buffering**: Uses `bufsize=1` for line-buffered output
- **Queue size**: Unbounded queue (use `maxsize` if memory is a concern)
- **SSE timeout**: 1-second timeout on queue reads to send heartbeats
- **Auto-scroll**: Implemented efficiently with `scrollTop = scrollHeight`

## Future Enhancements

Potential improvements:
1. Add streaming progress indicators
2. Support multiple concurrent streams
3. Add stream recording/playback
4. Implement stream pause/resume
5. Add syntax highlighting for code blocks
6. Support rich text/markdown rendering
7. Add export functionality (save stream to file)

## Summary

The streaming feature provides a vastly improved user experience by:
- ✅ Showing progress in real-time
- ✅ Eliminating ugly JSON output
- ✅ Enabling live monitoring in web interface
- ✅ Supporting custom callbacks for extensibility
- ✅ Maintaining backward compatibility

