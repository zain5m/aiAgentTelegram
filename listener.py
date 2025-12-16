import base64
import os

import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

WEBHOOK_URL = "https://primary-production-f837.up.railway.app/webhook/telegram-jobs"

CHANNELS = [
    # "EastMed Mobile Release",
    # "@EastMedMobileRelease"
    -1003394865233  # EastMed Mobile Release this for test
]
session_str = os.getenv("TG_SESSION")
client = TelegramClient(StringSession(session_str), api_id, api_hash)
# client = TelegramClient("session_name", api_id, api_hash)


async def serialize_message(msg):
    data = {
        "message_id": msg.id,
        "date": msg.date.isoformat(),
        "text": msg.text or "",
        "views": msg.views,
        "channel_id": msg.peer_id.channel_id if msg.peer_id else None,
        "media": [],
    }

    if isinstance(msg.media, MessageMediaPhoto):
        file_bytes = await client.download_media(msg, file=bytes)
        data["media"].append(
            {
                "type": "photo",
                "mime": "image/jpeg",
                "base64": base64.b64encode(file_bytes).decode(),
            }
        )

    elif isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        file_bytes = await client.download_media(msg, file=bytes)

        file_name = None
        for attr in doc.attributes:
            if hasattr(attr, "file_name"):
                file_name = attr.file_name

        data["media"].append(
            {
                "type": "document",
                "mime": doc.mime_type,
                "size": doc.size,
                "file_name": file_name,
                "base64": base64.b64encode(file_bytes).decode(),
            }
        )

    return data


@client.on(events.NewMessage(chats=CHANNELS))
async def handler(event):
    msg = event.message
    payload = await serialize_message(msg)

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print("Sent to n8n:", r.status_code)
    except Exception as e:
        print("Failed to send:", e)


async def main():
    print("🚀 Listening to Telegram channels...")
    await client.run_until_disconnected()


client.start()
client.loop.run_until_complete(main())
