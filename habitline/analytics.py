from dataclasses import dataclass
from datetime import datetime, date, timedelta
from functools import reduce
from typing import Callable

from habitline.repository import Habit, Periodicity


@dataclass(frozen=True)
class HabitAnalysis:
    """
    Stores habit data derived during analysis, such as streaks, as well as the underlying habit data.

    Attributes:
        habit: Underlying habit data.
        streak: Current streak length in periods, possibly constrained by the analysis period.
        longest_streak: Longest streak length in periods, possibly constrained by the analysis period.
        failure_rate: Failure rate of habit completions (percentage of periods that were failed) from 0 to 1, possibly constrained by the analysis period. Only covers past periods, since the current period is not over and thus cannot have been failed.
        pending: Whether the habit has yet to be completed in the current period.
    """
    habit: Habit
    streak: int
    longest_streak: int
    failure_rate: float
    pending: bool


@dataclass(frozen=True)
class AggregateAnalysis:
    """
    Stores data derived during aggregate analysis of a habit collection.

    When streaks of habits with daily periodicities are compared, the comparison ignores the period length. For example,
    a streak of 3 days for a daily habit is a period longer than a streak of 2 weeks for a weekly habit.

    Attributes:
        habit_count: Number of habits analysed.
        current_longest_streak: Length of the current longest streak among all habits in periods, possibly constrained by the analysis period.
        longest_streak: Length of the overall longest streak among all habits in periods, possibly constrained by the analysis period.
        avg_failure_rate: Average failure rate of habit completions (percentage of periods that were failed) from 0 to 1, possibly constrained by the analysis period. Only covers past periods, since the current period is not over and thus cannot have been failed.
    """
    habit_count: int
    current_longest_streak: int
    longest_streak: int
    avg_failure_rate: float


# Habit analysis filter, returning a boolean indicating whether the input habit (with analysis) should be kept or
# removed. Is based on either basic habit data or analysis results.
@dataclass(frozen=True)
class HabitAnalysisFilter:
    """
    Habit analysis filter.

    Attributes:
        fn: Function that returns whether the passed analysis entry should be kept.
    """
    fn: Callable[[HabitAnalysis], bool]

    @staticmethod
    def by_periodicity(periodicity: Periodicity) -> "HabitAnalysisFilter":
        return HabitAnalysisFilter(lambda analysis: analysis.habit.periodicity == periodicity)

    @staticmethod
    def by_pending(pending: bool) -> "HabitAnalysisFilter":
        return HabitAnalysisFilter(lambda analysis: analysis.pending == pending)

    @staticmethod
    def by_search_match(name: str) -> "HabitAnalysisFilter":
        return HabitAnalysisFilter(lambda analysis: name.lower() in analysis.habit.name.lower())


@dataclass(frozen=True)
class HabitAnalysisOrder:
    """
    Habit analysis order.

    Attributes:
        key: Function to retrieve the comparison key.
        asc: Whether to sort in ascending order.
    """
    key: Callable[[HabitAnalysis], any]
    asc: bool

    @staticmethod
    def by_name(asc: bool) -> "HabitAnalysisOrder":
        return HabitAnalysisOrder(lambda analysis: analysis.habit.name, asc)

    @staticmethod
    def by_created_at(asc: bool) -> "HabitAnalysisOrder":
        return HabitAnalysisOrder(lambda analysis: analysis.habit.created_at, asc)

    @staticmethod
    def by_streak(asc: bool) -> "HabitAnalysisOrder":
        return HabitAnalysisOrder(lambda analysis: analysis.streak, asc)

    @staticmethod
    def by_longest_streak(asc: bool) -> "HabitAnalysisOrder":
        return HabitAnalysisOrder(lambda analysis: analysis.longest_streak, asc)

    @staticmethod
    def by_failure_rate(asc: bool) -> "HabitAnalysisOrder":
        return HabitAnalysisOrder(lambda analysis: analysis.failure_rate, asc)


