from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import json

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
                print("📨 Code execution payload received!")
                await self.channel_layer.send(self.channel_name, {
                    "type": "run_code_task",
                    "code": code
                })
            else:
                print(f"✨ Routing to AI Core Engine for action: {action}")
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
        # Import dynamically inside async method context to prevent any load-time blocking
        from .tasks import execute_user_code_async
        await execute_user_code_async(code, self.channel_name)

    async def run_ai_task(self, event):
        action = event["action"]
        code = event["code"]
        from .tasks import generate_ai_response_async
        await generate_ai_response_async(action, code, self.channel_name)

    async def code_result(self, event):
        output = event['output']
        # Send actual stdout data or AI markdown streaming straight to the Monaco layout console
        await self.send(text_data=json.dumps({
            'type': 'stdout',
            'output': output
        }))
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard('code', self.channel_name)
        raise StopConsumer()