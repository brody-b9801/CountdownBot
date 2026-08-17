import discord
import os
from dotenv import load_dotenv

load_dotenv()

class Client(discord.Client):
    async def on_ready(self):
        print(f"logged in as {self.user}")

intents = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)
client.run(os.getenv("DISCORD_TOKEN"))