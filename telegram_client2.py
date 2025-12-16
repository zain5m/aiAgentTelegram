import base64
import json
import os

import requests
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

# client = TelegramClient("session_multi", api_id, api_hash)
client = TelegramClient("session_name", api_id, api_hash)
#
# القنوات التي نريد مراقبتها
CHANNELS = ["EastMed Mobile Release"]

WEBHOOK_URL = (
    # "https://primary-production-f837.up.railway.app/webhook-test/telegram-jobs"
    "https://primary-production-f837.up.railway.app/webhook/telegram-jobs"
    # "https://yasmin-unclimbed-mathilde.ngrok-free.dev/webhook-test/telegram-jobs"
)


# ملف تخزين آخر ID مقروء (خاص بنا، غير تيليغرام)
STATE_FILE = "read_state.json"


# ────────────────────────────────────────────
async def serialize_message(msg):
    data = {
        "message_id": msg.id,
        "date": msg.date.isoformat(),
        "text": msg.message or "",
        "caption": getattr(msg, "caption", ""),
        "views": msg.views,
        "media": [],
    }

    # 🖼 معالجة الصور
    if isinstance(msg.media, MessageMediaPhoto):
        photo = msg.media.photo

        # تحميل الصورة (JPEG) وتحويلها base64
        file_bytes = await client.download_media(msg, file=bytes)
        encoded = base64.b64encode(file_bytes).decode()

        data["media"].append(
            {
                "type": "photo",
                "mime": "image/jpeg",
                "base64": encoded,
            }
        )

    # 📄 معالجة الملفات (PDF, APK...)
    elif isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document

        file_bytes = await client.download_media(msg, file=bytes)
        encoded = base64.b64encode(file_bytes).decode()

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
                "base64": encoded,
            }
        )

    return data


# ────────────────────────────────────────────


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# ────────────────────────────────────────────
async def check_unread_channel(channel_username, state):
    channel = await client.get_entity(channel_username)

    full = await client(GetFullChannelRequest(channel))
    tg_read_id = full.full_chat.read_inbox_max_id or 0
    local_read_id = state.get(channel_username, 0)

    last_read_id = max(tg_read_id, local_read_id)

    print(f"\n[{channel_username}] Last read id = {last_read_id}")

    history = await client(
        GetHistoryRequest(
            peer=channel,
            limit=100,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0,
        )
    )

    messages = history.messages
    unread = [m for m in messages if m.id > last_read_id]

    if not unread:
        print(f"No unread messages.\n")
        return

    print(f"Found {len(unread)} new messages!")

    for msg in unread:
        payload = await serialize_message(msg)

        print("\nSending message to n8n:")
        # print(json.dumps(payload, indent=2))
        # print("\________________________")
        save_state(payload)
        # إرسال الرسالة للن8ن
        response = requests.post(WEBHOOK_URL, json=payload)
        print(response.status_code, response.reason, response.text)

    # تحديث آخر رسالة
    state[channel_username] = unread[-1].id


async def main():
    state = load_state()

    for ch in CHANNELS:
        await check_unread_channel(ch, state)

    # save_state(state)


client.start()
client.loop.run_until_complete(main())
