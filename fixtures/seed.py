from datetime import datetime, timedelta
from sqlite3 import Connection

from habitline.repository import Habit, Periodicity


def make_test_habits(now: datetime) -> list[Habit]:
    """
    Generates 5 predefined habits with 4 weeks of example tracking data,
    relative to the given date and time as the current moment.

    :param now: Current date and time.
    :return: Nothing.
    """
    return [
        Habit(1, "Journal", Periodicity.DAILY, at_time(offset_date(now, -29), 12, 40, 31), [
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
        ]),

        Habit(2, "Do morning exercise", Periodicity.DAILY, at_time(offset_date(now, -28), 8, 32, 19), [
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
            at_time(offset_date(now, -11), 7, 9, 48),
            at_time(offset_date(now, -10), 9, 25, 10),
            at_time(offset_date(now, -9), 9, 46, 51),
            at_time(offset_date(now, -8), 8, 30, 49),
            at_time(offset_date(now, -6), 8, 38, 42),
            at_time(offset_date(now, -5), 9, 24, 2),
            at_time(offset_date(now, -4), 7, 28, 52),
            at_time(offset_date(now, -3), 7, 51, 41),
            at_time(offset_date(now, -2), 7, 37, 3),
            at_time(offset_date(now, -1), 8, 50, 6),
            at_time(now, 8, 40, 42),
        ]),

        Habit(3, "Call grandparents", Periodicity.WEEKLY, at_time(offset_date(now, -29), 14, 23, 58), [
            at_time(offset_date(now, -23), 17, 23, 25),
            at_time(offset_date(now, -16), 15, 21, 17),
            at_time(offset_date(now, -9), 15, 53, 30),
        ]),

        Habit(4, "Do laundry", Periodicity.WEEKLY, at_time(offset_date(now, -28), 17, 44, 5), [
            at_time(offset_date(now, -28), 18, 1, 3),
            at_time(offset_date(now, -21), 19, 32, 12),
            at_time(offset_date(now, -14), 18, 57, 11),
            at_time(offset_date(now, -7), 21, 22, 12),
            at_time(now, 20, 58, 21),
        ]),

        Habit(5, "Take a walk", Periodicity.DAILY, at_time(offset_date(now, -28), 11, 53, 27), [
            at_time(offset_date(now, -28), 11, 35, 5),
            at_time(offset_date(now, -26), 12, 32, 17),
            at_time(offset_date(now, -25), 15, 11, 54),
            at_time(offset_date(now, -23), 11, 12, 41),
            at_time(offset_date(now, -20), 15, 30, 5),
            at_time(offset_date(now, -18), 12, 31, 8),
            at_time(offset_date(now, -14), 15, 21, 26),
            at_time(offset_date(now, -12), 14, 58, 27),
            at_time(offset_date(now, -11), 12, 30, 29),
            at_time(offset_date(now, -10), 14, 38, 18),
            at_time(offset_date(now, -9), 11, 30, 40),
            at_time(offset_date(now, -7), 11, 4, 25),
            at_time(offset_date(now, -6), 14, 1, 52),
            at_time(offset_date(now, -5), 14, 32, 10),
            at_time(offset_date(now, -4), 15, 1, 59),
            at_time(offset_date(now, -3), 12, 39, 48),
            at_time(offset_date(now, -2), 14, 5, 5),
            at_time(offset_date(now, -1), 12, 53, 56),
            at_time(now, 13, 50, 36),
        ]),
    ]


def offset_date(ref: datetime, days: int) -> datetime:
    return ref + timedelta(days=days)


def at_time(ref: datetime, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    return datetime(ref.year, ref.month, ref.day, hour, minute, second)


def insert_raw(connection: Connection, habits: list[Habit]) -> None:
    """
    Inserts given habits into the given database directly, bypassing the normal insertion logic and guards.
    For testing purposes only.

    :param connection: Database connection.
    :param habits: Habits to insert.
    :return: Nothing.
    """
    cursor = connection.cursor()
    cursor.executemany("INSERT INTO habit(id, name, periodicity, created_at) VALUES (?, ?, ?, ?);",
                       [(habit.id, habit.name, habit.periodicity.value, int(habit.created_at.timestamp())) for habit in
                        habits])
    cursor.executemany("INSERT INTO completion(habit_id, completed_at) VALUES (?, ?);",
                       [(habit.id, int(completion.timestamp())) for habit in habits for completion in
                        habit.completions])
    connection.commit()


def clear_database(connection: Connection) -> None:
    """
    Completely clears all application data in the database.

    :param connection: Database connection.
    :return: Nothing.
    """
    cursor = connection.cursor()
    cursor.execute("DELETE FROM completion")
    cursor.execute("DELETE FROM habit")
    connection.commit()
