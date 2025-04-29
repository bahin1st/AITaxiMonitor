

from django.urls import re_path
from .consumers import TaxiReceiveConsumer, TaxiUpdateConsumer  

websocket_urlpatterns = [
   re_path(r'ws/taxi/receive/$', TaxiReceiveConsumer.as_asgi()),
    re_path(r'ws/taxi/updates/$', TaxiUpdateConsumer.as_asgi()),

]
