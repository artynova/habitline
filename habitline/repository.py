from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from sqlite3 import Connection


class Periodicity(Enum):
    """Habit periodicity."""
    DAILY = 0
    WEEKLY = 1


# Unique identifier of a habit - either its numeric ID or its name.
HabitIdentifier = int | str


@dataclass(frozen=True)
class Habit:
    """
    Stores basic persistent habit data.

    Attributes:
        id: Numeric identifier of the habit.
        name: Name of the habit.
        periodicity: Periodicity of the habit.
        created_at: Date and time the habit was created.
        completions: Tuple of dates and times of the habit's logged completions in chronological order.
    """
    id: int
    name: str
    periodicity: Periodicity
    created_at: datetime
    completions: tuple[datetime, ...]


def periodicity_to_stored(periodicity: Periodicity) -> int:
    """
    Converts periodicity to an integer that can be stored in the database.

    :param periodicity: Periodicity.
    :return: Integer representing the periodicity.
    """
    return periodicity.value


def datetime_to_stored(date_and_time: datetime) -> int:
    """
    Converts date and time to an integer that can be stored in the database (the POSIX timestamp).

    :param date_and_time: Date and time.
    :return: Integer representing the date and time.
    """
    return int(date_and_time.timestamp())


def get_identifier_column(identifier: HabitIdentifier) -> str:
    """
    Determines the database column storing the given identifier type.

    :param identifier: Habit identifier - either numeric ID or name.
    :return: "name" for string identifiers, "id" for integer identifiers.
    """
    # ID case
    if type(identifier) is int:
        return "id"
    # Name case
    return "name"


class HabitRepositoryException(Exception):
    """
    Logical exception raised by HabitRepository.
    """

    def __init__(self, message):
        super().__init__(message)


class HabitNotFoundException(HabitRepositoryException):
    """
    Exception raised when a habit could not be found.
    """

    def __init__(self, identifier: HabitIdentifier):
        if type(identifier) is int:
            super().__init__(f"Could not find habit with ID {identifier}.")
        else:
            super().__init__(f'Could not find habit with name "{identifier}".')


class HabitNameTakenException(HabitRepositoryException):
    """
    Exception raised changing a habit's name to the given name would result in a name collision.
    """

    def __init__(self, name: str):
        super().__init__(f'Habit name "{name}" is already taken.')


