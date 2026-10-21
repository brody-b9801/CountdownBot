import calendar
import sqlite3
from datetime import datetime

import discord

con = sqlite3.connect("event_database.db")
con.row_factory = sqlite3.Row
SCHEMA = """
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
CREATE TABLE IF NOT EXISTS pings (
    guild_id   INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    ping_time  TEXT NOT NULL,
    timezone   TEXT NOT NULL,
    last_ping_date TEXT
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    # CREATE TABLE IF NOT EXISTS won't add columns to an existing table, so rebuild
    # a pings table from before channel_id existed. Its rows have no channel to ping
    # anyway, so server owners just rerun /setup-ping.
    ping_columns = {row[1] for row in conn.execute("PRAGMA table_info(pings)")}
    if ping_columns and "channel_id" not in ping_columns:
        conn.execute("DROP TABLE pings")
    conn.executescript(SCHEMA)
    conn.commit()

def get_days_in_month(month: int, year: int) -> int:
    return calendar.monthrange(year, month)[1]


def convert_to_unixepoch(month: int, day: int, year: int) -> int:
    return int(datetime(year, month, day, 0, 0).timestamp())


def get_days_until(date_ts: int) -> int:
    # Compare calendar dates, not exact times: events are stored at midnight, so an
    # event tomorrow is under 24 hours away but should still count as 1 day
    return (datetime.fromtimestamp(date_ts).date() - datetime.now().date()).days


def is_in_dms(interaction: discord.Interaction) -> bool:
    return interaction.guild is None


def delete_past_events(guild_id: int) -> None:
    # Keep today's events so they show "0 days" on the day, and delete them the day after
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    con.execute(
        "DELETE FROM events WHERE guild_id = ? AND event_ts < ?",
        (guild_id, int(today_start.timestamp())),
    )
    con.commit()