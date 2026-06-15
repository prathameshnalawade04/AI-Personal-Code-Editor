import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer

class Myconsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print(f"🚀 WebSocket Connected: {self.channel_name}")
        await self.channel_layer.group_add("code", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            action = data.get('action')  # Expected: 'run', 'refactor', 'explain'
            code = data.get('code')
            
            if action == 'run':
                print(f"📨 Code execution payload received on {self.channel_name}!")
                await self.channel_layer.send(self.channel_name, {
                    "type": "run_code_task",
                    "code": code
                })
            else:
                print(f"✨ Routing action '{action}' to AI Core Engine...")
                await self.channel_layer.send(self.channel_name, {
                    "type": "run_ai_task",
                    "action": action,
                    "code": code
                })
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'stdout',
                'output': f"Error parsing incoming JSON payload: {str(e)}"
            }))

    async def run_code_task(self, event):
        code = event["code"]
        # Delaying import to avoid circular dependency issues
        from .tasks import execute_user_code_async
        await execute_user_code_async(code, self.channel_name)

    async def run_ai_task(self, event):
        action = event["action"]
        code = event["code"]
        # Delaying import to avoid circular dependency issues
        from .tasks import generate_ai_response_async
        await generate_ai_response_async(action, code, self.channel_name)

    async def code_result(self, event):
        output = event['output']
        await self.send(text_data=json.dumps({
            'type': 'stdout',
            'output': output
        }))

    async def ai_result(self, event):
        output = event['output']
        await self.send(text_data=json.dumps({
            'type': 'ai_response',
            'output': output
        }))
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard('code', self.channel_name)
        print(f"🛑 WebSocket Disconnected: {self.channel_name}")
        raise StopConsumer()


# =====================================================================
# STEP 3: main/tasks.py
# =====================================================================
import sys
import io
import google.generativeai as genai
from channels.layers import get_channel_layer
from django.conf import settings

# Configure Gemini API securely using settings
# Make sure GEMINI_API_KEY is in your editor/settings.py
genai.configure(api_key=getattr(settings, 'GEMINI_API_KEY', 'dummy_key'))

async def generate_ai_response_async(action, code, channel_name):
    """Handles communicating with Gemini API and dispatching the result back."""
    channel_layer = get_channel_layer()
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    try:
        # Construct the prompt based on user action
        prompt = f"Please deeply analyze and {action} the following python code. Format your response in clean Markdown:\n\n{code}"
        
        # Execute asynchronous call to Gemini
        response = await model.generate_content_async(prompt)
        gemini_parsed_text = response.text
        
        print("✅ Gemini content parsed successfully!")

        # Push the payload back to the channel layer to trigger 'ai_result' in consumers.py
        await channel_layer.send(
            channel_name,
            {
                "type": "ai_result",  
                "output": gemini_parsed_text 
            }
        )
        
    except Exception as e:
        print(f"❌ Error in Gemini API task: {str(e)}")
        # Push error payload back to the frontend so the UI doesn't hang
        await channel_layer.send(
            channel_name,
            {
                "type": "ai_result",
                "output": f"**Error generating AI response:**\n{str(e)}"
            }
        )

async def execute_user_code_async(code, channel_name):
    """Executes standard python code and dispatches standard out back to the consumer."""
    channel_layer = get_channel_layer()
    
    # Capture standard output
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        # Execute the python string
        exec(code, {})
        output = redirected_output.getvalue()
    except Exception as e:
        output = f"Execution Error: {str(e)}"
    finally:
        # Restore standard output immediately to prevent memory leaks
        sys.stdout = old_stdout

    # Push the standard output payload back to 'code_result' in consumers.py
    await channel_layer.send(
        channel_name,
        {
            "type": "code_result",
            "output": output
        }
    )