from datetime import datetime, timedelta
from sqlite3 import Connection

from habitline.analytics import HabitAnalysis, AggregateAnalysis
from habitline.repository import Habit, Periodicity


def make_test_habits(now: datetime) -> list[Habit]:
    """
    Generates 6 predefined habits with at least 4 weeks of example tracking data, relative to the given date and time
    as the current moment.

    :param now: Current date and time.
    :return: Test habits.
    """
    analyses = make_test_habit_analyses(now)
    return [analysis.habit for analysis in analyses]


def make_test_habit_analyses(now: datetime) -> list[HabitAnalysis]:
    """
    Generates 6 predefined habits with at least 4 weeks of example tracking data, relative to the given date and time
    as the current moment, and provides expected analysis data for each habit.

    :param now: Current date and time.
    :return: Test habit analyses with test habits and expected analysis results.
    """
    week_start = at_week_start(now)
    return [
        HabitAnalysis(Habit(1, "Journal", Periodicity.DAILY, at_time(offset_date(now, -29), 12, 40, 31), (
            at_time(offset_date(now, -29), 19, 35, 17),
            at_time(offset_date(now, -28), 18, 2, 29),
            at_time(offset_date(now, -27), 17, 59, 54),
            at_time(offset_date(now, -26), 20, 33, 3),
            at_time(offset_date(now, -25), 20, 46, 41),
            at_time(offset_date(now, -24), 18, 36, 41),
            at_time(offset_date(now, -23), 18, 37, 12),
            at_time(offset_date(now, -22), 20, 45, 8),
            at_time(offset_date(now, -21), 17, 35, 32),
            at_time(offset_date(now, -20), 17, 47, 40),
            at_time(offset_date(now, -19), 19, 52, 14),
            at_time(offset_date(now, -18), 18, 10, 49),
            at_time(offset_date(now, -17), 20, 23, 40),
            at_time(offset_date(now, -16), 17, 48, 33),
            at_time(offset_date(now, -15), 17, 54, 22),
            at_time(offset_date(now, -14), 17, 5, 56),
            at_time(offset_date(now, -13), 17, 23, 4),
            at_time(offset_date(now, -12), 17, 2, 41),
            at_time(offset_date(now, -11), 20, 56, 8),
            at_time(offset_date(now, -10), 19, 41, 18),
            at_time(offset_date(now, -9), 19, 33, 30),
            at_time(offset_date(now, -8), 20, 34, 24),
            at_time(offset_date(now, -7), 20, 8, 39),
            at_time(offset_date(now, -6), 18, 40, 58),
            at_time(offset_date(now, -5), 20, 53, 40),
            at_time(offset_date(now, -4), 19, 30, 9),
            at_time(offset_date(now, -3), 19, 24, 48),
            at_time(offset_date(now, -2), 19, 27, 17),
            at_time(offset_date(now, -1), 20, 1, 20),
            at_time(now, 17, 33, 25),
        )), 30, 30, 0.0, False),

        HabitAnalysis(Habit(2, "Do morning exercise", Periodicity.DAILY, at_time(offset_date(now, -28), 8, 32, 19), (
            at_time(offset_date(now, -28), 8, 45, 38),
            at_time(offset_date(now, -27), 9, 44, 49),
            at_time(offset_date(now, -26), 7, 12, 45),
            at_time(offset_date(now, -25), 8, 29, 31),
            at_time(offset_date(now, -24), 7, 37, 12),
            at_time(offset_date(now, -23), 9, 39, 25),
            at_time(offset_date(now, -22), 9, 21, 22),
            at_time(offset_date(now, -21), 9, 15, 22),
            at_time(offset_date(now, -20), 8, 49, 5),
            at_time(offset_date(now, -19), 7, 45, 25),
            at_time(offset_date(now, -18), 7, 13, 30),
            at_time(offset_date(now, -17), 9, 44, 25),
            at_time(offset_date(now, -16), 7, 16, 22),
            at_time(offset_date(now, -15), 9, 36, 8),
            at_time(offset_date(now, -14), 7, 54, 20),
            at_time(offset_date(now, -13), 9, 14, 54),
            at_time(offset_date(now, -12), 7, 5, 39),
            at_time(offset_date(now, -9), 9, 46, 51),
            at_time(offset_date(now, -8), 8, 30, 49),
            at_time(offset_date(now, -6), 8, 38, 42),
            at_time(offset_date(now, -5), 9, 24, 2),
        )), 0, 17, 0.25, True),

        HabitAnalysis(
            Habit(3, "Call grandparents", Periodicity.WEEKLY, at_time(offset_date(week_start, -29), 14, 23, 58), (
                at_time(offset_date(week_start, -24), 17, 23, 25),
                at_time(offset_date(week_start, -18), 15, 21, 17),
                at_time(offset_date(week_start, -15), 15, 53, 30),
                at_time(offset_date(week_start, -9), 13, 17, 25),
            )), 0, 3, 0.4, True),

        HabitAnalysis(Habit(4, "Do laundry", Periodicity.WEEKLY, at_time(offset_date(week_start, -28), 17, 44, 5), (
            at_time(offset_date(week_start, -28), 18, 1, 3),
            at_time(offset_date(week_start, -21), 19, 32, 12),
            at_time(offset_date(week_start, -14), 18, 57, 11),
            at_time(offset_date(week_start, -7), 21, 22, 12),
            at_time(now, 20, 58, 21),
        )), 5, 5, 0.0, False),

        HabitAnalysis(Habit(5, "Take a walk", Periodicity.DAILY, at_time(offset_date(now, -28), 11, 53, 27), (
            at_time(offset_date(now, -28), 11, 35, 5),
            at_time(offset_date(now, -26), 12, 32, 17),
            at_time(offset_date(now, -25), 15, 11, 54),
            at_time(offset_date(now, -23), 11, 12, 41),
            at_time(offset_date(now, -20), 15, 30, 5),
            at_time(offset_date(now, -18), 12, 31, 8),
            at_time(offset_date(now, -15), 14, 5, 5),
            at_time(offset_date(now, -14), 9, 35, 10),
            at_time(offset_date(now, -14), 15, 21, 26),
            at_time(offset_date(now, -12), 14, 58, 27),
            at_time(offset_date(now, -11), 12, 30, 29),
            at_time(offset_date(now, -10), 14, 38, 18),
            at_time(offset_date(now, -9), 11, 30, 40),
            at_time(offset_date(now, -7), 11, 4, 25),
            at_time(offset_date(now, -6), 14, 1, 52),
            at_time(offset_date(now, -5), 14, 32, 10),
            at_time(offset_date(now, -4), 10, 40, 12),
            at_time(offset_date(now, -4), 15, 1, 59),
            at_time(offset_date(now, -1), 12, 53, 56),
        )), 1, 4, 11.0 / 28.0, True),

        HabitAnalysis(
            Habit(6, "Review financials", Periodicity.WEEKLY, at_time(offset_date(week_start, -28), 13, 22, 39), ()),
            0, 0, 1.0, True),
    ]


