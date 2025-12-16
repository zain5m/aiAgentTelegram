import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session = os.getenv("TG_SESSION")


CHANNEL_NAME = "EastMed Mobile Release"  # الاسم اللي بدك تدخله

client = TelegramClient(StringSession(session), api_id, api_hash)


async def main():
    found = False
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and dialog.name == CHANNEL_NAME:
            print("✅ Found channel!")
            print("Name:", dialog.name)
            print("ID:", dialog.id)
            found = True
            break

    if not found:
        print("❌ Channel not found. Are you a member?")


with client:
    client.loop.run_until_complete(main())
