import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', description=description, intents=intents)

con = sqlite3.connect("event_database.db")
cur = con.cursor()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def schedule(ctx, name: str, month: int, day: int, year: int):
    date = f"{month}/{day}/{year}"    
    guild_id = ctx.guild.id
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS events (
            guild TEXT PRIMARY KEY NOT NULL UNIQUE,
            eventname TEXT NOT NULL,
            month INTEGER,
            day INTEGER,
            year INTEGER
        )
    """)

    date_info = (guild_id, name, month, day, year)

    cur.execute(f"INSERT INTO events (guild, eventname, month, day, year) VALUES (?, ?, ?, ?, ?)", date_info)
    await ctx.send(f"Event '{name}' created for {date}")

@bot.command()
async def countdown(ctx, name: str):
    #retreive event from guild the command was sent from, compute days until the date using helper method
    await ctx.send(f"Countdown for event '{name}' is not implemented yet")

async def delete(ctx, name: str):
    await ctx.send("deleted")

load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))