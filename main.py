import discord
from ui import ScheduleModal
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import datetime
import calendar
from table2ascii import table2ascii as t2a, PresetStyle

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()
intents.message_content = True

con = sqlite3.connect("event_database.db")
con.row_factory = sqlite3.Row


class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        cur = con.cursor()
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



# --------Scheduling command--------
@bot.tree.command(name="schedule", description="schedule a countdown")
async def schedule(interaction: discord.Interaction) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message("This command only works in a server.")
        return
    await interaction.response.send_modal(ScheduleModal())


# --------Countdown command--------
@bot.tree.command(name="countdown", description="view countdowns for events in this server")
async def countdown(interaction: discord.Interaction) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message("This command only works in a server.")
        return
    guild_id = interaction.guild.id
    cur = con.cursor()
    cur.execute("SELECT * FROM events WHERE guild_id = ?", (guild_id,))
    result = cur.fetchall()

    if not result:
        await interaction.response.send_message("No events have been created in this server")
        return
    headers = ["Event", "Days Remaining"]
    data = [[row["name"], get_days_until(row["event_ts"])] for row in result]
    ascii_table = t2a(
        header=headers,
        body=data,
        style=PresetStyle.thin_compact_rounded
    )
    await interaction.response.send_message(f"```\n{ascii_table}\n```")


# --------Delete command--------
@bot.tree.command(name="delete", description="delete an event")
async def delete(interaction: discord.Interaction, name: str) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message("This command only works in a server.")
        return
    sender = interaction.user.id
    guild_id = interaction.guild.id
    cur = con.cursor()
    cur.execute(
        "DELETE FROM events WHERE guild_id = ? AND user_id = ? AND name = ?",
        (guild_id, sender, name),
    )
    if cur.rowcount == 0:
        await interaction.response.send_message("No event with that name found for you in this server")
        return
    con.commit()
    await interaction.response.send_message(f"Deleted {name}")


load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])