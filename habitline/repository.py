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


class HabitNotFoundException(Exception):
    """
    Exception raised when a habit could not be found.
    """

    def __init__(self, identifier: HabitIdentifier):
        if type(identifier) is int:
            super().__init__(f"Could not find habit with ID {identifier}.")
        else:
            super().__init__(f'Could not find habit with name "{identifier}".')


class HabitNameTakenException(Exception):
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
        if self.exists(name):
            raise HabitNameTakenException(name)
        self.__connection.execute("INSERT INTO habit (name, periodicity, created_at) VALUES (?, ?, ?)",
                                  (name, periodicity.value, int(created_at.timestamp())))
        self.__connection.commit()

    def update(self, identifier: HabitIdentifier, name: str) -> None:
        """
        Updates a habit.

        Raises an exception if the habit cannot be found or if the habit name is already taken.

        :param identifier: Habit identifier - either numeric ID or name.
        :param name: New unique name of the habit.
        :return: Nothing.
        """
        if not self.exists(identifier):
            raise HabitNotFoundException(identifier)
        if self.exists(name):
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
        if not self.exists(identifier):
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
        habit_id = self.get_habit_id(identifier)
        self.__connection.execute("INSERT INTO completion (habit_id, completed_at) VALUES (?, ?)",
                                  (habit_id, int(completed_at.timestamp())))

    def get_habit_id(self, identifier: HabitIdentifier) -> int:
        """
        Retrieves the numeric ID of the habit with the given identifier.
        If the given identifier is a name, this serves to match it with the numeric identifier.

        Raises an exception if the habit cannot be found, thus providing assurance that the habit exists.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Numeric ID of the habit.
        """
        result = self.__connection.execute(f"SELECT id FROM habit WHERE {get_identifier_column(identifier)} = ?",
                                           (identifier,)).fetchone()
        if result is None:
            raise HabitNotFoundException(identifier)
        return result[0]

    def exists(self, identifier: HabitIdentifier) -> bool:
        """
        Checks whether the habit with the given identifier exists.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Whether the habit exists.
        """
        try:
            self.get_habit_id(identifier)
            return True
        except HabitNotFoundException:
            return False

    def read_all(self) -> list[Habit]:
        """
        Reads all habits from the database.

        :return: List of all habits.
        """
        # Query retrieves habit data joined with completions, providing flattened results with one row for each
        # completion of a habit, to minimise the number of separate queries made to the database for optimisation
        results = self.__connection.execute(f"""
            SELECT habit.id, habit.name, habit.periodicity, habit.created_at, completion.completed_at
            FROM habit LEFT JOIN completion ON habit.id = completion.habit_id
            ORDER BY habit.id, completion.completed_at""").fetchall()
        # Collect temporary habit records, including completion timestamp lists, from the flat query results
        habit_records: dict[int, tuple[str, Periodicity, datetime, list[datetime]]] = dict()
        for row in results:
            if habit_records.get(row[0]) is None:
                habit_records[row[0]] = (row[1], Periodicity(row[2]), datetime.fromtimestamp(row[3]), [])
            # Record the completion if it is not NULL in the results. If it is NULL, then the row in question is
            # the result of the LEFT JOIN and the completions for this habit are absent
            if row[4]:
                habit_records[row[0]][3].append(datetime.fromtimestamp(row[4]))
        # Convert records to proper habit objects and return the resulting list
        return [Habit(habit_id, record[0], record[1], record[2], tuple(record[3])) for habit_id, record in
                habit_records.items()]

    def read_one(self, identifier: HabitIdentifier) -> Habit:
        """
        Reads a specific habit from the database.

        Raises an exception if the habit cannot be found.

        :param identifier: Habit identifier - either numeric ID or name.
        :return: Matched habit.
        """
        # Flattened row structure similar to the one in read_all, but easier to handle since all completions
        # belong to the same habit
        results = self.__connection.execute(f"""
            SELECT habit.id, habit.name, habit.periodicity, habit.created_at, completion.completed_at
            FROM habit LEFT JOIN completion ON habit.id = completion.habit_id
            WHERE {get_identifier_column(identifier)} = ?
            ORDER BY completion.completed_at""", (identifier,)).fetchall()
        if not results:
            raise HabitNotFoundException(identifier)
        habit_completions = [datetime.fromtimestamp(row[4]) for row in results if row[4]]
        return Habit(results[0][0], results[0][1], Periodicity(results[0][2]), datetime.fromtimestamp(results[0][3]),
                     tuple(habit_completions))
