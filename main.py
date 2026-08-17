import discord
import os
from dotenv import load_dotenv

load_dotenv

class Client(discord.client):
    async def on_ready(self):
        print("Test")

intents = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)
client.run(os.getenv("DISCORD_TOKEN"))