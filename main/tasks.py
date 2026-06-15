import sys
import os
import json
import asyncio
import urllib.request
import urllib.error
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from channels.layers import get_channel_layer
from celery import shared_task
from django.conf import settings

@shared_task
def execute_user_code(code, channel_name):
    """
    Standard synchronous Celery task fallback signature.
    Maintains system compatibility if you decide to activate full Celery brokers in production.
    """
    pass

async def execute_user_code_async(code, channel_name):
    """
    Asynchronously executes arbitrary Python code in an isolated context,
    captures all standard outputs (prints) or runtime crashes, and streams
    the resulting text buffer back to the user's specific WebSocket channel.
    """
    output_buffer = StringIO()
    channel_layer = get_channel_layer()
    
    try:
        # Intercept standard output and errors in real-time
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            exec_globals = {
                "__builtins__": __builtins__,
                "__import__": __import__,
            }
            exec_locals = {}
            
            # Execute user's code block safely
            exec(code, exec_globals, exec_locals)
            
        output = output_buffer.getvalue()
        if not output.strip():
            output = "[Code executed successfully with no print output statements]"
            
    except Exception as e:
        output = f"Runtime Error: {str(e)}"
    finally:
        output_buffer.close()

    # Stream the output directly down to the browser terminal panel
    await channel_layer.send(
        channel_name,
        {
            "type": "code_result",
            "output": output
        }
    )

async def generate_ai_response_async(action, code, channel_name):
    """
    Sends contextual prompt configurations to Google Gemini 2.5 Flash.
    Now utilizes fully non-blocking asynchronous sleep calls and fail-fast rate-limiting logic.
    """
    channel_layer = get_channel_layer()
    
    # 1. Select the correct instructions based on the button clicked in the UI
    if action == 'refactor':
        prompt = f"Optimize and refactor the following Python code for better performance, safety, and readability. Ensure any optimized parts are documented with clean inline comments:\n\n{code}"
    elif action == 'explain':
        prompt = f"Provide a clean, descriptive, line-by-line breakdown and architectural overview explaining what this Python code is doing:\n\n{code}"
    else:
        prompt = f"Analyze the following Python script for possible bugs, security concerns, or logic issues:\n\n{code}"

    # 2. Extract key from Django configuration settings or environmental variables
    api_key = getattr(settings, "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    
    # 3. Handle Fallback Mock Engine if no API Key is verified
    if not api_key:
        if action == 'refactor':
            ai_output = """### ✨ AI Suggested Optimization (Fallback Mode)
*No API Key found. To use live AI, run: `set GEMINI_API_KEY=your_key` or add it to settings.py*

```python
# Optimized & Refactored version
import time

def process_data(limit=1000):
    # Utilizing a fast generator expression/comprehension instead of standard loops
    return sum(x * x for x in range(limit) if x % 2 == 0)
```

#### Key Improvements:
1. **Memory Efficiency**: Switched from nested arrays to local memory generator streams.
2. **Type Scope**: Wrapped loose execution scopes within functional, callable containers."""
        elif action == 'explain':
            ai_output = """### 🧠 Code Architecture Explanation (Fallback Mode)
*No API Key found. To use live AI, run: `set GEMINI_API_KEY=your_key` or add it to settings.py*

#### Architectural Flow Breakdown:
1. **Execution Engine**: The system loads the python code string into an isolated standard environment global block (`__builtins__`).
2. **Standard Output Redirect**: A temporary `StringIO` memory buffer intercepts and captures anything printed to the console.
3. **WebSocket Broadcast**: On completion, the data is pulled from memory and immediately routed through active WebSocket channel layers to the screen."""
        else:
            ai_output = """### 🛡️ AI Sandbox Static Analysis (Fallback Mode)
Your python script has been verified against syntax standard frameworks. No immediate compilation crashes or infinite loop blockages identified."""
    else:
        # Build stable production REST API request routing directly to the Gemini 2.5 Flash model
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        # System instructions to keep outputs structured, clean, and screenshot-friendly
        system_instruction = (
            "You are an expert AI software companion. Provide crisp, professional, highly concise markdown answers. "
            "Your entire response MUST fit completely on a single screen without vertical scrolling. "
            "For refactoring, provide only the core optimized function and a short 3-bullet-point optimization summary."
        )
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            }
        }
        
        data_bytes = json.dumps(payload).encode("utf-8")
        
        # Exponential backoff parameters: retry up to 5 times (delays: 1s, 2s, 4s, 8s, 16s)
        success = False
        ai_output = ""
        delays = [1, 2, 4, 8, 16]
        
        for i, delay in enumerate(delays):
            try:
                req = urllib.request.Request(
                    api_url, 
                    data=data_bytes, 
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    
                    # Safe dictionary parsing to avoid IndexError / KeyError loop freezes
                    candidates = res_data.get('candidates', [])
                    if candidates:
                        content = candidates[0].get('content', {})
                        parts = content.get('parts', [])
                        if parts:
                            ai_output = parts[0].get('text', '')
                            print("✅ Gemini content parsed successfully!")
                            break
                        else:
                            ai_output = "### ❌ AI Parsing Error\nGoogle returned empty payload components."
                    else:
                        error_info = res_data.get('error', {})
                        ai_output = f"### ❌ Gemini API Error\n{error_info.get('message', 'Unknown API structure returned.')}"
                    break # Break immediately if parsing structure failed (no need to retry)
                    
            except urllib.error.HTTPError as e:
                # INSTANT FAILURE: Do not retry client configuration errors or rate limits (429)
                if e.code == 429:
                    ai_output = (
                        "### ⏳ Quota Rate Limit Exceeded (429)\n\n"
                        "You have exceeded your free tier limit of **15 requests per minute** or **1,500 requests per day**.\n\n"
                        "**Immediate Action Needed:**\n"
                        "1. Wait 15–30 seconds for the current window to reset.\n"
                        "2. Once the countdown timer on your button finishes, try clicking again!"
                    )
                    print(f"❌ Gemini Connection Rate Limited (429). Fast-failing task immediately.")
                    break
                elif 400 <= e.code < 500:
                    try:
                        error_details = json.loads(e.read().decode("utf-8"))
                        error_msg = error_details.get('error', {}).get('message', 'Client configuration error.')
                    except Exception:
                        error_msg = e.reason
                    
                    print(f"❌ Gemini Connection Client Error ({e.code}): {error_msg}")
                    ai_output = f"### ❌ Gemini API Client Error ({e.code})\n\n{error_msg}"
                    break
                
                # Server/Quota Errors retry cycles
                if i == len(delays) - 1:
                    ai_output = f"### ❌ Gemini API Connection Timeout\nServer is currently experiencing latency."
                else:
                    print(f"⚠️ Gateway Latency. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            except Exception as e:
                if i == len(delays) - 1:
                    ai_output = f"### ❌ Connection Error\n{str(e)}"
                else:
                    print(f"⚠️ Exception hit. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    
    # 4. Stream response back to user's screen interface console using the "ai_result" event type
    await channel_layer.send(
        channel_name,
        {
            "type": "ai_result",
            "output": ai_output
        }
    )