import discord
import datetime
import sqlite3
import math
from utilities import con, get_days_in_month, convert_to_unixepoch

# --------Scheduling Modal--------
class ScheduleModal(discord.ui.Modal, title="Schedule an Event"):
    event_name = discord.ui.TextInput(
        label="Event Name", 
        placeholder="Event Name", 
        min_length=1, 
        max_length=50
    )

    event_month = discord.ui.TextInput(
        label="Event Month", 
        placeholder="Event Month", 
        min_length=1, 
        max_length=2
    )

    event_day = discord.ui.TextInput(
        label="Event Day", 
        placeholder="Event Day", 
        min_length=1, 
        max_length=2
    )
    event_year = discord.ui.TextInput(
        label="Event Year", 
        placeholder="Event Year", 
        min_length=4, 
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            month = int(self.event_month.value)
            day = int(self.event_day.value)
            year = int(self.event_year.value)
        except ValueError:
            await interaction.response.send_message("Invalid date, all fields must be numeric", ephemeral=True)
            return
        
        currtime = datetime.datetime.now()

        if year < currtime.year or year > currtime.year + 100:
            await interaction.response.send_message("Invalid year")
            return
        if month < 1 or month > 12 or (year == currtime.year and month < currtime.month):
            await interaction.response.send_message("Invalid month")
            return
        if day < 1 or day > get_days_in_month(month, year) or (year == currtime.year and month == currtime.month and day < currtime.day):
            await interaction.response.send_message("Invalid day")
            return

        sender = interaction.user.id
        guild_id = interaction.guild.id
        date_ts = convert_to_unixepoch(month, day, year)
        created_ts = int(currtime.timestamp())
        date_info = (guild_id, sender, self.event_name.value, date_ts, created_ts)
        cur = con.cursor()

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
        await interaction.response.send_message(f"Event '{self.event_name.value}' created for {date_str}")


    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if interaction.response.is_done():
            await interaction.followup.send("An error occurred.", ephemeral=True)
        else:
            await interaction.response.send_message("An error occurred.", ephemeral=True)

# --------Delete Dropdown With Pagination--------

class DeleteDropdown(discord.ui.Select):
    def __init__(self, options, user_id, guild_id):
        super().__init__(placeholder="Pick an event to delete", options=options, row=0)
        self.user_id = user_id
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        cur = con.cursor()
        cur.execute(
            "DELETE FROM events WHERE guild_id = ? AND user_id = ? AND name = ?",
            (self.guild_id, self.user_id, name),
        )
        con.commit()
        if cur.rowcount == 0:
            await interaction.response.edit_message(content="That event no longer exists.", view=None)
        else:
            await interaction.response.edit_message(content=f"Deleted {name}", view=None)


class DeleteView(discord.ui.View):

    def __init__(self, full_options, user_id, guild_id):
        super().__init__(timeout=60)
        self.full_options = full_options
        self.user_id = user_id
        self.guild_id = guild_id
        self.page = 0
        self.max_page = max(0, math.ceil(len(full_options) / 25) - 1)
        self.dropdown = None

        if self.max_page == 0:
            self.remove_item(self.back)
            self.remove_item(self.forward)

        self.rebuild()

    def rebuild_delete(self):
        if self.dropdown is not None:
            self.remove_item(self.dropdown)
        start = self.page * 25
        page_options = self.full_options[start:start + 25]
        self.dropdown = DeleteDropdown(page_options, self.user_id, self.guild_id)
        self.add_item(self.dropdown)

        if self.max_page > 0:
            self.back.disabled = self.page == 0
            self.forward.disabled = self.page >= self.max_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.rebuild_delete()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=1)
    async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.rebuild_delete()
        await interaction.response.edit_message(view=self)