import pytest

from habitline.util import maybe_pluralise


class TestUtil:
    @pytest.mark.parametrize(["word", "count", "expected"], [
        pytest.param("habit", 1, "habit", id="one_habit"),
        pytest.param("habit", 0, "habits", id="zero_habits"),
        pytest.param("day", 15, "days", id="fifteen_days"),
        pytest.param("week", 1, "week", id="one_week"),
    ])
    def test_maybe_pluralise(self, word: str, count: int, expected: str):
        """
        Tests the maybe_pluralise function.

        :param word: Input word.
        :param count: Input count.
        :param expected: Expected output.
        :return: Nothing.
        """
        result = maybe_pluralise(word, count)

        assert result == expected