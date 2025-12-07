import os

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest

api_id = os.environ["API_ID"]
api_hash = os.environ["API_HASH"]

client = TelegramClient("session_name", api_id, api_hash)

# القناة المطلوب مراقبتها
CHANNEL_USERNAME = "wazifnico"


async def check_unread():
    # 1. احصل على القناة
    channel = await client.get_entity(CHANNEL_USERNAME)

    # 2. معلومات القناة (منها read_inbox_max_id)
    full = await client(GetFullChannelRequest(channel))
    max_read = full.full_chat.read_inbox_max_id or 0

    print("Last read message ID:", max_read)

    # 3. جلب آخر 1000 رسالة
    history = await client(
        GetHistoryRequest(
            peer=channel,
            limit=1000,
            offset_date=None,  # <-- هذا المطلوب لتصحيح الخطأ
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0,
        )
    )

    messages = history.messages

    # 4. فلترة الرسائل غير المقروءة
    unread = [m for m in messages if m.id > max_read]

    print(f"Unread messages count: {len(unread)}")

    for msg in unread:
        if msg.message:
            print("UNREAD:", msg.message)

    # 5. تعليم كـ مقروء
    if unread:
        await client.send_read_acknowledge(channel, max_id=unread[-1].id)


async def main():
    await check_unread()


client.start()
client.loop.run_until_complete(main())
