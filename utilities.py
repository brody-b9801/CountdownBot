import calendar
from datetime import datetime
import sqlite3
import discord
    
con = sqlite3.connect("event_database.db")

def get_days_in_month(month: int, year: int) -> int:
    return calendar.monthrange(year, month)[1]


def convert_to_unixepoch(month: int, day: int, year: int) -> int:
    return int(datetime(year, month, day, 0, 0).timestamp())


def get_days_until(date_ts: int) -> int:
    target = datetime.fromtimestamp(date_ts)
    delta = target - datetime.now()
    return delta.days

def is_in_dms(interaction: discord.Interaction) -> bool:
    return interaction.guild is None

def audit_events(interaction: discord.Interaction): 
    cur = con.cursor()
    cur.execute("SELECT from events WHERE ")

def delete_past_events(list: []):
    cur = con.cursor()
    for event in options:
        if get_days_until(event) < 0:
            cur.execute("DELETE FROM event WHERE name=?", event)