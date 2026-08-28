import os
import sqlite3

import discord
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


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


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


load_dotenv()
bot.run(os.environ["DISCORD_TOKEN"])