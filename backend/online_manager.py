class OnlineManager:

    def __init__(self):
        self.online_users = set()

    def connect(self, user_id: int):
        self.online_users.add(user_id)

    def disconnect(self, user_id: int):
        self.online_users.discard(user_id)

    def get_online_users(self):
        return list(self.online_users)


online_manager = OnlineManager()