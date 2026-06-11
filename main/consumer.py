from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from .tasks import execute_user_code
import json
class Myconsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print(self.channel_name)
        await self.channel_layer.group_add("code",self.channel_name)

    
    async def receive(self, text_data = None, bytes_data = None):
        data=json.loads(text_data)
        action=data.get('action')
        code=data.get('code')
        if action=='run':
            print("the code is running...")
        else:
            print("Refactoring the code with AI....")
        execute_user_code.delay(code,self.channel_name)
    async def code_result(self, event):
        output = event['output']
    # Send actual data to the browser
        await self.send(text_data=json.dumps({
        'type': 'stdout',
        'output': output
    }))
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard('code',self.channel_name)

