import discord
import datetime
import sqlite3
from main import con, get_days_in_month, convert_to_unixepoch

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

        if year < currtime.year:
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
    def __init__(self, options):
        super().__init__(placeholder="Select an event to delete", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_event = self.values[0]
        sender = interaction.user.id
        guild_id = interaction.guild.id
        cur = con.cursor()
        cur.execute(
            "DELETE FROM events WHERE guild_id = ? AND user_id = ? AND name = ?",
            (guild_id, sender, selected_event),
        )
        if cur.rowcount == 0:
            await interaction.response.send_message("No event with that name found for you in this server", ephemeral=True)
            return
        con.commit()
        await interaction.response.send_message(f"Deleted {selected_event}", ephemeral=True)

class DeleteView(discord.ui.View):
    def __init__(self, options):
        super().__init__()
        self.add_item(DeleteDropdown(options))

class BackButtonView(discord.ui.View):
    def __init__(self, dropdown: DeleteDropdown):
        super().__init__(timeout=180)
        self.add_item(dropdown)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary, custom_id="back")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        dropdown
        return

class ForwardButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary, custom_id="forward")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        return