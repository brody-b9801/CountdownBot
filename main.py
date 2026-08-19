import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()
intents.message_content = True

con = sqlite3.connect("event_database.db")
cur = con.cursor()

class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild TEXT PRIMARY KEY NOT NULL UNIQUE,
                sender TEXT NOT NULL,
                eventname TEXT NOT NULL,
                month INTEGER,
                day INTEGER,
                year INTEGER
            )
        """)
        await self.tree.sync()

bot = Bot(command_prefix='/', description=description, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="schedule", description="schedule a countdown")
async def schedule(ctx, name: str, month: int, day: int, year: int) -> None:
    sender = ctx.author
    guild_id = ctx.guild.id
    cur.execute("SELECT * FROM events WHERE eventname = ?", name)
    if cur.fetchone() != None:
        await client.send(ctx.channel, "You have already created an event with this name")
        return;
    
    date_info = (guild_id, sender, name, month, day, year)

    cur.execute("INSERT INTO events (guild, sender, eventname, month, day, year) VALUES (?, ?, ?, ?, ?, ?)", date_info)
    date = f"{month}/{day}/{year}"    
    await ctx.send(f"Event '{name}' created for {date}")

@bot.tree.command(name="countdown", description="get a countdown to your event")
async def countdown(ctx, name: str) -> None:
    await ctx.send(f"Countdown for event '{name}' is not implemented yet")

@bot.tree.command(name="delete", description="delete an event")
async def delete(ctx, name: str) -> None:
    sender = ctx.author
    guild_id = ctx.guild.id
    cur.execute("DELETE * FROM events WHERE guild = ? AND sender = ? AND eventname = ?", (guild_id, sender, name))
    await ctx.send("deleted")

load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])
