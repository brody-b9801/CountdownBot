import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import datetime

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()
intents.message_content = True

con = sqlite3.connect("event_database.db")
cur = con.cursor()

days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]

class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                name       TEXT NOT NULL,
                event_ts   INTEGER NOT NULL,
                created_ts INTEGER NOT NULL DEFAULT (unixepoch()),
                UNIQUE (guild_id, name)
            );
            CREATE INDEX IF NOT EXISTS idx_guild_ts ON events (guild_id, event_ts);
        """)
        await self.tree.sync()

bot = Bot(command_prefix='/', description=description, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="schedule", description="schedule a countdown")
async def schedule(ctx, name: str, month: int, day: int, year: int) -> None:
    #input validation
    currtime = datetime.datetime.now()
    if year < datetime.datetime.now().year:
        await ctx.send("Invalid year")
        return
    if month < 0 or month > 12 or (year == currtime.year and month < currtime.month):
        await ctx.send("Invalid month")
        return
    if day < 0 or day > get_days_in_month(month) or (month == currtime.month and day < currtime.day):
        await ctx.send("Invalid day")
        return
        
    sender = ctx.author.id
    guild_id = ctx.guild.id
    date = convert_to_unixepoch(month, day, year)
    date_info = (guild_id, sender, name, date, datetime.datetime.now())
    try:
        cur.execute("INSERT INTO events (guild_id, user_id, name, event_ts, created_ts) VALUES (?, ?, ?, ?, ?)", date_info)
    except sqlite3.IntegrityError:
        await ctx.send("There's already an event with that name in this server")
        return
    con.commit()
    date = f"{month}/{day}/{year}"    
    await ctx.send(f"Event '{name}' created for {date}")

@bot.tree.command(name="countdown", description="get a countdown to your event")
async def countdown(ctx, name: str) -> None:
    guild_id = ctx.guild.id
    cur.execute("SELECT * FROM events WHERE name = ? AND guild_id = ?")
    result = cur.fetchone()
    if result == None:
        await ctx.send(f"No event with name '{name}' has been created in this server")
        return
    
    await ctx.send(f"{get_days_until(result.event_ts)} days until {name}!")

@bot.tree.command(name="delete", description="delete an event")
async def delete(ctx, name: str) -> None:
    sender = ctx.author
    guild_id = ctx.guild.id
    cur.execute("DELETE FROM events WHERE guild_id = ? AND user_id = ? AND name = ?", (guild_id, sender, name))
    await ctx.send("deleted")

def get_days_until(date_ts: int) -> int:
    target = datetime.datetime.fromtimestamp(date_ts)
    delta = target - datetime.datetime.now()
    return max(delta.days, 0)

def convert_to_unixepoch(month, day, year) -> int:
    return int(datetime.datetime(year, month, day, 0, 0).timestamp())

def get_days_in_month(month: int) -> int:
    return get_days_in_month[month - 1]
    
load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])
