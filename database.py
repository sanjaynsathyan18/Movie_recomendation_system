import json
import os

DB_FILE = "users.json"

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f)

def login_user(username, password):
    users = load_users()
    return username in users and users[username] == password

def add_userdata(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = password
    save_users(users)
    return True