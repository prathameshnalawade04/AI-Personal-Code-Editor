from django.urls import path
from .consumer import *

websocket_urlpatterns=[path('ws/execute/',Myconsumer.as_asgi())]