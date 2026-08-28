import calendar
import sqlite3
import time
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import utilities as utils

#---------Utility tests---------

SCHEMA = """
CREATE TABLE events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name     TEXT    NOT NULL,
    event_ts INTEGER NOT NULL
);
"""

#--------get_days_in_month---------

class TestGetDaysInMonth:
    @pytest.mark.parametrize(
        "month, year, expected",
        [
            (1, 2024, 31),
            (2, 2024, 29),   
            (2, 2023, 28),   
            (2, 2000, 29),  
            (2, 1900, 28),   
            (4, 2021, 30),
            (6, 2021, 30),
            (9, 2021, 30),
            (11, 2021, 30),
            (12, 2025, 31),
        ],
    )
    def test_known_month_lengths(self, month, year, expected):
        assert utils.get_days_in_month(month, year) == expected

    def test_full_year_sums_correctly(self):
        assert sum(utils.get_days_in_month(m, 2023) for m in range(1, 13)) == 365
        assert sum(utils.get_days_in_month(m, 2024) for m in range(1, 13)) == 366

    def test_result_is_int(self):
        assert isinstance(utils.get_days_in_month(3, 2024), int)

    @pytest.mark.parametrize("month", [0, 13, -1, 100])
    def test_invalid_month_raises(self, month):
        with pytest.raises(calendar.IllegalMonthError):
            utils.get_days_in_month(month, 2024)


#--------convert_to_unixepoch---------


class TestConvertToUnixepoch:
    def test_roundtrips_to_local_midnight(self):
        ts = utils.convert_to_unixepoch(7, 4, 2024)
        assert datetime.fromtimestamp(ts) == datetime(2024, 7, 4, 0, 0)

    def test_returns_int(self):
        assert isinstance(utils.convert_to_unixepoch(1, 1, 2024), int)

    def test_later_dates_are_larger(self):
        earlier = utils.convert_to_unixepoch(3, 1, 2024)
        later = utils.convert_to_unixepoch(3, 2, 2024)
        assert later > earlier

    def test_consecutive_january_days_differ_by_one_day(self):
        a = utils.convert_to_unixepoch(1, 10, 2024)
        b = utils.convert_to_unixepoch(1, 11, 2024)
        assert b - a == 86_400

    @pytest.mark.parametrize(
        "month, day, year",
        [
            (2, 30, 2023),  
            (2, 29, 2023),   
            (4, 31, 2024), 
            (13, 1, 2024),  
            (1, 0, 2024),    
        ],
    )
    def test_invalid_dates_raise(self, month, day, year):
        with pytest.raises(ValueError):
            utils.convert_to_unixepoch(month, day, year)

    @pytest.mark.skipif(
        not hasattr(time, "tzset"), reason="TZ manipulation needs POSIX tzset"
    )
    def test_result_depends_on_local_timezone(self, monkeypatch):
        def ts_under(tz):
            monkeypatch.setenv("TZ", tz)
            time.tzset()
            return utils.convert_to_unixepoch(1, 15, 2024)

        try:
            utc = ts_under("UTC")
            chicago = ts_under("America/Chicago")
            assert utc == 1_705_276_800          
            assert chicago - utc == 6 * 3600     
        finally:
            monkeypatch.undo()
            time.tzset()


#--------get_days_until--------

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0)


