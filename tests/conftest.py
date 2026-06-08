from dataclasses import dataclass
from datetime import datetime
from sqlite3 import Connection

import pytest
from pytest_mock import MockerFixture

from habitline.analytics import HabitAnalysis
from habitline.repository import Periodicity, Habit, HabitRepository
from habitline.service import HabitService

MOCK_ID = 1
MOCK_NAME = "Lorem ipsum"
MOCK_PERIODICITY = Periodicity.DAILY
MOCK_CREATED_AT = datetime(2026, 5, 10, 16, 38, 21)
MOCK_COMPLETIONS = ()
MOCK_STREAK = 2
MOCK_LONGEST_STREAK = 4
MOCK_FAILURE_RATE = 1.0 / 3.0
MOCK_PENDING = True
MOCK_NOW = datetime(2026, 5, 14, 18, 12, 30)


def make_mock_habit(id: int | None = None, name: str | None = None, periodicity: Periodicity | None = None,
                    created_at: datetime | None = None, completions: tuple[datetime, ...] | None = None) -> Habit:
    """
    Makes a test habit using the provided field values, filling missing information with mock defaults.

    The primary use case for this is creating test data for contexts where only a part of the supported fields are
    relevant.

    :param id: Numeric identifier of the habit. Defaults to 1.
    :param name: Name of the habit. Defaults to "Lorem ipsum".
    :param periodicity: Periodicity of the habit. Defaults to daily.
    :param created_at: Date and time the habit was created. Defaults to "2026-05-13T16:38:21".
    :param completions: Tuple of dates and times of the habit's logged completions in chronological order. Defaults to being empty.
    :return: Created habit.
    """
    return Habit(id if id is not None else MOCK_ID,
                 name if name is not None else MOCK_NAME,
                 periodicity if periodicity is not None else MOCK_PERIODICITY,
                 created_at if created_at is not None else MOCK_CREATED_AT,
                 completions if completions is not None else MOCK_COMPLETIONS)


@dataclass(frozen=True)
class HabitAnalysisResult:
    """
    Individual habit analysis result, without the underlying habit. Used for expected test output specification purposes.

    Attributes:
        streak: Current streak length in periods, possibly constrained by the analysis period.
        longest_streak: Longest streak length in periods, possibly constrained by the analysis period.
        failure_rate: Failure rate of habit completions (percentage of periods that were failed) from 0 to 1, possibly constrained by the analysis period. Only covers past periods, since the current period is not over and thus cannot have been failed.
        pending: Whether the habit has yet to be completed in the current period.
    """
    streak: int
    longest_streak: int
    failure_rate: float
    pending: bool


def make_mock_analysis_result(streak: int | None = None, longest_streak: int | None = None,
                              failure_rate: float | None = None, pending: bool | None = None) -> HabitAnalysisResult:
    """
    Makes a test habit analysis result using the provided field values, filling missing information with mock defaults.

    :param streak: Current streak length in periods, possibly constrained by the analysis period. Defaults to 2.
    :param longest_streak: Longest streak length in periods, possibly constrained by the analysis period. Defaults to 4.
    :param failure_rate: Failure rate of habit completions (percentage of periods that were failed) from 0 to 1, possibly constrained by the analysis period. Defaults to 1.0/3.0.
    :param pending: Whether the habit has yet to be completed in the current period. Defaults to True.
    :return: Created habit analysis result.
    """
    return HabitAnalysisResult(streak if streak is not None else MOCK_STREAK,
                               longest_streak if longest_streak is not None else MOCK_LONGEST_STREAK,
                               failure_rate if failure_rate is not None else MOCK_FAILURE_RATE,
                               pending if pending is not None else MOCK_PENDING)


def make_mock_analysis(id: int | None = None, name: str | None = None, periodicity: Periodicity | None = None,
                       created_at: datetime | None = None, completions: tuple[datetime, ...] | None = None,
                       streak: int | None = None, longest_streak: int | None = None,
                       failure_rate: float | None = None, pending: bool | None = None) -> HabitAnalysis:
    """
    Makes a test habit analysis, including the underlying habit, using the provided field values,
    filling missing information with mock defaults.

    The primary use case for this is creating test data for contexts where only a part of the supported fields are
    relevant.

    :param id: Numeric identifier of the habit. Defaults to 1.
    :param name: Name of the habit. Defaults to "Lorem ipsum".
    :param periodicity: Periodicity of the habit. Defaults to daily.
    :param created_at: Date and time the habit was created. Defaults to "2026-05-13T16:38:21".
    :param completions: Tuple of dates and times of the habit's logged completions in chronological order. Defaults to being empty.
    :param streak: Current streak length in periods, possibly constrained by the analysis period. Defaults to 2.
    :param longest_streak: Longest streak length in periods, possibly constrained by the analysis period. Defaults to 4.
    :param failure_rate: Failure rate of habit completions (percentage of periods that were failed) from 0 to 1, possibly constrained by the analysis period. Defaults to 1.0/3.0.
    :param pending: Whether the habit has yet to be completed in the current period. Defaults to True.
    :return: Created habit analysis.
    """
    habit = Habit(id if id is not None else MOCK_ID,
                  name if name is not None else MOCK_NAME,
                  periodicity if periodicity is not None else MOCK_PERIODICITY,
                  created_at if created_at is not None else MOCK_CREATED_AT,
                  completions if completions is not None else MOCK_COMPLETIONS)
    return HabitAnalysis(habit,
                         streak if streak is not None else MOCK_STREAK,
                         longest_streak if longest_streak is not None else MOCK_LONGEST_STREAK,
                         failure_rate if failure_rate is not None else MOCK_FAILURE_RATE,
                         pending if pending is not None else MOCK_PENDING)


@pytest.fixture(scope="function")
def mock_connection(mocker: MockerFixture):
    """
    Creates a mock database connection.

    :param mocker: Mocker fixture.
    :return: Mock database connection.
    """
    mock_connection = mocker.MagicMock(spec=Connection)
    mock_cursor = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.execute.return_value = mock_cursor
    return mock_connection


@pytest.fixture()
def mock_repository(mocker: MockerFixture):
    """
    Creates a mock HabitRepository.

    :param mocker: Mocker fixture.
    :return: Mock class.
    """
    return mocker.MagicMock(spec=HabitRepository)


@pytest.fixture()
def mock_service(mocker: MockerFixture):
    """
    Creates a mock HabitService.

    :param mocker: Mocker fixture.
    :return: Mock class.
    """
    return mocker.MagicMock(spec=HabitService)
