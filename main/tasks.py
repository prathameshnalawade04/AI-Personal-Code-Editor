import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from channels.layers import get_channel_layer
from celery import shared_task

@shared_task
def execute_user_code(code, channel_name):
    # This remains a plain function for Celery signature fallback compatibility,
    # but we will manually invoke the channel_layer asynchronously below.
    pass

# We create an explicit clean async version that runs perfectly inside your consumer loop
async def execute_user_code_async(code, channel_name):
    output_buffer = StringIO()
    channel_layer = get_channel_layer()
    
    try:
        # Redirect stdout and stderr into our memory buffer
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            exec_globals = {
                "__builtins__": __builtins__,
                "__import__": __import__,
            }
            exec_locals = {}
            
            # Run the code snippet
            exec(code, exec_globals, exec_locals)
            
        output = output_buffer.getvalue()
        if not output.strip():
            output = "[Code executed successfully with no print output statements]"
            
    except Exception as e:
        output = f"Runtime Error: {str(e)}"
    finally:
        output_buffer.close()

    # FIX: Use native 'await' directly instead of fighting with async_to_sync!
    await channel_layer.send(
        channel_name,
        {
            "type": "code_result",
            "output": output
        }
    )