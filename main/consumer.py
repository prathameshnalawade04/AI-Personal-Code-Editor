from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import json

class Myconsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print(f"🚀 WebSocket Connected: {self.channel_name}")
        await self.channel_layer.group_add("code", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        action = data.get('action')
        code = data.get('code')
        
        if action == 'run':
            print("📨 Code payload received! Processing...")
        else:
            print("✨ Refactoring the code with AI...")
            
        # FIX: Send the task to our custom async runner handler instead of using Celery .delay()
        await self.channel_layer.send(self.channel_name, {
            "type": "run_code_task",
            "code": code
        })

    async def run_code_task(self, event):
        code = event["code"]
        # Import and await our clean async version natively
        from .tasks import execute_user_code_async
        await execute_user_code_async(code, self.channel_name)

    async def code_result(self, event):
        output = event['output']
        # Send actual data to the browser
        await self.send(text_data=json.dumps({
            'type': 'stdout',
            'output': output
        }))
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard('code', self.channel_name)
        raise StopConsumer()