import os
import sqlite3
import zoneinfo
from datetime import date, datetime, time, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
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
# Discord shows at most 25 autocomplete choices, so before anything is typed show
# common zones instead of the first 25 alphabetically (which are all Africa/*)
COMMON_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Phoenix",
    "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu", "America/Toronto",
    "America/Vancouver", "America/Mexico_City", "America/Sao_Paulo", "Europe/London",
    "Europe/Paris", "Europe/Berlin", "Europe/Madrid", "Europe/Moscow", "Africa/Johannesburg",
    "Asia/Dubai", "Asia/Kolkata", "Asia/Singapore", "Asia/Shanghai", "Asia/Tokyo",
    "Australia/Sydney", "Pacific/Auckland", "UTC",
]


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    scheduleNextPing()

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

    message = build_countdown_message(interaction.guild.id)
    if message is None:
        await interaction.response.send_message("No events have been created in this server")
        return
    await interaction.response.send_message(message)


def build_countdown_message(guild_id: int) -> str | None:
    delete_past_events(guild_id)

    rows = con.execute(
        "SELECT name, event_ts FROM events WHERE guild_id = ? ORDER BY event_ts",
        (guild_id,),
    ).fetchall()

    if not rows:
        return None

    ascii_table = t2a(
        header=["Event", "Days Remaining"],
        body=[[row["name"], get_days_until(row["event_ts"])] for row in rows],
        style=PresetStyle.thin_box,
    )
    return f"```\n{ascii_table}\n```"


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
        "INSERT INTO pings (guild_id, channel_id, ping_time, timezone) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (guild_id) DO UPDATE SET channel_id = excluded.channel_id, "
        "ping_time = excluded.ping_time, timezone = excluded.timezone",
        (interaction.guild.id, interaction.channel_id, ping_time, timezone),
    )
    con.commit()
    refresh_ping_times()
    await interaction.response.send_message(
        f"Daily ping set for {ping_time} ({timezone}) in this channel", ephemeral=True
    )


@setup_ping.autocomplete("timezone")
async def timezone_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    query = current.lower().replace(" ", "_")
    if not query:
        matches = COMMON_TIMEZONES
    else:
        matches = [tz for tz in TIMEZONES if query in tz.lower()]
        matches.sort(key=lambda tz: not tz.lower().rsplit("/", 1)[-1].startswith(query))
    return [app_commands.Choice(name=tz, value=tz) for tz in matches[:25]]

# --------Scheduled ping--------
PING_GRACE = timedelta(minutes=5)


def ping_datetime(row: sqlite3.Row, day: date) -> datetime:
    hour, minute = map(int, row["ping_time"].split(":"))
    return datetime.combine(day, time(hour, minute), tzinfo=zoneinfo.ZoneInfo(row["timezone"]))


def next_ping_times() -> list[time]:
    now = datetime.now(timezone.utc)
    times = []
    for row in con.execute("SELECT ping_time, timezone FROM pings"):
        local_today = now.astimezone(zoneinfo.ZoneInfo(row["timezone"])).date()
        next_ping = ping_datetime(row, local_today)
        if next_ping <= now:
            next_ping = ping_datetime(row, local_today + timedelta(days=1))
        times.append(next_ping.astimezone(timezone.utc).timetz())
    return times or [time(0, 0, tzinfo=timezone.utc)]


def refresh_ping_times() -> None:
    daily_ping.change_interval(time=next_ping_times())


@tasks.loop(time=time(0, 0, tzinfo=timezone.utc))
async def daily_ping() -> None:
    try:
        await send_due_pings()
    finally:
        refresh_ping_times()


async def send_due_pings() -> None:
    rows = con.execute(
        "SELECT guild_id, channel_id, ping_time, timezone, last_ping_date FROM pings"
    ).fetchall()

    for row in rows:
        local_now = datetime.now(zoneinfo.ZoneInfo(row["timezone"]))
        today = local_now.date().isoformat()
        since_ping = local_now - ping_datetime(row, local_now.date())
        if not timedelta(0) <= since_ping < PING_GRACE or row["last_ping_date"] == today:
            continue

        con.execute(
            "UPDATE pings SET last_ping_date = ? WHERE guild_id = ?",
            (today, row["guild_id"]),
        )
        con.commit()

        channel = bot.get_channel(row["channel_id"])
        message = build_countdown_message(row["guild_id"])
        if channel is None or message is None:
            continue
        try:
            await channel.send(message)
        except discord.HTTPException as e:
            print(f"Failed to send ping to guild {row['guild_id']}: {e}")


@daily_ping.before_loop
async def before_daily_ping() -> None:
    await bot.wait_until_ready()


def scheduleNextPing() -> None:
    if not daily_ping.is_running():
        kick = (datetime.now(timezone.utc) + timedelta(seconds=2)).timetz()
        daily_ping.change_interval(time=next_ping_times() + [kick])
        daily_ping.start()



load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])