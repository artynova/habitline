from datetime import datetime, date
from sqlite3 import Connection
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from fixtures.seed import insert_raw, make_test_habits, make_test_habit_analyses, make_test_aggregate_analysis
from habitline.analytics import AnalysisRange, HabitAnalysis, HabitAnalysisFilter, HabitAnalysisOrder, AggregateAnalysis
from habitline.database import get_connection
from habitline.repository import Periodicity, HabitNameTakenException, HabitNotFoundException, HabitIdentifier, Habit
from habitline.service import HabitService
from tests.conftest import MOCK_NOW


@pytest.fixture()
def patched_create_repository(mocker: MockerFixture, mock_repository: Mock):
    """
    Patches the HabitRepository class to create the mock repository object.

    :param mocker: Mocker fixture.
    :param mock_repository: Mock habit repository.
    :return: Patched class.
    """
    return mocker.patch("habitline.service.HabitRepository", return_value=mock_repository)


@pytest.fixture()
def patched_now(mocker: MockerFixture):
    """
    Patches datetime.now to return the fixed mock current datetime.

    :param mocker: Mocker fixture.
    :return: Patched function.
    """
    mock_datetime = mocker.patch("habitline.service.datetime")
    mock_datetime.now.return_value = MOCK_NOW
    return mock_datetime.now


@pytest.fixture()
def patched_analyse_one(mocker: MockerFixture):
    """
    Patches the analyse_one analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched function.
    """
    return mocker.patch("habitline.service.analyse_one")


@pytest.fixture()
def patched_analyse_many(mocker: MockerFixture):
    """
    Patches the analyse_many analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched function.
    """
    return mocker.patch("habitline.service.analyse_many")


@pytest.fixture()
def patched_aggregate(mocker: MockerFixture):
    """
    Patches the aggregate analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched function.
    """
    return mocker.patch("habitline.service.aggregate")


