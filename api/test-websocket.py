import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:5000/ws"
    async with websockets.connect(uri) as websocket:
        # Corrected line: using json.dumps() to convert the dictionary to a JSON string
        await websocket.send(json.dumps({"data": "Hello from the client!"}))
        response = await websocket.recv()
        print(f"Response from server: {response}")

        # Close the connection when done
        await websocket.close()

asyncio.get_event_loop().run_until_complete(websocket_client())

