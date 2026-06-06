from datetime import datetime, date
from typing import Callable
from unittest.mock import Mock, call

import pytest

from habitline.analytics import AnalysisRange, analyse_one, HabitAnalysisFilter, HabitAnalysis, HabitAnalysisOrder, \
    analyse_many, aggregate, AggregateAnalysis
from habitline.repository import Periodicity, Habit
from tests.conftest import make_mock_habit, make_mock_analysis, MOCK_STREAK, MOCK_LONGEST_STREAK, MOCK_FAILURE_RATE, \
    MOCK_PENDING, HabitAnalysisResult, make_mock_analysis_result


def make_mock_analyse_one(id_result_map: dict[int, HabitAnalysisResult] | None = None) -> Callable[
    [Habit, AnalysisRange, datetime], HabitAnalysis]:
    """
    Creates a mocked version of the analyse_one analytics function for habits based on the provided mapping between
    habit IDs and analysis results. If the mock function receives a habit it does not have a mapping for, it produces
    a default mocked analysis result.

    :param id_result_map: Dictionary mapping habit IDs to habit analysis results, or None, in which case an empty dictionary is used.
    :return: Mocked analyse_one function.
    """
    if id_result_map is None:
        id_result_map = {}

    def mock_analyse_one(habit: Habit, _analysis_range: AnalysisRange, _now: datetime) -> HabitAnalysis:
        result = id_result_map.get(habit.id)
        if result is None:
            return HabitAnalysis(habit, MOCK_STREAK, MOCK_LONGEST_STREAK, MOCK_FAILURE_RATE, MOCK_PENDING)
        return HabitAnalysis(habit, result.streak, result.longest_streak, result.failure_rate, result.pending)

    return mock_analyse_one


# Neutral order, returning the same value as comparison key for every analysis.
NEUTRAL_ORDER = HabitAnalysisOrder(lambda _analysis: 1, True)


