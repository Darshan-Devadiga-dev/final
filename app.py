import asyncio
import websockets
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store connected clients
clients = {}

async def register_client(websocket, path):
    """Register a new client"""
    client_id = f"user_{len(clients) + 1}_{datetime.now().strftime('%H%M%S')}"
    clients[client_id] = {
        'websocket': websocket,
        'name': f"Device {len(clients) + 1}"
    }
    
    logger.info(f"Client {client_id} connected")
    
    # Send client their ID and current peer list
    await websocket.send(json.dumps({
        'type': 'registered',
        'client_id': client_id,
        'name': clients[client_id]['name']
    }))
    
    # Broadcast updated peer list to all clients
    await broadcast_peer_list()
    
    try:
        async for message in websocket:
            data = json.loads(message)
            await handle_message(client_id, data)
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_id} disconnected")
    finally:
        # Remove client and update peer list
        if client_id in clients:
            del clients[client_id]
        await broadcast_peer_list()

async def handle_message(sender_id, data):
    """Handle incoming messages from clients"""
    message_type = data.get('type')
    
    if message_type == 'offer':
        # Forward WebRTC offer to target peer
        target_id = data.get('target')
        if target_id in clients:
            await clients[target_id]['websocket'].send(json.dumps({
                'type': 'offer',
                'offer': data.get('offer'),
                'sender': sender_id
            }))
    
    elif message_type == 'answer':
        # Forward WebRTC answer to target peer
        target_id = data.get('target')
        if target_id in clients:
            await clients[target_id]['websocket'].send(json.dumps({
                'type': 'answer',
                'answer': data.get('answer'),
                'sender': sender_id
            }))
    
    elif message_type == 'ice-candidate':
        # Forward ICE candidate to target peer
        target_id = data.get('target')
        if target_id in clients:
            await clients[target_id]['websocket'].send(json.dumps({
                'type': 'ice-candidate',
                'candidate': data.get('candidate'),
                'sender': sender_id
            }))

async def broadcast_peer_list():
    """Broadcast current peer list to all connected clients"""
    peer_list = []
    for client_id, client_data in clients.items():
        peer_list.append({
            'id': client_id,
            'name': client_data['name']
        })
    
    message = json.dumps({
        'type': 'peer-list',
        'peers': peer_list
    })
    
    # Send to all connected clients
    if clients:
        await asyncio.gather(
            *[client['websocket'].send(message) for client in clients.values()],
            return_exceptions=True
        )

async def main():
    """Start the WebSocket server"""
    logger.info("Starting WebSocket server on localhost:8765")
    async with websockets.serve(register_client, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())