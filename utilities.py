import calendar
from datetime import datetime
import discord

def get_days_in_month(month: int, year: int) -> int:
    return calendar.monthrange(year, month)[1]


def convert_to_unixepoch(month: int, day: int, year: int) -> int:
    return int(datetime(year, month, day, 0, 0).timestamp())


def get_days_until(date_ts: int) -> int:
    target = datetime.fromtimestamp(date_ts)
    delta = target - datetime.now()
    return max(delta.days, 0)

def is_in_dms(interaction: discord.Interaction) -> bool:
    return interaction.guild is None
