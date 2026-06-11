import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def execute_user_code(code, channel_name):
    output_buffer = StringIO()
    
    try:
        # Catch everything printed to stdout/stderr natively
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            # Create a clean sandboxed dictionary for execution context
            local_vars = {}
            exec(code, {"__builtins__": __builtins__}, local_vars)
            
        output = output_buffer.getvalue()
        if not output:
            output = "[Code executed successfully with no output returns]"
            
    except Exception as e:
        # Catch syntax errors or execution runtime crashes cleanly
        output = f"Runtime Error: {str(e)}"
    finally:
        output_buffer.close()

    # Ship it back straight away via Channel Layer
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(channel_name, {
        "type": "code_result",
        "output": output
    })