class TestAnalytics:
    """
    Tests the analytics module with unit tests.
    """

    @pytest.mark.parametrize(["analysis_filter", "analysis", "expected"], [
        # Periodicity filter
        pytest.param(HabitAnalysisFilter.by_periodicity(Periodicity.DAILY),
                     make_mock_analysis(periodicity=Periodicity.DAILY), True, id="by_periodicity_daily_pass"),
        pytest.param(HabitAnalysisFilter.by_periodicity(Periodicity.DAILY),
                     make_mock_analysis(periodicity=Periodicity.WEEKLY), False, id="by_periodicity_daily_fail"),
        pytest.param(HabitAnalysisFilter.by_periodicity(Periodicity.WEEKLY),
                     make_mock_analysis(periodicity=Periodicity.WEEKLY), True, id="by_periodicity_weekly_pass"),
        pytest.param(HabitAnalysisFilter.by_periodicity(Periodicity.WEEKLY),
                     make_mock_analysis(periodicity=Periodicity.DAILY), False, id="by_periodicity_weekly_fail"),

        # Pending filter
        pytest.param(HabitAnalysisFilter.by_pending(True), make_mock_analysis(pending=True), True,
                     id="by_pending_true_pass"),
        pytest.param(HabitAnalysisFilter.by_pending(True), make_mock_analysis(pending=False), False,
                     id="by_pending_true_fail"),
        pytest.param(HabitAnalysisFilter.by_pending(False), make_mock_analysis(pending=False), True,
                     id="by_pending_false_pass"),
        pytest.param(HabitAnalysisFilter.by_pending(False), make_mock_analysis(pending=True), False,
                     id="by_pending_false_fail"),

        # Name search filter
        pytest.param(HabitAnalysisFilter.by_search_match("jo"), make_mock_analysis(name="Journal"), True,
                     id="by_search_match_included_different_case"),
        pytest.param(HabitAnalysisFilter.by_search_match("UR"), make_mock_analysis(name="Journal"), True,
                     id="by_search_match_included_middle_different_case"),
        pytest.param(HabitAnalysisFilter.by_search_match(""), make_mock_analysis(name="Journal"), True,
                     id="by_search_match_empty"),
        pytest.param(HabitAnalysisFilter.by_search_match("jo"), make_mock_analysis(name="Take a walk"), False,
                     id="by_search_match_not_included"),
    ])
    def test_habit_analysis_filter(self, analysis_filter: HabitAnalysisFilter, analysis: HabitAnalysis, expected: bool):
        """
        Tests HabitAnalysisFilter.

        :param analysis_filter: Filter to test.
        :param analysis: Habit analysis to test with.
        :param expected: Expected result.
        :return: Nothing.
        """
        actual = analysis_filter.fn(analysis)

        assert actual == expected

    @pytest.mark.parametrize(["analysis_order", "analysis", "expected_key"], [
        pytest.param(HabitAnalysisOrder.by_name(True), make_mock_analysis(name="Journal"), "Journal", id="by_name"),
        pytest.param(HabitAnalysisOrder.by_created_at(False),
                     make_mock_analysis(created_at=datetime(2026, 5, 16, 21, 13, 20)),
                     datetime(2026, 5, 16, 21, 13, 20),
                     id="by_created_at"),
        pytest.param(HabitAnalysisOrder.by_streak(True), make_mock_analysis(streak=6), 6, id="by_streak"),
        pytest.param(HabitAnalysisOrder.by_longest_streak(False), make_mock_analysis(longest_streak=13), 13,
                     id="by_longest_streak"),
        pytest.param(HabitAnalysisOrder.by_failure_rate(True), make_mock_analysis(failure_rate=0.777), 0.777,
                     id="by_failure_rate"),
    ])
    def test_habit_analysis_order(self, analysis_order: HabitAnalysisOrder, analysis: HabitAnalysis, expected_key: any):
        """
        Tests HabitAnalysisOrder.

        :param analysis_order: Habit analysis order to test.
        :param analysis: Habit analysis to test with.
        :param expected_key: Expected output of the key retrieval function from the given analysis.
        :return: Nothing.
        """
        actual = analysis_order.key(analysis)

        assert actual == expected_key

    @pytest.mark.parametrize(["habit", "analysis_range", "now", "expected_result"], [
        # Daily habit tests without time range limitations.
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 14, 13, 30, 16),
                            completions=()),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 0.0, True),
            id="daily_new"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16),
                            completions=()),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 1.0, True),
            id="daily_no_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 12, 14, 56, 23),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 1, 0.75, True),
            id="daily_one_completion"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.5, True),
            id="daily_two_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(3, 3, 0.25, True),
            id="daily_streak_pending"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
                    datetime(2026, 5, 14, 16, 20, 49),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(4, 4, 0.25, False),
            id="daily_streak_completed"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 2, 0.5, True),
            id="daily_streak_broken"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 11, 16, 8, 31),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 14, 16, 20, 49),
                    datetime(2026, 5, 14, 17, 16, 19),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(1, 2, 0.5, False),
            id="daily_streak_multiple_completions"),

        # Daily habit tests with time range limitations.
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 12), None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.0, True),
            id="daily_limit_start"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(None, date(2026, 5, 12)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 1.0 / 3.0, True),
            id="daily_limit_end"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 12, 17, 21, 54),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 11), date(2026, 5, 12)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.0, True),
            id="daily_limit_multiple_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 4, 1), date(2026, 7, 13)), datetime(2026, 5, 14, 18, 12, 30),
            # Analysis results equivalent to when no bounds are specified, because the implicit bounds chosen due to the excessive
            # interval are the creation date and the current date, respectively.
            HabitAnalysisResult(3, 3, 0.25, True),
            id="daily_limit_clamped"),
        # A past period (day) with no completions counts as a failure
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 10), date(2026, 5, 10)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 1.0, True),
            id="daily_limit_no_completions_past"),
        # The current period (day) with no completions does not count as a failure
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 14), date(2026, 5, 14)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 0.0, True),
            id="daily_limit_no_completions_now"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 14, 16, 20, 49),
            )),
            AnalysisRange(date(2026, 5, 14), date(2026, 5, 14)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(1, 1, 0.0, False),
            id="daily_limit_completed_now"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 11), date(2026, 5, 13)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(3, 3, 0.0, True),
            id="daily_limit_streak_past"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16), completions=(
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
            )),
            AnalysisRange(date(2026, 5, 11), date(2026, 5, 13)), datetime(2026, 5, 14, 18, 12, 30),
            # The last day of the period (the 13th) lacks completions and, since it is in the past, should be
            # interpreted as a failure, and thus there also should not be any ongoing streak at the end.
            HabitAnalysisResult(0, 2, 1.0 / 3.0, True),
            id="daily_limit_streak_broken_past_last_period"),

        # Weekly habit tests without time range limitations.
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 5, 13, 13, 30, 16),
                            completions=()),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 0.0, True),
            id="weekly_new"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16),
                            completions=()),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 1.0, True),
            id="weekly_no_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 30, 14, 56, 23),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 1, 0.75, True),
            id="weekly_one_completion"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.5, True),
            id="weekly_two_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(3, 3, 0.25, True),
            id="weekly_streak_pending"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
                    datetime(2026, 5, 13, 16, 20, 49),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(4, 4, 0.25, False),
            id="weekly_streak_completed"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 2, 0.5, True),
            id="weekly_streak_broken"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 24, 16, 8, 31),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 13, 16, 20, 49),
                    datetime(2026, 5, 14, 17, 16, 19),
            )),
            AnalysisRange(None, None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(1, 2, 0.5, False),
            id="weekly_streak_multiple_completions"),

        # Weekly habit tests with time range limitations.
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            # The analysis range starts after the completion on the 30th, but the start date falls into the same
            # period, so the completion on the 30th should be included.
            AnalysisRange(date(2026, 5, 1), None), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.0, True),
            id="weekly_limit_start"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            # The analysis range ends before the completion on the 30th, but the end date falls into the same
            # period, so the completion on the 30th should be included.
            AnalysisRange(None, date(2026, 4, 28)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 1.0 / 3.0, True),
            id="weekly_limit_end"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 1, 17, 21, 54),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            # Range bounds overlapping with corresponding period bounds (e.g., starting from Monday)
            # should work correctly too.
            AnalysisRange(date(2026, 4, 20), date(2026, 5, 3)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(2, 2, 0.0, True),
            id="weekly_limit_multiple_completions"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 4, 1), date(2026, 7, 13)), datetime(2026, 5, 14, 18, 12, 30),
            # Analysis results equivalent to when no bounds are specified, because the implicit bounds chosen due to the excessive
            # interval are the creation date and the current date, respectively.
            HabitAnalysisResult(3, 3, 0.25, True),
            id="weekly_limit_clamped"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 4, 17), date(2026, 4, 18)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 1.0, True),
            id="weekly_limit_no_completions_past"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 5, 13), date(2026, 5, 14)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(0, 0, 0.0, True),
            id="weekly_limit_no_completions_now"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 5, 6, 13, 42, 21),
                    datetime(2026, 5, 13, 16, 20, 49),
            )),
            AnalysisRange(date(2026, 5, 13), date(2026, 5, 14)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(1, 1, 0.0, False),
            id="weekly_limit_completed_now"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            AnalysisRange(date(2026, 4, 20), date(2026, 5, 5)), datetime(2026, 5, 14, 18, 12, 30),
            HabitAnalysisResult(3, 3, 0.0, True),
            id="weekly_limit_streak_past"),
        pytest.param(
            make_mock_habit(periodicity=Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16), completions=(
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 4, 30, 14, 56, 23),
            )),
            AnalysisRange(date(2026, 4, 24), date(2026, 5, 7)), datetime(2026, 5, 14, 18, 12, 30),
            # The last week of the period lacks completions and, since it is in the past, should be
            # interpreted as a failure, and thus there also should not be any ongoing streak at the end.
            HabitAnalysisResult(0, 2, 1.0 / 3.0, True),
            id="weekly_limit_streak_broken_past_last_period"),
    ])
    def test_analyse_one(self, habit: Habit, analysis_range: AnalysisRange, now: datetime,
                         expected_result: HabitAnalysisResult) -> None:
        """
        Tests the analyse_one analytics function.

        :param habit: Habit.
        :param analysis_range: Analysis range.
        :param now: Current date and time.
        :param expected_result: Expected analysis result.
        :return: Nothing.
        """
        analysis = analyse_one(habit, analysis_range, now)

        assert analysis.streak == expected_result.streak
        assert analysis.longest_streak == expected_result.longest_streak
        # Use approximate comparison due to possible small rounding errors in floats
        assert analysis.failure_rate == pytest.approx(expected_result.failure_rate)
        assert analysis.pending == expected_result.pending

    @pytest.mark.parametrize(["habits", "analyser", "filters", "order", "expected_ids_ordered"], [
        pytest.param([], make_mock_analyse_one(), [], NEUTRAL_ORDER, [], id="no_habits"),
        pytest.param([
            make_mock_habit(id=1),
            make_mock_habit(id=2),
        ], make_mock_analyse_one(), [HabitAnalysisFilter(lambda _analysis: False)], NEUTRAL_ORDER, [],
            id="filter_to_no_habits"),
        pytest.param([
            make_mock_habit(id=1, periodicity=Periodicity.DAILY),
            make_mock_habit(id=2, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=3, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=4, periodicity=Periodicity.DAILY),
            make_mock_habit(id=5, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=6, periodicity=Periodicity.DAILY),
        ], make_mock_analyse_one(),
            [HabitAnalysisFilter(lambda analysis: analysis.habit.id % 2 == 0),
             HabitAnalysisFilter.by_periodicity(Periodicity.DAILY)],
            NEUTRAL_ORDER, [4, 6],
            id="two_filters_one_custom"),
        pytest.param([
            make_mock_habit(id=3),
            make_mock_habit(id=1),
            make_mock_habit(id=4),
            make_mock_habit(id=2),
        ], make_mock_analyse_one(),
            [], HabitAnalysisOrder(lambda analysis: analysis.habit.id, True), [1, 2, 3, 4],
            id="order_id"),
        # Ensure that when an order produces ties, they are broken using creation date and time.
        pytest.param([
            make_mock_habit(id=1, created_at=datetime(2026, 4, 18, 13, 30, 16)),
            make_mock_habit(id=2, created_at=datetime(2026, 4, 19, 13, 30, 16)),
            make_mock_habit(id=3, created_at=datetime(2026, 4, 17, 13, 30, 16)),
        ], make_mock_analyse_one(), [], NEUTRAL_ORDER, [3, 1, 2],
            id="order_neutral"),
        pytest.param([
            make_mock_habit(id=1, name="Write in journal", periodicity=Periodicity.DAILY),
            make_mock_habit(id=2, name="Go to gym", periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=3, name="Buy groceries", periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=4, name="Write code", periodicity=Periodicity.DAILY),
            make_mock_habit(id=5, name="Write weekly goals", periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=6, name="Stretch", periodicity=Periodicity.DAILY),
        ], make_mock_analyse_one({
            1: make_mock_analysis_result(failure_rate=0.4),
            2: make_mock_analysis_result(failure_rate=0.6),
            3: make_mock_analysis_result(failure_rate=0.86),
            4: make_mock_analysis_result(failure_rate=0.64),
            5: make_mock_analysis_result(failure_rate=0.2),
            6: make_mock_analysis_result(failure_rate=0.7),
        }),
            [HabitAnalysisFilter.by_search_match("wrIt"),
             HabitAnalysisFilter.by_periodicity(Periodicity.DAILY)],
            HabitAnalysisOrder.by_failure_rate(False), [4, 1],
            id="two_filters_order_failure_rate_reversed"),
    ])
    def test_analyse_many(self, habits: list[Habit], analyser: Callable[[Habit, AnalysisRange, datetime], HabitAnalysis],
                          filters: list[HabitAnalysisFilter], order: HabitAnalysisOrder,
                          expected_ids_ordered: list[int]) -> None:
        """
        Tests the analyse_many analytics function.

        :param habits: List of habits.
        :param analyser: Function used to analyse one habit.
        :param filters: List of filters for analysed habits.
        :param order: Analysed habit order.
        :param expected_ids_ordered: Ordered list of IDs of habits expected to be included in the analysis result in that order.
        :return: Nothing.
        """
        spy_analyser = Mock(wraps=analyser)
        mock_range = AnalysisRange(date(2026, 4, 17), date(2026, 4, 22))
        mock_now = datetime(2026, 5, 14, 18, 12, 30)

        actual = analyse_many(habits, filters, order, mock_range, mock_now, spy_analyser)
        actual_ids_ordered = [analysis.habit.id for analysis in actual]

        # Check that the analyser was called correctly. Using any order since order of individual analyses does not matter.
        spy_analyser.assert_has_calls([call(habit, mock_range, mock_now) for habit in habits], any_order=True)
        # Check that the ordering of analyses (identity established by numeric IDs) matches the expected ordering.
        assert actual_ids_ordered == expected_ids_ordered

    @pytest.mark.parametrize(["habits", "analyser", "filters", "expected"], [
        pytest.param([], make_mock_analyse_one(), [], AggregateAnalysis(0, 0, 0, 0.0), id="no_habits"),
        pytest.param([
            make_mock_habit(id=1),
            make_mock_habit(id=2)
        ], make_mock_analyse_one(), [HabitAnalysisFilter(lambda _analysis: False)], AggregateAnalysis(0, 0, 0, 0.0),
            id="filter_to_no_habits"),
        pytest.param([
            make_mock_habit(id=1, periodicity=Periodicity.DAILY),
            make_mock_habit(id=2, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=3, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=4, periodicity=Periodicity.DAILY),
            make_mock_habit(id=5, periodicity=Periodicity.WEEKLY),
            make_mock_habit(id=6, periodicity=Periodicity.DAILY),
            make_mock_habit(id=7, periodicity=Periodicity.DAILY),
            make_mock_habit(id=8, periodicity=Periodicity.DAILY),
        ], make_mock_analyse_one({
            1: HabitAnalysisResult(1, 3, 0.3, True),
            2: HabitAnalysisResult(0, 5, 0.51, False),
            3: HabitAnalysisResult(7, 7, 0.56, True),
            4: HabitAnalysisResult(2, 3, 0.25, False),
            5: HabitAnalysisResult(0, 0, 0.35, True),
            6: HabitAnalysisResult(1, 4, 0.65, True),
            7: HabitAnalysisResult(2, 5, 0.2, False),
            8: HabitAnalysisResult(0, 0, 0.0, True),
        }),
            [HabitAnalysisFilter(lambda analysis: analysis.habit.id % 2 == 0),
             HabitAnalysisFilter.by_periodicity(Periodicity.DAILY)], AggregateAnalysis(3, 2, 4, 0.3),
            id="two_filters_one_custom"),
    ])
    def test_aggregate(self, habits: list[Habit], analyser: Callable[[Habit, AnalysisRange, datetime], HabitAnalysis],
                       filters: list[HabitAnalysisFilter], expected: AggregateAnalysis):
        spy_analyser = Mock(wraps=analyser)
        mock_range = AnalysisRange(date(2026, 4, 17), date(2026, 4, 22))
        mock_now = datetime(2026, 5, 14, 18, 12, 30)

        actual = aggregate(habits, filters, mock_range, mock_now, spy_analyser)

        # Check that the analyser was called correctly. Using any order since order of individual analyses does not matter.
        spy_analyser.assert_has_calls([call(habit, mock_range, mock_now) for habit in habits], any_order=True)
        # Check result validity.
        assert actual == expected