class HabitRepository:
    """
    Reads and writes habit data from and to the database.
    """

    def __init__(self, connection: Connection):
        """
        Creates a new habit repository.

        The database connection needs to be kept alive in order for the repository to function correctly.

        :param connection: Database connection to use.
        """
        self.__connection = connection

    def create(self, name: str, periodicity: Periodicity, created_at: datetime) -> None:
        """
        Creates a new habit.

        Raises an exception if the habit name is already taken.

        :param name: Unique name of the habit.
        :param periodicity: Periodicity of the habit.
        :param created_at: Date and time the habit was created.
        :return: Nothing.
        """
        if self.__exists(name):
            raise HabitNameTakenException(name)
        self.__connection.execute("INSERT INTO habit (name, periodicity, created_at) VALUES (?, ?, ?)",
                                  (name, periodicity_to_stored(periodicity), datetime_to_stored(created_at)))
        self.__connection.commit()

    def update(self, identifier: HabitIdentifier, name: str) -> None:
        """
        Updates a habit.

        Raises an exception if the habit cannot be found or if the habit name is already taken.

        :param identifier: Habit identifier - either numeric ID or name.
        :param name: New unique name of the habit.
        :return: Nothing.
        """
        habit_with_identifier_id = self.__get_habit_id(identifier)
        # Case where the habit with the passed identifier does not exist.
        if habit_with_identifier_id is None:
            raise HabitNotFoundException(identifier)
        habit_with_name_id = self.__get_habit_id(name)
        # Case where the habit with the passed target name already exists.
        if habit_with_name_id is not None:
            # If this habit's ID and the ID of the habit with the target name are the same, that means this habit
            # already has the target name. Therefore, we bail early.
            if habit_with_identifier_id == habit_with_name_id:
                return
            # Otherwise, it is a different habit by which the name is already taken.
            raise HabitNameTakenException(name)
        self.__connection.execute(f"UPDATE habit SET name = ? WHERE {get_identifier_column(identifier)} = ?",
                                  (name, identifier))
        self.__connection.commit()

    def delete(self, identifier: HabitIdentifier) -> None:
        """
        Deletes a habit.

        Raises an exception if the habit cannot be found.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Nothing.
        """
        if not self.__exists(identifier):
            raise HabitNotFoundException(identifier)
        self.__connection.execute(f"DELETE FROM habit WHERE {get_identifier_column(identifier)} = ?", (identifier,))
        self.__connection.commit()

    def complete(self, identifier: HabitIdentifier, completed_at: datetime) -> None:
        """
        Logs the completion of a habit.

        Raises an exception if the habit cannot be found.

        :param identifier: Habit identifier - either numeric ID or name.
        :param completed_at: Date and time the habit was completed.
        :return: Nothing.
        """
        habit_id = self.__get_habit_id(identifier)
        if habit_id is None:
            raise HabitNotFoundException(identifier)
        self.__connection.execute("INSERT INTO completion (habit_id, completed_at) VALUES (?, ?)",
                                  (habit_id, datetime_to_stored(completed_at)))

    def __get_habit_id(self, identifier: HabitIdentifier) -> int | None:
        """
        Retrieves the numeric ID of the habit with the given identifier.
        If the given identifier is a name, this serves to match it with the numeric identifier.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Numeric ID of the habit, or None if the habit cannot be found.
        """
        result = self.__connection.execute(f"SELECT id FROM habit WHERE {get_identifier_column(identifier)} = ?",
                                           (identifier,)).fetchone()
        if result is None:
            return None
        return result[0]

    def __exists(self, identifier: HabitIdentifier) -> bool:
        """
        Checks whether the habit with the given identifier exists.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Whether the habit exists.
        """
        result = self.__get_habit_id(identifier)
        return result is not None

    def read_one(self, identifier: HabitIdentifier) -> Habit:
        """
        Reads a specific habit from the database.

        Raises an exception if the habit cannot be found.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Matched habit.
        """
        # Query retrieves habit data joined with completions, providing flattened results with one row for each
        # completion of the habit, to minimise the number of separate queries made to the database for optimisation.
        results = self.__connection.execute(f"""
            SELECT habit.id, habit.name, habit.periodicity, habit.created_at, completion.completed_at
            FROM habit LEFT JOIN completion ON habit.id = completion.habit_id
            WHERE {get_identifier_column(identifier)} = ?
            ORDER BY completion.completed_at""", (identifier,)).fetchall()
        if not results:
            raise HabitNotFoundException(identifier)
        # The "if row[4]" condition is only True when the completion.completed_at value is not NULL, in which case
        # the row corresponds to a join with an actual completion. If it is NULL, then it is produced by the left join
        # for a habit without completions.
        habit_completions = [datetime.fromtimestamp(row[4]) for row in results if row[4]]
        return Habit(results[0][0], results[0][1], Periodicity(results[0][2]), datetime.fromtimestamp(results[0][3]),
                     tuple(habit_completions))

    def read_all(self) -> list[Habit]:
        """
        Reads all habits from the database.

        :return: List of all habits.
        """
        # Query retrieves habit data joined with completions, providing flattened results with one row for each
        # completion of a habit, to minimise the number of separate queries made to the database for optimisation.
        results = self.__connection.execute(f"""
            SELECT habit.id, habit.name, habit.periodicity, habit.created_at, completion.completed_at
            FROM habit LEFT JOIN completion ON habit.id = completion.habit_id
            ORDER BY habit.id, completion.completed_at""").fetchall()
        # Collect temporary habit records, including completion timestamp lists, from the flat query results
        habit_records: dict[int, tuple[str, Periodicity, datetime, list[datetime]]] = dict()
        for row in results:
            if habit_records.get(row[0]) is None:
                habit_records[row[0]] = (row[1], Periodicity(row[2]), datetime.fromtimestamp(row[3]), [])
            # The "if row[4]" condition is only True when the completion.completed_at value is not NULL, in which case
            # the row corresponds to a join with an actual completion. If it is NULL, then it is produced by the
            # left join for a habit without completions.
            if row[4]:
                # Element at index 3 in the habit record is the parsed list of completions.
                habit_records[row[0]][3].append(datetime.fromtimestamp(row[4]))
        # Convert records to proper habit objects and return the resulting list
        return [Habit(habit_id, record[0], record[1], record[2], tuple(record[3])) for habit_id, record in
                habit_records.items()]
