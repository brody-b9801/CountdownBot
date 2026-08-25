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

DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        cur.executescript("""
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
        con.commit()
        await self.tree.sync()


bot = Bot(command_prefix='/', description=description, intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


def get_days_in_month(month: int) -> int:
    return DAYS_IN_MONTH[month - 1]


def convert_to_unixepoch(month: int, day: int, year: int) -> int:
    return int(datetime.datetime(year, month, day, 0, 0).timestamp())


def get_days_until(date_ts: int) -> int:
    target = datetime.datetime.fromtimestamp(date_ts)
    delta = target - datetime.datetime.now()
    return max(delta.days, 0)


@bot.tree.command(name="schedule", description="schedule a countdown")
async def schedule(interaction: discord.Interaction, name: str, month: int, day: int, year: int) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.")
        return
    currtime = datetime.datetime.now()

    if year < currtime.year:
        await interaction.response.send_message("Invalid year")
        return
    if month < 1 or month > 12 or (year == currtime.year and month < currtime.month):
        await interaction.response.send_message("Invalid month")
        return
    if day < 1 or day > get_days_in_month(month) or (
        year == currtime.year and month == currtime.month and day < currtime.day
    ):
        await interaction.response.send_message("Invalid day")
        return

    sender = interaction.user.id
    guild_id = interaction.guild.id
    date_ts = convert_to_unixepoch(month, day, year)
    created_ts = int(datetime.datetime.now().timestamp())
    date_info = (guild_id, sender, name, date_ts, created_ts)

    try:
        cur.execute(
            "INSERT INTO events (guild_id, user_id, name, event_ts, created_ts) VALUES (?, ?, ?, ?, ?)",
            date_info,
        )
        con.commit()
    except sqlite3.IntegrityError:
        await interaction.response.send_message("There's already an event with that name in this server")
        return

    date_str = f"{month}/{day}/{year}"
    await interaction.response.send_message(f"Event '{name}' created for {date_str}")


@bot.tree.command(name="countdown", description="get a countdown to your event")
async def countdown(interaction: discord.Interaction, name: str) -> None:
    guild_id = interaction.guild.id
    cur.execute("SELECT * FROM events WHERE name = ? AND guild_id = ?", (name, guild_id))
    result = cur.fetchone()

    if result is None:
        await interaction.response.send_message(f"No event with name '{name}' has been created in this server")
        return

    event_ts = result[4]  # event_ts column
    await interaction.response.send_message(f"{get_days_until(event_ts)} days until {name}!")


@bot.tree.command(name="delete", description="delete an event")
async def delete(interaction: discord.Interaction, name: str) -> None:
    sender = interaction.user.id
    guild_id = interaction.guild.id
    cur.execute(
        "DELETE FROM events WHERE guild_id = ? AND user_id = ? AND name = ?",
        (guild_id, sender, name),
    )
    con.commit()
    await interaction.response.send_message("deleted")


load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])