@pytest.fixture
def frozen_now(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FIXED_NOW

    monkeypatch.setattr(utils, "datetime", FrozenDateTime)
    return FIXED_NOW


def _ts(dt: datetime) -> int:
    return int(dt.timestamp())


class TestGetDaysUntil:
    @pytest.mark.parametrize(
        "offset, expected",
        [
            (timedelta(days=5), 5),
            (timedelta(days=1), 1),
            (timedelta(days=30), 30),
            (timedelta(0), 0),
        ],
    )
    def test_whole_days_in_future(self, frozen_now, offset, expected):
        assert utils.get_days_until(_ts(frozen_now + offset)) == expected

    @pytest.mark.parametrize(
        "offset, expected",
        [
            (timedelta(hours=1), 0),
            (timedelta(hours=23, minutes=59), 0),
            (timedelta(days=1, hours=23), 1),
            (timedelta(days=2, hours=12), 2),
        ],
    )
    def test_partial_days_truncate_down(self, frozen_now, offset, expected):
        assert utils.get_days_until(_ts(frozen_now + offset)) == expected

    @pytest.mark.parametrize(
        "offset, expected",
        [
            (timedelta(days=-1), -1),
            (timedelta(days=-5), -5),
            (timedelta(hours=-1), -1),      
            (timedelta(days=-1, hours=-1), -2),
            (timedelta(minutes=-1), -1),
        ],
    )
    def test_past_dates_floor_toward_negative(self, frozen_now, offset, expected):
        assert utils.get_days_until(_ts(frozen_now + offset)) == expected

    def test_returns_int(self, frozen_now):
        assert isinstance(utils.get_days_until(_ts(frozen_now)), int)

    def test_works_without_freezing(self):
        far_future = int((datetime.now() + timedelta(days=10, hours=1)).timestamp())
        assert utils.get_days_until(far_future) == 10


#--------is_in_dms--------

class TestIsInDms:
    def test_true_when_guild_is_none(self):
        assert utils.is_in_dms(SimpleNamespace(guild=None)) is True

    def test_false_when_guild_present(self):
        guild = SimpleNamespace(id=123456789, name="Illini VEX")
        assert utils.is_in_dms(SimpleNamespace(guild=guild)) is False

    def test_falsy_but_not_none_guild_is_not_a_dm(self):
        class EmptyGuild:
            def __bool__(self):
                return False

        assert utils.is_in_dms(SimpleNamespace(guild=EmptyGuild())) is False


#--------delete_past_events--------

@pytest.fixture
def db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(utils, "con", conn)
    yield conn
    conn.close()


def add_event(conn, guild_id, name, ts):
    conn.execute(
        "INSERT INTO events (guild_id, name, event_ts) VALUES (?, ?, ?)",
        (guild_id, name, ts),
    )
    conn.commit()


def event_names(conn, guild_id=None):
    if guild_id is None:
        rows = conn.execute("SELECT name FROM events ORDER BY name").fetchall()
    else:
        rows = conn.execute(
            "SELECT name FROM events WHERE guild_id = ? ORDER BY name", (guild_id,)
        ).fetchall()
    return [r["name"] for r in rows]


NOW = int(time.time())
HOUR = 3600
DAY = 86400

class TestDeletePastEvents:
    def test_removes_past_events(self, db):
        add_event(db, 1, "yesterday", NOW - DAY)
        add_event(db, 1, "last_week", NOW - 7 * DAY)

        utils.delete_past_events(1)

        assert event_names(db) == []

    def test_keeps_future_events(self, db):
        add_event(db, 1, "tomorrow", NOW + DAY)
        add_event(db, 1, "next_month", NOW + 30 * DAY)

        utils.delete_past_events(1)

        assert event_names(db) == ["next_month", "tomorrow"]

    def test_mixed_past_and_future(self, db):
        add_event(db, 1, "past", NOW - DAY)
        add_event(db, 1, "future", NOW + DAY)

        utils.delete_past_events(1)

        assert event_names(db) == ["future"]

    def test_leaves_other_guilds_alone(self, db):
        add_event(db, 1, "guild1_past", NOW - DAY)
        add_event(db, 2, "guild2_past", NOW - DAY)
        add_event(db, 2, "guild2_future", NOW + DAY)

        utils.delete_past_events(1)

        assert event_names(db, 1) == []
        assert event_names(db, 2) == ["guild2_future", "guild2_past"]

    def test_no_error_on_empty_table(self, db):
        utils.delete_past_events(999)
        assert event_names(db) == []

    def test_no_error_for_unknown_guild(self, db):
        add_event(db, 1, "keeper", NOW - DAY)
        utils.delete_past_events(424242)
        assert event_names(db) == ["keeper"]

    def test_boundary_just_past_vs_just_future(self, db):
        add_event(db, 1, "just_past", NOW - 60)
        add_event(db, 1, "just_future", NOW + 60)

        utils.delete_past_events(1)

        assert event_names(db) == ["just_future"]

    def test_returns_none(self, db):
        assert utils.delete_past_events(1) is None

    def test_deletion_is_committed(self, tmp_path, monkeypatch):
        path = tmp_path / "events.db"
        writer = sqlite3.connect(path)
        writer.row_factory = sqlite3.Row
        writer.executescript(SCHEMA)
        add_event(writer, 1, "past", NOW - DAY)
        add_event(writer, 1, "future", NOW + DAY)
        monkeypatch.setattr(utils, "con", writer)

        utils.delete_past_events(1)

        reader = sqlite3.connect(path)
        reader.row_factory = sqlite3.Row
        try:
            assert event_names(reader) == ["future"]
        finally:
            reader.close()
            writer.close()