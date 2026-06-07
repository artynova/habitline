from datetime import datetime, date
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from habitline.analytics import AnalysisRange, HabitAnalysis, HabitAnalysisFilter, HabitAnalysisOrder, AggregateAnalysis
from habitline.repository import Periodicity, HabitNameTakenException, HabitNotFoundException, HabitIdentifier, Habit
from habitline.service import HabitService
from tests.conftest import MOCK_NOW


@pytest.fixture()
def mock_repository(mocker: MockerFixture):
    """
    Patches the HabitRepository class to create a mock object and returns the mock.

    :param mocker: Mocker fixture.
    :return: Mock class.
    """
    return mocker.patch('habitline.service.HabitRepository').return_value


@pytest.fixture()
def mock_now(mocker: MockerFixture):
    """
    Patches datetime.now to return a fixed datetime and returns that datetime.

    :param mocker: Mocker fixture.
    :return: Mock value.
    """
    mock_datetime = mocker.patch("habitline.service.datetime")
    mock_datetime.now.return_value = MOCK_NOW
    return MOCK_NOW


@pytest.fixture()
def mock_analyse_one(mocker: MockerFixture):
    """
    Patches the analyse_one analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Mock function.
    """
    return mocker.patch("habitline.service.analyse_one")


@pytest.fixture()
def mock_analyse_many(mocker: MockerFixture):
    """
    Patches the analyse_many analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Mock function.
    """
    return mocker.patch("habitline.service.analyse_many")


@pytest.fixture()
def mock_aggregate(mocker: MockerFixture):
    """
    Patches the aggregate analytics function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Mock function.
    """
    return mocker.patch("habitline.service.aggregate")


class TestHabitService:
    """
    Tests HabitService with unit tests.
    """

    def test_create_failure_name_taken(self, mock_connection: Mock, mock_repository: Mock, mock_now: datetime):
        """
        Tests HabitService.create failure outcome when the provided name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param mock_now: Mock current date and time.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY
        mock_repository.create.side_effect = HabitNameTakenException(name)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNameTakenException):
            service.create(name, periodicity)

        mock_repository.create.assert_called_once_with(name, periodicity, mock_now)

    def test_create_success(self, mock_connection: Mock, mock_repository: Mock, mock_now: datetime):
        """
        Tests HabitService.create success outcome.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param mock_now: Mock current date and time.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY
        service = HabitService(mock_connection)

        service.create(name, periodicity)

        mock_repository.create.assert_called_once_with(name, periodicity, mock_now)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                          identifier: HabitIdentifier):
        """
        Tests HabitService.edit failure outcome when trying to change the name of a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
    def test_edit_failure_name_taken(self, mock_connection: Mock, mock_repository: Mock, identifier: HabitIdentifier):
        """
        Tests HabitService.edit failure outcome when the provided new name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
    def test_edit_success(self, mock_connection: Mock, mock_repository: Mock, identifier: HabitIdentifier):
        """
        Tests HabitService.edit success outcome.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
                                            identifier: HabitIdentifier):
        """
        Tests HabitService.delete failure outcome when trying to delete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
    def test_delete_success(self, mock_connection: Mock, mock_repository: Mock, identifier: HabitIdentifier):
        """
        Tests HabitService.delete success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
    def test_complete_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock, mock_now: datetime,
                                              identifier: HabitIdentifier):
        """
        Tests HabitService.complete failure outcome when trying to complete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_repository.complete.side_effect = HabitNotFoundException(identifier)
        service = HabitService(mock_connection)

        with pytest.raises(HabitNotFoundException):
            service.complete(identifier)

        mock_repository.complete.assert_called_once_with(identifier, mock_now)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_success(self, mock_connection: Mock, mock_repository: Mock, mock_now: datetime,
                              identifier: HabitIdentifier):
        """
        Tests HabitService.complete success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        service = HabitService(mock_connection)

        service.complete(identifier)

        mock_repository.complete.assert_called_once_with(identifier, mock_now)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_get_one_failure_habit_not_found(self, mock_connection: Mock, mock_repository: Mock,
                                             identifier: HabitIdentifier):
        """
        Tests HabitService.get_one success.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
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
    def test_get_one_success(self, mock_connection: Mock, mock_repository: Mock, mock_analyse_one: Mock,
                             mock_now: datetime, identifier: HabitIdentifier):
        """
        Tests HabitService.get_one success.
        
        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param mock_analyse_one: Patched mock analyse_one function.
        :param mock_now: Mock current date and time.
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
        mock_analyse_one.return_value = analysis
        service = HabitService(mock_connection)

        result = service.get_one(identifier, analysis_range)

        mock_repository.read_one.assert_called_once_with(identifier)
        mock_analyse_one.assert_called_once_with(habit, analysis_range, mock_now)
        assert result == analysis

    def test_get_many(self, mock_connection: Mock, mock_repository: Mock, mock_analyse_many: Mock, mock_now: datetime):
        """
        Tests HabitService.get_many.
        
        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param mock_analyse_many: Patched mock analyse_many function.
        :param mock_now: Mock current date and time.
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
        mock_analyse_many.return_value = analyses
        service = HabitService(mock_connection)

        result = service.get_many(filters, order, analysis_range)

        mock_repository.read_all.assert_called_once()
        mock_analyse_many.assert_called_once_with(habits, filters, order, analysis_range, mock_now)
        assert result == analyses

    def test_analyse(self, mock_connection: Mock, mock_repository: Mock, mock_aggregate: Mock, mock_now: datetime):
        """
        Tests HabitService.analyse.

        :param mock_connection: Mock database connection.
        :param mock_repository: Patched mock habit repository.
        :param mock_aggregate: Patched mock aggregate function.
        :param mock_now: Mock current date and time.
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
        mock_aggregate.return_value = analysis
        service = HabitService(mock_connection)

        result = service.analyse(filters, analysis_range)

        mock_repository.read_all.assert_called_once()
        mock_aggregate.assert_called_once_with(habits, filters, analysis_range, mock_now)
        assert result == analysis
