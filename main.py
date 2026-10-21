import os
import sqlite3
import zoneinfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from table2ascii import table2ascii as t2a, PresetStyle

from ui import ScheduleModal, DeleteView
from utilities import con, init_db, is_in_dms, get_days_until, delete_past_events

description = """A discord bot to count down the days until an event"""

intents = discord.Intents.default()


class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        init_db(con)
        await self.tree.sync()

bot = Bot(command_prefix='/', description=description, intents=intents)

TIMEZONES = sorted(zoneinfo.available_timezones())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    scheduleNextPing();

# --------Scheduling command--------
@bot.tree.command(name="schedule", description="schedule a countdown")
async def schedule(interaction: discord.Interaction) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message(
            "This command only works in a server.", ephemeral=True
        )
        return
    await interaction.response.send_modal(ScheduleModal())


# --------Countdown command--------
@bot.tree.command(name="countdown", description="view countdowns for events in this server")
async def countdown(interaction: discord.Interaction) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message(
            "This command only works in a server.", ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    delete_past_events(guild_id)

    rows = con.execute(
        "SELECT name, event_ts FROM events WHERE guild_id = ? ORDER BY event_ts",
        (guild_id,),
    ).fetchall()

    if not rows:
        await interaction.response.send_message("No events have been created in this server")
        return

    ascii_table = t2a(
        header=["Event", "Days Remaining"],
        body=[[row["name"], get_days_until(row["event_ts"])] for row in rows],
        style=PresetStyle.thin_box,
    )
    await interaction.response.send_message(f"```\n{ascii_table}\n```")


# --------Delete command--------
@bot.tree.command(name="delete", description="delete an event")
async def delete(interaction: discord.Interaction) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message(
            "This command only works in a server.", ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    delete_past_events(guild_id)

    rows = con.execute(
        "SELECT name FROM events WHERE guild_id = ? AND user_id = ? ORDER BY event_ts",
        (guild_id, interaction.user.id),
    ).fetchall()

    if not rows:
        await interaction.response.send_message(
            "You have no events in this server.", ephemeral=True
        )
        return

    options = [discord.SelectOption(label=row["name"]) for row in rows]
    view = DeleteView(options, interaction.user.id, guild_id)
    await interaction.response.send_message("Select an event:", view=view, ephemeral=True)

# --------Setup ping command--------
@bot.tree.command(name="setup-ping", description="set the daily countdown ping time (server owner only)")
@app_commands.describe(
    hour="Hour of the day (0-23)",
    minute="Minute of the hour (0-59)",
    timezone="Server time zone, e.g. America/Chicago",
)
async def setup_ping(
    interaction: discord.Interaction,
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Range[int, 0, 59],
    timezone: str,
) -> None:
    if is_in_dms(interaction):
        await interaction.response.send_message(
            "This command only works in a server.", ephemeral=True
        )
        return

    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message(
            "Only the server owner can use this command.", ephemeral=True
        )
        return

    if timezone not in TIMEZONES:
        await interaction.response.send_message(
            "Invalid time zone, pick one from the list (e.g. America/Chicago).", ephemeral=True
        )
        return

    ping_time = f"{hour:02d}:{minute:02d}"
    con.execute(
        "INSERT INTO pings (guild_id, ping_time, timezone) VALUES (?, ?, ?) "
        "ON CONFLICT (guild_id) DO UPDATE SET ping_time = excluded.ping_time, timezone = excluded.timezone",
        (interaction.guild.id, ping_time, timezone),
    )
    con.commit()
    await interaction.response.send_message(
        f"Daily ping time set to {ping_time} ({timezone})", ephemeral=True
    )


@setup_ping.autocomplete("timezone")
async def timezone_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    matches = [tz for tz in TIMEZONES if current.lower() in tz.lower()]
    return [app_commands.Choice(name=tz, value=tz) for tz in matches[:25]]

# --------Scheduled ping--------


load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])