import os
from telethon import TelegramClient, events
import asyncio

api_id = 38823753
api_hash = "edfaf36ed525766cf06cdbe8a132e6f5"
bot_token = os.getenv("BOT_TOKEN")

client = TelegramClient("bot_session", api_id, api_hash)

@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("✅ Bot ON hai bhai!")

async def main():
    await client.start(bot_token=bot_token)
    print("✅ Bot Running...")
    await client.run_until_disconnected()

asyncio.run(main())
