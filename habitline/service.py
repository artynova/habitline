from datetime import datetime
from sqlite3 import Connection

from habitline.analytics import HabitAnalysis, AggregateAnalysis, analyse_many, analyse_one, aggregate, \
    HabitAnalysisFilter, HabitAnalysisOrder, AnalysisRange
from habitline.repository import HabitRepository, Periodicity, HabitIdentifier


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
        self.__repository.create(name, periodicity, datetime.now())

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

    def complete(self, identifier: HabitIdentifier) -> None:
        """
        Logs the completion of a habit.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :return: Nothing.
        """
        self.__repository.complete(identifier, datetime.now())

    def get_one(self, identifier: HabitIdentifier, analysis_range: AnalysisRange) -> HabitAnalysis:
        """
        Retrieves a habit from the database and returns analysis results for it with range limitation for completions.
        Raises an error if the habit cannot be found.

        :param identifier: Identifier of the habit - either numeric ID or name.
        :param analysis_range: Analysis range.
        :return: Habit analysis.
        """
        habit = self.__repository.read_one(identifier)
        now = datetime.now()
        return analyse_one(habit, analysis_range, now)

    def get_many(self, filters: list[HabitAnalysisFilter], order: HabitAnalysisOrder,
                 analysis_range: AnalysisRange) -> list[HabitAnalysis]:
        """
        Retrieves habits from the database and returns analysis results for them with filtering, sorting, and range limitation for completions.

        :param filters: List of filters for analysed habits.
        :param order: Analysed habit order.
        :param analysis_range: Analysis range.
        :param analysis_range: Analysis range.
        :return: List of habit analyses.
        """
        habits = self.__repository.read_all()
        now = datetime.now()
        return analyse_many(habits, filters, order, analysis_range, now)

    def analyse(self, filters: list[HabitAnalysisFilter], analysis_range: AnalysisRange) -> AggregateAnalysis:
        """
        Determines aggregate metrics for a collection of habits with filtering and range limitation for completions.

        :param filters: List of filters for analysed habits.
        :param analysis_range: Analysis range.
        :return: Aggregate analysis.
        """
        habits = self.__repository.read_all()
        now = datetime.now()
        return aggregate(habits, filters, analysis_range, now)
