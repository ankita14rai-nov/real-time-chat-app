from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        websocket = self.active_connections.get(user_id)

        if websocket:
            await websocket.send_json(message)

    def is_online(self, user_id: int):
        return user_id in self.active_connections


manager = ConnectionManager()

async def send_delete_message(self, message_id: int, user_id: int):

    websocket = self.active_connections.get(user_id)

    if websocket:
        await websocket.send_json(
            {
                "type": "delete",
                "message_id": message_id
            }
        )