def make_test_aggregate_analysis() -> AggregateAnalysis:
    """
    Generates the expected aggregate analysis based on the 6 predefined habits with at least 4 weeks of example
    tracking data.

    Since the predefined data are designed in such a way that the distribution of dates follows the target pattern
    regardless of the specific reference current date and time, analytics data (aggregate analytics in this case) does
    not need the reference date.

    :return: Expected aggregate analysis.
    """
    return AggregateAnalysis(6, 30, 30, 143.0 / 420.0)


def offset_date(date_and_time: datetime, days: int) -> datetime:
    """
    Offsets the given date and time by the given number of days.

    :param date_and_time: Date and time.
    :param days: Number of days.
    :return: Offset date and time.
    """
    return date_and_time + timedelta(days=days)


def at_time(date_and_time: datetime, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Takes the date from the given datetime object and creates a new object with the same date and given time.
    :param date_and_time: Date and time.
    :param hour: Hour.
    :param minute: Minute.
    :param second: Second.
    :return: Date and time with the same date as input and specified time.
    """
    return datetime(date_and_time.year, date_and_time.month, date_and_time.day, hour, minute, second)


def at_week_start(date_and_time: datetime) -> datetime:
    """
    Creates a new datetime object with the same time and with the date set to the start of the corresponding week.
    :param date_and_time: Date and time.
    :return: Date and time with the same time and date set at the start of the week.
    """
    return offset_date(date_and_time, -date_and_time.weekday())


def insert_raw(connection: Connection, habits: list[Habit]) -> None:
    """
    Inserts given habits into the given database directly, bypassing the normal insertion logic and guards.
    For testing purposes only.

    :param connection: Database connection.
    :param habits: Habits to insert.
    :return: Nothing.
    """
    connection.executemany("INSERT INTO habit(id, name, periodicity, created_at) VALUES (?, ?, ?, ?);",
                           [(habit.id, habit.name, habit.periodicity.value, int(habit.created_at.timestamp())) for habit
                            in
                            habits])
    connection.executemany("INSERT INTO completion(habit_id, completed_at) VALUES (?, ?);",
                           [(habit.id, int(completion.timestamp())) for habit in habits for completion in
                            habit.completions])
    connection.commit()


def clear_database(connection: Connection) -> None:
    """
    Completely clears all application data in the database.

    :param connection: Database connection.
    :return: Nothing.
    """
    connection.execute("DELETE FROM completion")
    connection.execute("DELETE FROM habit")
    connection.commit()
