from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.role = user_data.get('role', 'consumer') 
        self.avatar_url = user_data.get('avatar_url', '')
        self.bio = user_data.get('bio', '')
        
    def get_id(self):
        return self.id