@dataclass(frozen=True)
class AnalysisRange:
    """
    Analysis date range specification consisting of the lower and upper bounds.
    An absent bound represents no restriction in the corresponding direction.

    Attributes:
        start: Start of the range (optional lower bound).
        end: End of the range (optional upper bound).
    """
    start: date | None
    end: date | None


# Mapping of habit periodicities to their date behaviours, represented as tuples.
# The first tuple item is the day step between adjacent periods (e.g., 7 for weekly habits).
# The second tuple item is a function that transforms a given date into the start of the period it falls
# into (e.g., the first day of the corresponding week for weekly habits).
HABIT_PERIOD_BEHAVIOURS: dict[Periodicity, tuple[int, Callable[[date], date]]] = {
    Periodicity.DAILY: (1, lambda day: day),
    Periodicity.WEEKLY: (7, lambda day: day - timedelta(days=day.weekday())),
}


def analyse_one(habit: Habit, analysis_range: AnalysisRange, now: datetime) -> HabitAnalysis:
    """
    Analyses a single habit, constraining the considered completion periods to only those overlapping with the
    analysis range. This includes periods that are partly, but not fully within the range - for example, if the range
    starts on a Tuesday and the habit is weekly, the period that Tuesday falls into will be fully considered, starting
    from Monday.

    :param habit: Habit to analyse.
    :param analysis_range: Analysis range.
    :param now: Current date and time.
    :return: Analysed habit.
    """
    period_step, get_period_start = HABIT_PERIOD_BEHAVIOURS[habit.periodicity]
    # Determine true analysis range, which fully covers all periods touched by the provided range.
    resolved_start = max(analysis_range.start,
                         habit.created_at.date()) if analysis_range.start else habit.created_at.date()
    resolved_end = min(analysis_range.end, now.date()) if analysis_range.end else now.date()
    true_range = AnalysisRange(get_period_start(resolved_start),
                               get_period_start(resolved_end) + timedelta(days=period_step - 1))
    # Total periods in the analysed range, possibly counting the currently ongoing period.
    total_periods = ((true_range.end - true_range.start).days + 1) // period_step
    # If the present date falls within the last period of the range, that means the period is still ongoing.
    last_range_period_is_current = get_period_start(true_range.end) == get_period_start(now.date())
    past_periods = total_periods - 1 if last_range_period_is_current else total_periods

    # Case for new habits.
    if not habit.completions:
        # Since there are no completions, if the analysis period encompasses at least one past period, that period was
        # failed and the failure rate is 100%. If only the current period is included, however, then it has not been
        # failed, and there are no failed periods, meaning the failure rate is 0%.
        return HabitAnalysis(habit, 0, 0, 1.0 if past_periods > 0 else 0.0, True)

    # Filter completions to only those that are in the analysed range.
    completions: list[datetime] = list(filter(
        lambda completion: (true_range.start is None or completion.date() >= true_range.start) and (
                true_range.end is None or completion.date() <= true_range.end), habit.completions))
    # Habit is pending if the last completion does NOT fall on the current period.
    habit_pending = habit.completions[-1].date() < get_period_start(now.date())

    # Case where no completions are to be analysed due to time range constraints, but the habit does have completions
    # and thus may or may not be pending.
    if not completions:
        return HabitAnalysis(habit, 0, 0, 1.0 if past_periods > 0 else 0.0, habit_pending)

    last_completion_period_is_current = get_period_start(completions[-1].date()) == get_period_start(now.date())
    completed_periods = 0
    streak = 0
    longest_streak = 0
    # The period-advancing step assumes that at least one previous completion exists, which is always true except
    # for the first completion. Therefore, the next_period_start is set to the next period relative to the first
    # completion, to ensure that the algorithm never attempts the step for the first completion.
    next_period_start = get_period_start(completions[0].date()) + timedelta(days=period_step)
    for completion in completions:
        if completion.date() >= next_period_start:
            # Count the previous completion when we shift periods
            completed_periods += 1
            streak += 1

            # Find how many periods elapsed between the previous completion's period and this completion's period
            # If more than 1, then some periods were skipped, and the streak has to be broken.
            new_next_period_start = get_period_start(completion.date()) + timedelta(days=period_step)
            period_diff = (new_next_period_start - next_period_start).days / period_step
            next_period_start = new_next_period_start
            if period_diff > 1:
                longest_streak = max(longest_streak, streak)
                streak = 0
    # The loop only counted each period when moving to the next period, so the final period and its completions
    # (at least one guaranteed since the list is non-empty) were not counted, and have to be counted here.
    completed_periods += 1
    streak += 1
    longest_streak = max(longest_streak, streak)
    # Determine if the streak currently holds.
    # If the last range period is in the present, the streak should be preserved if only the last period does not have a
    # completion since absence of completion in the current period is not a streak-breaking failure (the user can still
    # complete it before the period ends). Therefore, the minimum number of periods needed in the difference is 2.
    # If the last range period is in the past, then any period difference (1 or above) means streak-breaking failure
    # since the user cannot go back to the past and retroactively complete the period.
    min_periods_to_break_final_streak = 2 if last_range_period_is_current else 1
    last_completion_to_end_period_diff = (get_period_start(true_range.end) - get_period_start(
        completions[-1].date())).days / period_step
    if last_completion_to_end_period_diff >= min_periods_to_break_final_streak:
        streak = 0

    # If the final completion belongs to the currently ongoing period, then its period is included in the
    # completed_periods count, and this period should be subtracted to obtain the number of past completed periods.
    past_completed_periods = completed_periods - 1 if last_completion_period_is_current else completed_periods
    failure_rate = 0.0 if past_periods == 0 else (past_periods - past_completed_periods) / past_periods
    return HabitAnalysis(habit, streak, longest_streak, failure_rate, habit_pending)


