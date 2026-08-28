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
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()

def get_days_in_month(month: int, year: int) -> int:
    return calendar.monthrange(year, month)[1]


def convert_to_unixepoch(month: int, day: int, year: int) -> int:
    return int(datetime(year, month, day, 0, 0).timestamp())


def get_days_until(date_ts: int) -> int:
    return (datetime.fromtimestamp(date_ts) - datetime.now()).days


def is_in_dms(interaction: discord.Interaction) -> bool:
    return interaction.guild is None


def delete_past_events(guild_id: int) -> None:
    con.execute(
        "DELETE FROM events WHERE guild_id = ? AND event_ts < unixepoch()",
        (guild_id,),
    )
    con.commit()