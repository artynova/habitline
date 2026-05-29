from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from sqlite3 import Connection


class Periodicity(Enum):
    """Habit periodicity."""
    DAILY = 0,
    WEEKLY = 1,
    UNKNOWN = auto()


# Unique identifier of a habit - either its numeric ID or its name.
HabitIdentifier = int | str


@dataclass(frozen=True)
class CommandResult:
    """
    Habit command result.

    Attributes:
        success: Whether the command was successful.
        message: Optional human-readable message explaining the result.
    """
    success: bool
    message: str | None


@dataclass(frozen=True)
class Habit:
    """
    Stores basic persistent habit data.

    Attributes:
        id: Numeric identifier of the habit.
        name: Name of the habit.
        periodicity: Periodicity of the habit.
        created_at: Date and time the habit was created.
        completions: List of dates and times of the habit's logged completions.
    """
    id: int
    name: str
    periodicity: Periodicity
    created_at: datetime
    completions: list[datetime]


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
        self.__cursor = self.__connection.cursor()

    def create(self, name: str, periodicity: Periodicity) -> None:
        """
        Creates a new habit.
        Raises an error if the habit name is already taken.

        :param name: Unique name of the habit.
        :param periodicity: Periodicity of the habit.
        :return: Nothing.
        """
        pass

    def update(self, identifier: HabitIdentifier, name: str) -> None:
        """
        Updates a habit.
        Raises an error if the habit cannot be found or if the habit name is already taken.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :param name: New unique name of the habit.
        :return: Nothing.
        """
        pass

    def delete(self, identifier: HabitIdentifier) -> None:
        """
        Deletes a habit.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :return: Nothing.
        """
        pass

    def complete(self, identifier: HabitIdentifier, completed_at: datetime) -> None:
        """
        Logs the completion of a habit.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :param completed_at: Date and time the habit was completed.
        :return: Nothing.
        """
        pass

    def read(self) -> list[Habit]:
        """
        Reads all habits from the database.

        :return: List of all habits.
        """
        pass

    def read_one(self, identifier: HabitIdentifier) -> Habit | None:
        """
        Reads a specific habit from the database.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :return: Matched habit.
        """
        pass
