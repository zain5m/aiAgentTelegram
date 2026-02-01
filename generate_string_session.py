import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== STRING SESSION ===\n")
    print(client.session.save())
