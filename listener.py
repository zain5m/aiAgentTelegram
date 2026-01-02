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

WEBHOOK_URL = os.getenv("URL")


CHANNELS = [
    "EastMed Mobile Release",
    "@wazifnico",
    "@RemoteOnlineWork",
    "@saudijobscom",
    "@profinder_sy",
    "@jobs963",
    "@teleworksjobs",
    "@ExtraJobs",
    "@MGLNaJ",
    "@damasjob",
    "@tawasolsyria",
]

session_str = os.getenv("TG_SESSION")
client = TelegramClient(StringSession(session_str), api_id, api_hash)

resolved_channels = {}


async def serialize_message(msg, channel):
    data = {
        "message_id": msg.id,
        "date": msg.date.isoformat(),
        "text": msg.message or "",
        "caption": getattr(msg, "caption", ""),
        "views": msg.views,
        "channel_id": channel.id,
        "channel_username": channel.username,
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


async def resolve_channels(client, channels):
    resolved = {}

    async for dialog in client.iter_dialogs():
        if not dialog.is_channel:
            continue

        name = dialog.name
        username = f"@{dialog.entity.username}" if dialog.entity.username else None

        for ch in channels:
            if ch == name or ch == username:
                resolved[dialog.id] = dialog.entity

    return resolved


# @client.on(events.NewMessage(chats=CHANNELS))
@client.on(events.NewMessage)
async def handler(event):
    channel = resolved_channels.get(event.chat_id)
    if not channel:
        return

    msg = event.message
    payload = await serialize_message(msg, channel)

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"Sent {msg.id} from @{channel.username}")
    except Exception as e:
        print("Failed to send:", e)


async def main():
    global resolved_channels

    print("🔎 Resolving channels...")
    resolved_channels = await resolve_channels(client, CHANNELS)

    if not resolved_channels:
        print("❌ No channels resolved. Are you a member?")
        return

    print("✅ Listening to channels:")
    for cid, ch in resolved_channels.items():
        print(f"  {ch.title} ({ch.username}) → {cid}")

    await client.run_until_disconnected()


client.start()
client.loop.run_until_complete(main())
