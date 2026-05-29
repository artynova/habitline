from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from repository import Habit


@dataclass(frozen=True)
class HabitAnalysis:
    """Stores habit data derived during analysis, such as streaks, as well as the underlying habit data."""
    habit: Habit
    streak: int
    longest_streak: int
    success_rate: float
    pending: bool


@dataclass(frozen=True)
class AggregateAnalysis:
    """Container for data derived during aggregate analysis of a habit collection."""
    longest_streak: int
    success_rate: float


# Habit filter, returning a boolean indicating whether the input habit should be kept or removed.
# Is based on either basic habit data or analysis results.
HabitFilter = Callable[[HabitAnalysis], bool]

# Habit comparison strategy, defined by the comparison key retrieval function
# Is based on either basic habit data or analysis results.
HabitComparator = Callable[[HabitAnalysis], any]


@dataclass(frozen=True)
class AnalysisPeriod:
    """
    Analysis period specification consisting of the lower and upper bounds.
    An absent bound represents no restriction in the corresponding direction.

    Attributes:
        start: Start of the period (optional lower bound).
        end: End of the period (optional upper bound).
    """
    start: datetime | None
    end: datetime | None


def analyse_one(habit: Habit, period: AnalysisPeriod, now: datetime) -> HabitAnalysis:
    """
    Analyses a single habit.

    :param habit: Habit to analyse.
    :param period: Analysis period.
    :param now: Current date and time.
    :return: Analysed habit.
    """
    pass


def analyse_many(habits: list[Habit], filters: list[HabitFilter], comparator: HabitComparator, sort_asc: bool,
                 period: AnalysisPeriod, now: datetime) -> list[HabitAnalysis]:
    """
    Analyses a list of habits with filtering, sorting, and period limitation for completions.

    :param habits: List of habits.
    :param filters: List of filter functions for analysed habits.
    :param comparator: Function retrieving the comparison key from an analysed habit.
    :param sort_asc: Whether to sort in ascending order.
    :param period: Analysis period.
    :param now: Current date and time.
    :return: List of analysed habits.
    """
    pass


def aggregate(habits: list[Habit], filters: list[HabitFilter], period: AnalysisPeriod,
              now: datetime) -> AggregateAnalysis:
    """
    Determines aggregate metrics for a list of habits with filtering and period limitation for completions.

    :param habits: List of habits.
    :param filters: List of filter functions for analysed habits.
    :param period: Analysis period.
    :param now: Current date and time.
    :return: Results of aggregate analysis.
    """
    pass
