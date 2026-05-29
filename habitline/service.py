from datetime import datetime
from sqlite3 import Connection

from analytics import HabitAnalysis, AggregateAnalysis
from habitline.analytics import analyse_many, analyse_one, aggregate, HabitFilter, HabitComparator, AnalysisPeriod
from management import HabitRepository, Periodicity, HabitIdentifier


class HabitService:
    """
    Manages habit persistence and analytics.
    """

    def __init__(self, connection: Connection):
        """
        Creates a new habit service.
        The database connection needs to be kept alive in order for the service to function correctly.

        :param connection: Database connection to use.
        """
        self.__repository = HabitRepository(connection)

    def create(self, name: str, periodicity: Periodicity) -> None:
        """
        Creates a new habit.
        Raises an error if the habit name is already taken.

        :param name: Unique name of the habit.
        :param periodicity: Periodicity of the habit.
        :return: Nothing.
        """
        self.__repository.create(name, periodicity)

    def edit(self, identifier: HabitIdentifier, name: str) -> None:
        """
        Edits a habit.
        Raises an error if the habit cannot be found or if the habit name is already taken.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :param name: New unique name of the habit.
        :return: Nothing.
        """
        self.__repository.update(identifier, name)

    def delete(self, identifier: HabitIdentifier) -> None:
        """
        Deletes a habit.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :return: Nothing.
        """
        self.__repository.delete(identifier)

    def complete(self, identifier: HabitIdentifier, completed_at: datetime) -> None:
        """
        Logs the completion of a habit.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :param completed_at: Date and time the habit was completed.
        :return: Nothing.
        """
        self.__repository.complete(identifier, completed_at)

    def get_many(self, filters: list[HabitFilter], comparator: HabitComparator, sort_asc: bool, period: AnalysisPeriod) -> \
            list[HabitAnalysis]:
        """
        Retrieves habits from the database and returns analysis results for them with filtering, sorting, and period limitation for completions.

        :return: List of habit analyses.
        """
        habits = self.__repository.read_all()
        now = datetime.now()
        return analyse_many(habits, filters, comparator, sort_asc, period, now)

    def get_one(self, identifier: HabitIdentifier, period: AnalysisPeriod) -> HabitAnalysis:
        """
        Retrieves a habit from the database and returns analysis results for it with period limitation for completions.
        Raises an error if the habit cannot be found.

        :return: Habit analysis.
        """
        habit = self.__repository.read_one(identifier)
        now = datetime.now()
        return analyse_one(habit, period, now)

    def analyse(self, filters: list[HabitFilter], period: AnalysisPeriod) -> AggregateAnalysis:
        """
        Determines aggregate metrics for a collection of habits with filtering and period limitation for completions.

        :param filters: List of filter functions for analysed habits.
        :param period: Analysis period.
        :return: Results of aggregate analysis.
        """
        habits = self.__repository.read_all()
        now = datetime.now()
        return aggregate(habits, filters, period, now)