def analyse_many(habits: list[Habit], filters: list[HabitAnalysisFilter], order: HabitAnalysisOrder,
                 analysis_range: AnalysisRange, now: datetime) -> list[
    HabitAnalysis]:
    """
    Analyses a list of habits with filtering, sorting, and period limitation for completions.

    :param habits: List of habits.
    :param filters: List of filters for analysed habits.
    :param order: Analysed habit order. Ties created by this order will be broken using the habit creation date.
    :param analysis_range: Analysis range.
    :param now: Current date and time.
    :return: List of analysed habits.
    """
    analysed_habits = [analyse_one(habit, analysis_range, now) for habit in habits]
    filtered_analyses = filter(lambda habit: all([analysis_filter.fn(habit) for analysis_filter in filters]),
                               analysed_habits)
    # Pre-sort by the creation date so that, in case of ties in the main sort, the tied analyses are naturally ordered
    # by the habit creation date.
    pre_sorted = sorted(filtered_analyses, key=lambda analysis: analysis.habit.created_at)
    return sorted(pre_sorted, key=order.key, reverse=not order.asc)


def aggregate(habits: list[Habit], filters: list[HabitAnalysisFilter], analysis_range: AnalysisRange,
              now: datetime) -> AggregateAnalysis:
    """
    Determines aggregate metrics for a list of habits with filtering and period limitation for completions.

    :param habits: List of habits.
    :param filters: List of filters for analysed habits.
    :param analysis_range: Analysis period.
    :param now: Current date and time.
    :return: Results of aggregate analysis.
    """
    analysed_habits = [analyse_one(habit, analysis_range, now) for habit in habits]
    filtered_analyses: list[HabitAnalysis] = list(
        filter(lambda habit: all([analysis_filter.fn(habit) for analysis_filter in filters]), analysed_habits))
    habit_count = len(filtered_analyses)
    if habit_count == 0:
        # No habits means no failures.
        return AggregateAnalysis(0, 0, 0, 0.0)
    current_longest_streak = reduce(lambda prev_longest, analysis: max(prev_longest, analysis.streak),
                                    filtered_analyses, 0)
    longest_streak = reduce(lambda prev_longest, analysis: max(prev_longest, analysis.longest_streak),
                            filtered_analyses, 0)
    avg_failure_rate = sum([analysis.failure_rate for analysis in filtered_analyses]) / habit_count
    return AggregateAnalysis(habit_count, current_longest_streak, longest_streak, avg_failure_rate)
