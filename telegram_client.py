import os

from telethon import TelegramClient, events

api_id = os.environ["API_ID"]
api_hash = os.environ["API_HASH"]

# اسم ملف الجلسة – هو اللي بيمثّل تسجيل دخول حسابك
client = TelegramClient("session_name", api_id, api_hash)

# THIS FOR CRATE SESSION
# async def main():
#     me = await client.get_me()
#     print("Logged in as:", me.username)


# client.start()
# client.loop.run_until_complete(main())
# -- TODO:

# @client.on(events.NewMessage)
# async def handler(event):
#     if event.is_channel:  # فقط القنوات
#         print("New message from channel:")
#         print("Channel:", event.chat.title)
#         print("Message:", event.message.message)


# client.start()
# client.run_until_disconnected()
