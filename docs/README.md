# CountdownBot

A Discord bot that counts down the days until events in your server. Anyone can schedule an event with a slash command, and everyone in the server sees the countdown.

**[Add CountdownBot to your server](https://discord.com/oauth2/authorize?client_id=1538941872926494790&permissions=8&integration_type=0&scope=bot)**

## Commands

| Command | What it does |
| --- | --- |
| `/schedule` | Opens a form for the event name, month, day, and year, then creates the countdown |
| `/countdown` | Posts a table of every upcoming event in the server and the days remaining for each |
| `/delete` | Opens a private menu of the events *you* created so you can pick one to remove |

All commands work only inside a server, not in DMs.

```
┌──────────────────┬────────────────┐
│ Event            │ Days Remaining │
├──────────────────┼────────────────┤
│ Spring Break     │ 12             │
│ Robotics Worlds  │ 47             │
└──────────────────┴────────────────┘
```

### Rules

- **Event names are unique per server.** Two servers can each have a "Finals" event, but one server can't have two.
- **Dates must be real and not in the past.** The year can be up to 100 years ahead. Leap years are handled.
- **Only the creator can delete an event.** The delete menu shows only your own events, and only you can use it.
- **Expired events clean themselves up.** An event is removed once its day begins; this happens whenever someone runs `/countdown` or `/delete`.
- **The delete menu pages at 25 events** (Discord's dropdown limit) and expires after 60 seconds.

## How it works

The bot is built with [discord.py](https://discordpy.readthedocs.io/) using application (slash) commands, a modal form for scheduling, and a paginated dropdown view for deletion. Events are stored in SQLite:

```sql
CREATE TABLE events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    event_ts   INTEGER NOT NULL,          -- event date, Unix time
    created_ts INTEGER NOT NULL DEFAULT (unixepoch()),
    UNIQUE (guild_id, name)
);
CREATE INDEX idx_guild_ts ON events (guild_id, event_ts);
```

- Every query is scoped by `guild_id`, so servers never see each other's events.
- The `UNIQUE (guild_id, name)` constraint enforces unique names at the database level, not just in the UI.
- The `(guild_id, event_ts)` index covers the bot's main query: one server's events in date order.
- All queries are parameterized.
- The schema is created on startup if it doesn't exist, so a fresh install needs no setup step.

| File | Contents |
| --- | --- |
| `main.py` | Bot setup and the three slash commands |
| `ui.py` | The scheduling modal and the paginated delete menu |
| `utilities.py` | Database connection, schema, and date helpers |
| `tests.py` | pytest suite |

## Running your own instance

### Requirements

- Python 3 (developed on 3.14)
- SQLite 3.38 or newer, for `unixepoch()` (bundled with recent Python releases)
- A bot application and token from the [Discord Developer Portal](https://discord.com/developers/applications)

### Setup

```bash
git clone https://github.com/brody-b9801/CountdownBot.git
cd CountdownBot
pip install discord.py python-dotenv table2ascii
```

Copy `example.env` to `.env` and set your bot token:

```
DISCORD_TOKEN=your_token_here
```

Then start the bot:

```bash
python main.py
```

Slash commands are registered with Discord when the bot starts. The database is written to `event_database.db` in the working directory.

> **Timezones:** event dates are stored as midnight in the timezone of the machine running the bot, so run it on a host set to your community's timezone.

## Tests

```bash
pip install pytest
pytest tests.py
```

The suite covers the date and database helpers:

- **Month lengths**, including leap years and century rules (2000 vs. 1900)
- **Date conversion**: round-tripping to local midnight, rejecting invalid dates, and timezone behavior
- **Days-until math**: truncating partial days and flooring past dates
- **DM detection**
- **Pruning**: removing past events, keeping future ones, and leaving other servers' events untouched
- **Constraints**: per-server name uniqueness, and that deletions are actually committed

The database tests run against an in-memory SQLite instance, and time-dependent tests freeze the clock.
