import asyncio
import base64
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest, ReadHistoryRequest
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

# ENV
load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
client = TelegramClient("session_name", api_id, api_hash)
session = requests.Session()
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
    "@careerguidesy",
    "@jodfreelancer",
    "@wazfni2025",
    "@tawzeefy",
    "@recjobs",
    "@pgfow",
]

WEBHOOK_URL = os.getenv("URL")

STATE_FILE = "read_state.json"
FAILED_MESSAGES_FILE = "failed_messages.json"


def save_failed_message(msg, channel, payload, error):
    record = {
        "message_id": msg.id,
        "channel_id": channel.id,
        "channel_username": channel.username,
        "channel_title": channel.title,
        "payload_size": len(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
        "error": str(error),
        "timestamp": datetime.utcnow().isoformat(),
    }

    if os.path.exists(FAILED_MESSAGES_FILE):
        with open(FAILED_MESSAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(record)

    with open(FAILED_MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def send_with_retry(session, payload, msg, channel, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            r = session.post(WEBHOOK_URL, json=payload, timeout=15)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed for msg {msg.id}: {e}")

            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                print(f"❌ Permanent failure msg {msg.id}")
                save_failed_message(msg, channel, payload, e)
                return False


# ────────────────────────────────────────────
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

    # 🖼 معالجة الصور
    if isinstance(msg.media, MessageMediaPhoto):
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
async def resolve_channel(entity_ref):
    if isinstance(entity_ref, int):
        async for dialog in client.iter_dialogs():
            if dialog.entity.id == abs(entity_ref):
                return dialog.entity
        raise ValueError(f"Channel id {entity_ref} not found in dialogs")

    return await client.get_entity(entity_ref)


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def debug_payload(msg, payload, channel_username):
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_size = len(payload_json.encode("utf-8"))

    print("---- DEBUG (FAILED MESSAGE) ----")
    print("Channel:", channel_username)
    print("Message ID:", msg.id)
    print("Text length:", len(payload.get("text", "")))
    print("Has media:", bool(msg.media))
    print("Payload size (bytes):", payload_size)
    print("-------------------------------")


def print_failed_message(msg, payload, channel_username):
    print("\n========== FAILED MESSAGE ==========")
    print("Channel       :", channel_username)
    print("Message ID    :", msg.id)

    text = payload.get("text", "") or ""
    if len(text) > 500:
        text = text[:500] + " ...[TRUNCATED]"

    print("Text          :", text if text else "<NO TEXT>")
    print("Text length  :", len(payload.get("text", "") or ""))

    if msg.media:
        print("Has media     : YES")
        print("Media type    :", type(msg.media).__name__)
    else:
        print("Has media     : NO")

    payload_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    print("Payload size :", f"{payload_size} bytes")
    print("====================================\n")


async def check_unread_channel(channel_username, state):
    # حل الكيان
    channel = await client.get_entity(channel_username)

    # ── 1) قراءة آخر قراءة من تيليغرام (كمصدر مساعد) ──
    try:
        full = await client(GetFullChannelRequest(channel))
        telegram_last_read = full.full_chat.read_inbox_max_id or 0
    except Exception:
        telegram_last_read = 0

    # ── 2) قراءة آخر قراءة من الملف (المصدر الأساسي للاستمرار) ──
    local_last_read = state.get(str(channel.id), 0)

    # ── 3) اختيار الأحدث بينهما ──
    last_read_id = max(telegram_last_read, local_last_read)

    print(
        f"\n[{channel_username}] "
        f"telegram_last={telegram_last_read}, "
        f"local_last={local_last_read}, "
        f"effective_last={last_read_id}"
    )

    # ── 4) Pagination: قراءة كل الرسائل بعد last_read_id ──
    PAGE_SIZE = 100
    offset_id = 0
    all_unread = []

    while True:
        history = await client(
            GetHistoryRequest(
                peer=channel,
                limit=PAGE_SIZE,
                offset_id=offset_id,
                offset_date=None,
                max_id=0,
                min_id=last_read_id,  # لا نقرأ أقل من آخر قراءة فعّالة
                add_offset=0,
                hash=0,
            )
        )

        if not history.messages:
            break

        msgs = history.messages
        all_unread.extend(msgs)

        # أقدم رسالة في هذه الدفعة
        offset_id = msgs[-1].id

        # إذا الدفعة أصغر من PAGE_SIZE → خلصنا
        if len(msgs) < PAGE_SIZE:
            break

    # ترتيب تصاعدي (قديم → جديد)
    unread = sorted(all_unread, key=lambda m: m.id)

    if not unread:
        print("No unread messages.")
        return

    print(
        f"Found {len(unread)} new messages " f"(range {unread[0].id} → {unread[-1].id})"
    )

    # ── 5) إرسال + حفظ بعد كل رسالة ناجحة ──
    session = requests.Session()
    total = len(unread)

    for idx, msg in enumerate(unread, start=1):
        print(f"[{idx}/{total}] Sending message {msg.id}")

        payload = await serialize_message(msg, channel)
        success = await send_with_retry(session, payload, msg, channel)

        if success:
            state[str(channel.id)] = msg.id
            save_state(state)
            print(f"✅ Sent & saved message {msg.id}")
        else:
            print(f"⏭ Skipped saving state for failed msg {msg.id}")
        # try:
        #     response = session.post(WEBHOOK_URL, json=payload, timeout=15)
        #     response.raise_for_status()
        # except requests.exceptions.RequestException as e:
        #     print(f"❌ STOPPED at message {msg.id}")
        #     print("Reason:", e)
        #     debug_payload(msg, payload, channel_username)
        #     print_failed_message(msg, payload, channel_username)
        #     # return

        # # ✅ نجاح → نحفظ فورًا في الملف
        # state[str(channel.id)] = msg.id
        # save_state(state)

        print(f"→ Sent & saved message {msg.id}")


async def main():
    state = load_state()

    for ch in CHANNELS:
        await check_unread_channel(ch, state)


client.start()
client.loop.run_until_complete(main())
#