class TestHabitService:
    """
    Tests HabitService with unit tests.
    """

    def test_create_failure_name_taken(self, mock_connection: Mock, mock_repository: Mock,
                                       patched_create_repository: Mock, patched_now: Mock):
        """
        Tests HabitService.create failure outcome when the provided name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY
        mock_repository.create.side_effect = HabitNameTakenException(name)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNameTakenException):
            service.create(name, periodicity)

        mock_repository.create.assert_called_once_with(name, periodicity, MOCK_NOW)

    def test_create_success(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                            patched_now: Mock):
        """
        Tests HabitService.create success outcome.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY
        service = HabitService(mock_connection)

        service.create(name, periodicity)

        mock_repository.create.assert_called_once_with(name, periodicity, MOCK_NOW)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                          patched_create_repository: Mock,
                                          identifier: HabitIdentifier):
        """
        Tests HabitService.edit failure outcome when trying to change the name of a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"
        mock_repository.update.side_effect = HabitNotFoundException(identifier)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNotFoundException):
            service.edit(identifier, name)

        mock_repository.update.assert_called_once_with(identifier, name)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_failure_name_taken(self, mock_connection: Mock, mock_repository: Mock,
                                     patched_create_repository: Mock, identifier: HabitIdentifier):
        """
        Tests HabitService.edit failure outcome when the provided new name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"
        mock_repository.update.side_effect = HabitNameTakenException(name)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNameTakenException):
            service.edit(identifier, name)

        mock_repository.update.assert_called_once_with(identifier, name)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_success(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                          identifier: HabitIdentifier):
        """
        Tests HabitService.edit success outcome.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"
        service = HabitService(mock_connection)

        service.edit(identifier, name)

        mock_repository.update.assert_called_once_with(identifier, name)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_delete_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                            patched_create_repository: Mock,
                                            identifier: HabitIdentifier):
        """
        Tests HabitService.delete failure outcome when trying to delete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_repository.delete.side_effect = HabitNotFoundException(identifier)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNotFoundException):
            service.delete(identifier)

        mock_repository.delete.assert_called_once_with(identifier)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_delete_success(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                            identifier: HabitIdentifier):
        """
        Tests HabitService.delete success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        service = HabitService(mock_connection)

        service.delete(identifier)

        mock_repository.delete.assert_called_once_with(identifier)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                              patched_create_repository: Mock, patched_now: Mock,
                                              identifier: HabitIdentifier):
        """
        Tests HabitService.complete failure outcome when trying to complete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_repository.complete.side_effect = HabitNotFoundException(identifier)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNotFoundException):
            service.complete(identifier)

        mock_repository.complete.assert_called_once_with(identifier, MOCK_NOW)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_success(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                              patched_now: Mock,
                              identifier: HabitIdentifier):
        """
        Tests HabitService.complete success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        service = HabitService(mock_connection)

        service.complete(identifier)

        mock_repository.complete.assert_called_once_with(identifier, MOCK_NOW)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_get_one_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                             patched_create_repository: Mock,
                                             identifier: HabitIdentifier):
        """
        Tests HabitService.get_one success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_repository.read_one.side_effect = HabitNotFoundException(identifier)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNotFoundException):
            service.get_one(identifier, AnalysisRange(None, None))

        mock_repository.read_one.assert_called_once_with(identifier)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_get_one_success(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                             patched_analyse_one: Mock,
                             patched_now: datetime, identifier: HabitIdentifier):
        """
        Tests HabitService.get_one success.
        
        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param patched_analyse_one: Patched mock analyse_one function.
        :param patched_now: Patched datetime.now function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        habit = Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
            datetime(2026, 5, 11, 12, 15, 40),
            datetime(2026, 5, 12, 14, 56, 23),
            datetime(2026, 5, 13, 13, 42, 21),
        ))
        analysis_range = AnalysisRange(date(2026, 5, 12), None)
        analysis = HabitAnalysis(habit, 2, 2, 0.0, True)
        mock_repository.read_one.return_value = habit
        patched_analyse_one.return_value = analysis
        service = HabitService(mock_connection)

        result = service.get_one(identifier, analysis_range)

        mock_repository.read_one.assert_called_once_with(identifier)
        patched_analyse_one.assert_called_once_with(habit, analysis_range, MOCK_NOW)
        assert result == analysis

    def test_get_many(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                      patched_analyse_many: Mock, patched_now: Mock):
        """
        Tests HabitService.get_many.
        
        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param patched_analyse_many: Patched mock analyse_many function.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        habits = [
            Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
                datetime(2026, 5, 11, 12, 15, 40),
                datetime(2026, 5, 13, 13, 42, 21),
                datetime(2026, 5, 14, 16, 20, 49),
            )),
            Habit(2, "Call grandparents", Periodicity.WEEKLY, datetime(2026, 4, 17, 13, 30, 16), (
                datetime(2026, 4, 22, 12, 15, 40),
                datetime(2026, 5, 6, 13, 42, 21),
            )),
            Habit(3, "Go to gym", Periodicity.WEEKLY, datetime(2026, 4, 17, 14, 49, 21), ()),
        ]
        analysis_range = AnalysisRange(None, date(2026, 5, 12))
        analyses = [
            HabitAnalysis(habits[1], 2, 2, 1.0 / 3.0, True),
            HabitAnalysis(habits[2], 0, 0, 1.0, True),
        ]
        filters = [HabitAnalysisFilter.by_search_match("o")]
        order = HabitAnalysisOrder.by_streak(True)
        mock_repository.read_all.return_value = habits
        patched_analyse_many.return_value = analyses
        service = HabitService(mock_connection)

        result = service.get_many(filters, order, analysis_range)

        mock_repository.read_all.assert_called_once()
        patched_analyse_many.assert_called_once_with(habits, filters, order, analysis_range, MOCK_NOW)
        assert result == analyses

    def test_analyse(self, mock_connection: Mock, mock_repository: Mock, patched_create_repository: Mock,
                     patched_aggregate: Mock, patched_now: Mock):
        """
        Tests HabitService.analyse.

        :param mock_connection: Mock database connection.
        :param mock_repository: Mock habit repository.
        :param patched_create_repository: Patched habit repository class.
        :param patched_aggregate: Patched mock aggregate function.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        habits = [
            Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
                datetime(2026, 5, 11, 12, 15, 40),
                datetime(2026, 5, 14, 16, 20, 49),
            )),
            Habit(2, "Call grandparents", Periodicity.WEEKLY, datetime(2026, 4, 17, 13, 30, 16), (
                datetime(2026, 4, 22, 12, 15, 40),
                datetime(2026, 5, 6, 13, 42, 21),
            )),
            Habit(3, "Go to gym", Periodicity.WEEKLY, datetime(2026, 4, 17, 14, 49, 21), ()),
        ]
        analysis_range = AnalysisRange(None, date(2026, 5, 12))
        analysis = AggregateAnalysis(1, 1, 2, 2.0 / 3.0)
        filters = [HabitAnalysisFilter.by_search_match("o")]
        mock_repository.read_all.return_value = habits
        patched_aggregate.return_value = analysis
        service = HabitService(mock_connection)

        result = service.analyse(filters, analysis_range)

        mock_repository.read_all.assert_called_once()
        patched_aggregate.assert_called_once_with(habits, filters, analysis_range, MOCK_NOW)
        assert result == analysis


@pytest.fixture()
def connection():
    """
    Creates a connection to a seeded in-memory SQLite database. The database is seeded with the 6 predefined habits
    that are provided by the debug seeding module, created with reference to the mock present date and time.

    The connection is closed as part of post-test cleanup.

    :return: Connection.
    """
    connection = get_connection(":memory:")
    habits = make_test_habits(MOCK_NOW)
    insert_raw(connection, habits)

    yield connection

    # Clean up.
    connection.close()


@pytest.fixture()
def analyses():
    """
    Returns the 6 predefined habits and expected analyses that are provided by the debug seeding module, created with
    reference to the mock present date and time.

    :return: Habit analyses.
    """
    return make_test_habit_analyses(MOCK_NOW)


@pytest.fixture()
def aggregate_analysis():
    """
    Returns the expected aggregate analysis for the 6 predefined habits, provided by the debug seeding module.

    :return: Aggregate analysis.
    """
    return make_test_aggregate_analysis()


class TestHabitServiceIntegration:
    """
    Tests HabitService using integration tests, with a real (in-memory) SQLite database connection, real repository,
    and real analytics module.
    """

    def test_create(self, connection: Connection, patched_now: Mock):
        """
        Tests HabitService.create.

        :param connection: Connection to a seeded database.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        expected = HabitAnalysis(Habit(7, "Go to gym", Periodicity.WEEKLY, MOCK_NOW, ()), 0, 0, 0.0, True)
        service = HabitService(connection)

        service.create("Go to gym", Periodicity.WEEKLY)
        # Roll back any uncommitted data, which is what happens when the CLI application closes.
        connection.rollback()
        result = service.get_one("Go to gym", AnalysisRange(None, None))

        assert result == expected

    def test_edit(self, connection: Connection, analyses: list[HabitAnalysis], patched_now: Mock):
        """
        Tests HabitService.edit.

        :param connection: Connection to a seeded database.
        :param analyses: Test habit analyses based on the mock current date and time.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        original = analyses[3]
        expected = HabitAnalysis(
            Habit(original.habit.id, "Go to gym", original.habit.periodicity, original.habit.created_at,
                  original.habit.completions), original.streak, original.longest_streak, original.failure_rate,
            original.pending)
        service = HabitService(connection)

        service.edit("Do laundry", "Go to gym")
        connection.rollback()
        result = service.get_one("Go to gym", AnalysisRange(None, None))

        assert result == expected

    def test_delete(self, connection: Connection, patched_now: Mock):
        """
        Tests HabitService.delete.

        :param connection: Connection to a seeded database.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        service = HabitService(connection)

        service.delete("Do laundry")
        connection.rollback()
        with pytest.raises(HabitNotFoundException):
            service.get_one("Do laundry", AnalysisRange(None, None))

    def test_complete(self, connection: Connection, analyses: list[HabitAnalysis], patched_now: Mock):
        """
        Tests HabitService.complete.

        :param connection: Connection to a seeded database.
        :param analyses: Test habit analyses based on the mock current date and time.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        original = analyses[2]
        expected_completions = tuple([*original.habit.completions, MOCK_NOW])
        # Streak should change from original 0 to 1 and the habit should no longer be pending for the current period.
        expected = HabitAnalysis(
            Habit(original.habit.id, original.habit.name, original.habit.periodicity, original.habit.created_at,
                  expected_completions), 1, original.longest_streak, original.failure_rate, False)
        service = HabitService(connection)

        service.complete("Call grandparents")
        connection.rollback()
        result = service.get_one("Call grandparents", AnalysisRange(None, None))

        assert result == expected

    def test_get_one(self, connection: Connection, analyses: list[HabitAnalysis], patched_now: Mock):
        """
        Tests HabitService.get_one.

        :param connection: Connection to a seeded database.
        :param analyses: Test habit analyses based on the mock current date and time.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        service = HabitService(connection)

        result = service.get_one("Do morning exercise", AnalysisRange(None, None))

        assert result == analyses[1]

    def test_get_many(self, connection: Connection, analyses: list[HabitAnalysis], patched_now: Mock):
        """
        Tests HabitService.get_many.

        :param connection: Connection to a seeded database.
        :param analyses: Test habit analyses based on the mock current date and time.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        service = HabitService(connection)

        result = service.get_many([], HabitAnalysisOrder(lambda analysis: analysis.habit.id, True),
                                  AnalysisRange(None, None))

        assert result == analyses

    def test_analyse(self, connection: Connection, aggregate_analysis: AggregateAnalysis, patched_now: Mock):
        """
        Tests HabitService.analyse.

        :param connection: Connection to a seeded database.
        :param aggregate_analysis: Test aggregate analysis.
        :param patched_now: Patched datetime.now function.
        :return: Nothing.
        """
        service = HabitService(connection)

        result = service.analyse([], AnalysisRange(None, None))

        assert result.habit_count == aggregate_analysis.habit_count
        assert result.current_longest_streak == aggregate_analysis.current_longest_streak
        assert result.longest_streak == aggregate_analysis.longest_streak
        # Necessary to do the approximate comparison because of the tiny imprecision introduced by floating-point
        # arithmetic.
        assert result.avg_failure_rate == pytest.approx(aggregate_analysis.avg_failure_rate)
