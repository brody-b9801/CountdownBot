import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()
intents.message_content = True
load_dotenv()

bot = commands.Bot(command_prefix='/', description=description, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def schedule(ctx, name: str, month: int, day: int, year: int):
    date = f"{month}/{day}/{year}"
    await ctx.send(f"Event '{name}' created for {date}")

@bot.command()
async def countdown(ctx, name: str):
    await ctx.send(f"Countdown for event '{name}' is not implemented yet")

bot.run(os.getenv("DISCORD_TOKEN"))