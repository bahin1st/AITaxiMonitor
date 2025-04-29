# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class TaxiConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract taxi plate from URL path if available
        self.taxi_plate = self.scope['url_route']['kwargs'].get('taxi_plate', None)
        
        if self.taxi_plate:
            # Join a specific taxi group
            self.group_name = f'taxi_{self.taxi_plate}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
        else:
            # Join general taxi group for connections without a specific taxi
            self.group_name = 'taxi_all'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Send initial status message
        await self.send(text_data=json.dumps({
            'status': 'connected',
            'taxi_plate': self.taxi_plate or 'all'
        }))

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle ping messages for keeping connection alive
        if text_data == "ping":
            await self.send(text_data="pong")
            return
        
        try:
            # Process incoming messages (if any)
            data = json.loads(text_data)
            
            # Example: handle client requesting specific taxi data
            if data.get('action') == 'subscribe' and data.get('taxi_plate'):
                new_plate = data.get('taxi_plate')
                
                # Leave current group
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
                
                # Join new taxi-specific group
                self.taxi_plate = new_plate
                self.group_name = f'taxi_{new_plate}'
                await self.channel_layer.group_add(
                    self.group_name,
                    self.channel_name
                )
                
                await self.send(text_data=json.dumps({
                    'status': 'subscribed',
                    'taxi_plate': new_plate
                }))
            
        except json.JSONDecodeError:
            # Not JSON, ignore or handle accordingly
            pass

    # Handler for taxi update messages from the server
    async def taxi_update(self, event):
        taxi_data = event['data']
        
        # If we're subscribed to a specific taxi, only forward matching data
        if self.taxi_plate:
            if taxi_data.get('plate_number') == self.taxi_plate:
                await self.send(text_data=json.dumps(taxi_data))
        else:
            # For general subscriptions, send all taxi updates
            await self.send(text_data=json.dumps(taxi_data))


# Helper function to broadcast taxi data updates (can be called from anywhere)
async def broadcast_taxi_data(taxi_data):
    channel_layer = get_channel_layer()
    plate_number = taxi_data.get('plate_number')
    
    # Send to general taxi group
    await channel_layer.group_send(
        'taxi_all',
        {
            'type': 'taxi_update',
            'data': taxi_data
        }
    )
    
    # Also send to taxi-specific group
    if plate_number:
        await channel_layer.group_send(
            f'taxi_{plate_number}',
            {
                'type': 'taxi_update',
                'data': taxi_data
            }
        )