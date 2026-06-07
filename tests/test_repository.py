from collections.abc import Sequence
from datetime import datetime
from unittest.mock import Mock

import pytest

from habitline.repository import HabitRepository, Periodicity, HabitNameTakenException, HabitIdentifier, \
    HabitNotFoundException, Habit
from tests.conftest import MOCK_NOW


def check_identifier_filter(query: str, identifier: HabitIdentifier):
    """
    Asserts that the query string includes the correct habit lookup WHERE filter for the specified identifier.

    :param query: SQL query string.
    :param identifier: Habit identifier.
    :return: Nothing.
    """
    if type(identifier) == int:
        assert "WHERE id = ?" in query
    else:
        assert "WHERE name = ?" in query


def check_identifier_lookup(query: str, parameters: tuple[any, ...], identifier: HabitIdentifier):
    """
    Asserts that the query string and the query parameters are correct for looking up a habit with the given identifier.
    This includes the query being a habit SELECT query, the query containing the correct WHERE filter, and the
    query parameters providing the identifier's value.

    :param query: SQL query string.
    :param parameters: Tuple of query parameters.
    :param identifier: Habit identifier.
    :return: Nothing.
    """
    assert query.startswith("SELECT id FROM habit")
    check_identifier_filter(query, identifier)
    assert parameters == (identifier,)


def check_identifier_lookup_call(args: Sequence[str, tuple], identifier: HabitIdentifier):
    """
    Asserts that the call arguments for query execution (SQL query string and query parameters) are correct for looking
    up a habit with the given identifier. This includes the query being a habit SELECT query, the query containing the
    correct WHERE filter, and the query parameters providing the identifier's value.

    :param args: Tuple of call arguments (SQL string and query parameters).
    :param identifier: Habit identifier.
    :return: Nothing.
    """

    query, parameters = args
    check_identifier_lookup(query, parameters, identifier)


# Order of columns: ID, name, periodicity (as an integer), created_at (as an integer), completed_at (as an integer).
# The completed_at column belongs to the joined completion, the rest belong to the habit.
SelectHabitRow = tuple[int, str, int, int, int | None]


def make_select_habit_row(id: int, name: str, periodicity: Periodicity, created_at: datetime,
                          completed_at: datetime | None) -> SelectHabitRow:
    """
    Creates a joined habit SELECT result row based on the given parameters.

    :param id: Habit ID.
    :param name: Habit name.
    :param periodicity: Habit periodicity.
    :param created_at: Habit creation date.
    :param completed_at: Habit completion date and time, or None.
    :return: Habit SELECT result row.
    """
    return id, name, HabitRepository.periodicity_to_stored(periodicity), HabitRepository.datetime_to_stored(
        created_at), HabitRepository.datetime_to_stored(completed_at) if completed_at is not None else None


def check_select_habit_query_text(query: str):
    """
    Asserts that the habit SELECT query string contains correct elements.

    :param query: Query string.
    :return: Nothing.
    """
    assert "SELECT" in query
    assert "FROM habit" in query
    assert "LEFT JOIN completion" in query


def make_select_habit_rows(id: int, name: str, periodicity: Periodicity, created_at: datetime,
                           completions: list[datetime]):
    """
    Creates joined habit SELECT result rows based on the given parameters.
    The result always has at least one row even if there are no completions, same as SQL's LEFT JOIN behaviour.

    :param id: Habit ID, repeated in all rows.
    :param name: Habit name, repeated in all rows.
    :param periodicity: Habit periodicity, repeated in all rows.
    :param created_at: Habit creation date and time, repeated in all rows.
    :param completions: Habit completions, each corresponds to one row.
    :return: Habit SELECT result rows.
    """
    # Same as SQL LEFT JOIN behaviour, return one row if there are no completions.
    if not completions:
        return [make_select_habit_row(id, name, periodicity, created_at, None)]
    return [make_select_habit_row(id, name, periodicity, created_at, completed_at) for completed_at in completions]


class TestHabitRepository:
    """
    Tests HabitRepository with unit tests.
    """

    def test_create_failure_name_taken(self, mock_connection: Mock):
        """
        Tests HabitRepository.create failure outcome when the provided name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.return_value = (1,)
        name = "Journal"
        periodicity = Periodicity.DAILY
        created_at = datetime(2026, 5, 14, 13, 30, 16)
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNameTakenException):
            repository.create(name, periodicity, created_at)

        mock_connection.execute.assert_called_once()
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, name)

    @pytest.mark.parametrize(["periodicity"], [
        pytest.param(Periodicity.DAILY, id="daily"),
        pytest.param(Periodicity.WEEKLY, id="weekly"),
    ])
    def test_create_success(self, mock_connection: Mock, periodicity: Periodicity):
        """
        Tests HabitRepository.create success outcome.

        :param mock_connection: Mock database connection.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.return_value = None
        name = "Journal"
        created_at = datetime(2026, 5, 14, 13, 30, 16)
        repository = HabitRepository(mock_connection)

        repository.create(name, periodicity, created_at)

        assert len(mock_connection.execute.mock_calls) == 2
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, name)
        insert_query, insert_parameters = mock_connection.execute.mock_calls[1].args
        assert "INSERT INTO habit" in insert_query
        assert "VALUES (?, ?, ?)" in insert_query
        assert set(insert_parameters) == {name, HabitRepository.periodicity_to_stored(periodicity),
                                          HabitRepository.datetime_to_stored(created_at)}

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_update_failure_habit_not_found(self, mock_connection: Mock, identifier: HabitIdentifier):
        """
        Tests HabitRepository.update failure outcome when trying to change the name of a non-existent habit.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.return_value = None
        name = "Journal"
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNotFoundException):
            repository.update(identifier, name)

        mock_connection.execute.assert_called_once()
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)

    @pytest.mark.parametrize(["identifier", "own_id"], [
        pytest.param(1, 1, id="identifier_id"),
        pytest.param("Journal", 1, id="identifier_name"),
    ])
    def test_update_failure_name_taken(self, mock_connection: Mock, identifier: HabitIdentifier, own_id: int):
        """
        Tests HabitRepository.update failure outcome when the provided new name is already assigned to another habit.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param own_id: Habit ID.
        :return: Nothing.
        """
        other_id = own_id + 1
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.side_effect = [(own_id,), (other_id,)]
        name = "Take a walk"
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNameTakenException):
            repository.update(identifier, name)

        assert len(mock_connection.execute.mock_calls) == 2
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)
        check_identifier_lookup_call(mock_connection.execute.mock_calls[1].args, name)

    @pytest.mark.parametrize(["identifier", "own_id"], [
        pytest.param(1, 1, id="identifier_id"),
        pytest.param("Journal", 1, id="identifier_name"),
    ])
    def test_update_success(self, mock_connection: Mock, identifier: HabitIdentifier, own_id: int):
        """
        Tests HabitRepository.update success outcome.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param own_id: Habit ID.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.side_effect = [(own_id,), None]
        name = "Take a walk"
        repository = HabitRepository(mock_connection)

        repository.update(identifier, name)

        assert len(mock_connection.execute.mock_calls) == 3
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)
        check_identifier_lookup_call(mock_connection.execute.mock_calls[1].args, name)
        update_query, update_parameters = mock_connection.execute.mock_calls[2].args
        assert "UPDATE habit SET" in update_query
        assert "SET name = ?" in update_query
        check_identifier_filter(update_query, identifier)
        assert set(update_parameters) == {name, identifier}

    @pytest.mark.parametrize(["identifier", "own_id"], [
        pytest.param(1, 1, id="identifier_id"),
        pytest.param("Journal", 1, id="identifier_name"),
    ])
    def test_update_success_name_unchanged(self, mock_connection: Mock, identifier: HabitIdentifier, own_id: int):
        """
        Tests HabitRepository.update success outcome when trying to change the name to the same value.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param own_id: Habit ID.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.side_effect = [(own_id,), (own_id,)]
        name = "Journal"
        repository = HabitRepository(mock_connection)

        repository.update(identifier, name)

        assert len(mock_connection.execute.mock_calls) == 2
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)
        check_identifier_lookup_call(mock_connection.execute.mock_calls[1].args, name)
        # There should not be any updates because changing the name to the same value is a no-op and does not need to
        # access the database

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_delete_failure_habit_not_found(self, mock_connection: Mock, identifier: HabitIdentifier):
        """
        Tests HabitRepository.delete failure outcome when trying to delete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.return_value = None
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNotFoundException):
            repository.delete(identifier)

        mock_connection.execute.assert_called_once()
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)

    @pytest.mark.parametrize(["identifier", "own_id"], [
        pytest.param(1, 1, id="identifier_id"),
        pytest.param("Journal", 1, id="identifier_name"),
    ])
    def test_delete_success(self, mock_connection: Mock, identifier: HabitIdentifier, own_id: int):
        """
        Tests HabitRepository.delete success outcome.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param own_id: Habit ID.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.side_effect = [(own_id,)]
        repository = HabitRepository(mock_connection)

        repository.delete(identifier)

        assert len(mock_connection.execute.mock_calls) == 2
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)
        delete_query, delete_parameters = mock_connection.execute.mock_calls[1].args
        assert "DELETE FROM habit" in delete_query
        check_identifier_filter(delete_query, identifier)
        assert delete_parameters == (identifier,)

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_failure_habit_not_found(self, mock_connection: Mock, identifier: HabitIdentifier):
        """
        Tests HabitRepository.complete failure outcome when trying to complete a non-existent habit.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.return_value = None
        completed_at = MOCK_NOW
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNotFoundException):
            repository.complete(identifier, completed_at)

        mock_connection.execute.assert_called_once()
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)

    @pytest.mark.parametrize(["identifier", "own_id"], [
        pytest.param(1, 1, id="identifier_id"),
        pytest.param("Journal", 1, id="identifier_name"),
    ])
    def test_complete_success(self, mock_connection: Mock, identifier: HabitIdentifier, own_id: int):
        """
        Tests HabitRepository.complete success outcome.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param own_id: Habit ID.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchone.side_effect = [(own_id,)]
        completed_at = datetime(2026, 5, 14, 18, 12, 30)
        repository = HabitRepository(mock_connection)

        repository.complete(identifier, completed_at)

        assert len(mock_connection.execute.mock_calls) == 2
        check_identifier_lookup_call(mock_connection.execute.mock_calls[0].args, identifier)
        insert_query, insert_parameters = mock_connection.execute.mock_calls[1].args
        assert "INSERT INTO completion" in insert_query
        assert "VALUES (?, ?)" in insert_query
        assert set(insert_parameters) == {own_id, HabitRepository.datetime_to_stored(completed_at)}

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_read_one_failure_habit_not_found(self, mock_connection: Mock, identifier: HabitIdentifier):
        """
        Tests HabitRepository.read_one failure outcome when trying to read a non-existent habit.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchall.return_value = []
        repository = HabitRepository(mock_connection)

        with pytest.raises(HabitNotFoundException):
            repository.read_one(identifier)

        mock_connection.execute.assert_called_once()
        select_query, select_parameters = mock_connection.execute.mock_calls[0].args
        check_identifier_filter(select_query, identifier)
        assert set(select_parameters) == {identifier}

    @pytest.mark.parametrize(["identifier", "rows", "expected_habit"], [
        pytest.param(1, make_select_habit_rows(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), []),
                     Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), ()),
                     id="identifier_id_no_completions"),
        pytest.param("Journal",
                     make_select_habit_rows(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), [
                         datetime(2026, 5, 11, 12, 15, 40),
                         datetime(2026, 5, 12, 14, 56, 23),
                         datetime(2026, 5, 13, 13, 42, 21),
                     ]),
                     Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
                             datetime(2026, 5, 11, 12, 15, 40),
                             datetime(2026, 5, 12, 14, 56, 23),
                             datetime(2026, 5, 13, 13, 42, 21),
                     )),
                     id="identifier_name_completions"),
    ])
    def test_read_one_success(self, mock_connection: Mock, identifier: HabitIdentifier,
                              rows: list[SelectHabitRow], expected_habit: Habit):
        """
        Tests HabitRepository.read_one success outcome.

        :param mock_connection: Mock database connection.
        :param identifier: Habit identifier.
        :param rows: Mock habit SELECT rows.
        :param expected_habit: Expected parsed habit.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchall.return_value = rows
        repository = HabitRepository(mock_connection)

        actual_habit = repository.read_one(identifier)

        mock_connection.execute.assert_called_once()
        select_query, select_parameters = mock_connection.execute.mock_calls[0].args
        check_select_habit_query_text(select_query)
        check_identifier_filter(select_query, identifier)
        assert set(select_parameters) == {identifier}
        assert actual_habit == expected_habit

    @pytest.mark.parametrize(["rows", "expected_habits"], [
        pytest.param([], [], id="no_habits"),
        pytest.param(make_select_habit_rows(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), []), [
            Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), ()),
        ], id="one_habit_no_completions"),
        pytest.param(make_select_habit_rows(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), [
            datetime(2026, 5, 11, 12, 15, 40),
            datetime(2026, 5, 12, 14, 56, 23),
            datetime(2026, 5, 13, 13, 42, 21),
        ]), [
                         Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
                                 datetime(2026, 5, 11, 12, 15, 40),
                                 datetime(2026, 5, 12, 14, 56, 23),
                                 datetime(2026, 5, 13, 13, 42, 21),
                         )),
                     ], id="one_habit_completions"),
        pytest.param([
            *make_select_habit_rows(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), [
                datetime(2026, 5, 11, 12, 15, 40),
                datetime(2026, 5, 12, 14, 56, 23),
                datetime(2026, 5, 13, 13, 42, 21),
            ]),
            *make_select_habit_rows(2, "Call grandparents", Periodicity.WEEKLY, datetime(2026, 4, 17, 13, 30, 16), [
                datetime(2026, 4, 22, 12, 15, 40),
                datetime(2026, 5, 6, 13, 42, 21),
            ]),
            *make_select_habit_rows(3, "Go to gym", Periodicity.WEEKLY, datetime(2026, 4, 17, 14, 49, 21), [])
        ], [
            Habit(1, "Journal", Periodicity.DAILY, datetime(2026, 5, 10, 13, 30, 16), (
                    datetime(2026, 5, 11, 12, 15, 40),
                    datetime(2026, 5, 12, 14, 56, 23),
                    datetime(2026, 5, 13, 13, 42, 21),
            )),
            Habit(2, "Call grandparents", Periodicity.WEEKLY, datetime(2026, 4, 17, 13, 30, 16), (
                    datetime(2026, 4, 22, 12, 15, 40),
                    datetime(2026, 5, 6, 13, 42, 21),
            )),
            Habit(3, "Go to gym", Periodicity.WEEKLY, datetime(2026, 4, 17, 14, 49, 21), ()),
        ], id="three_habits"),
    ])
    def test_read_all(self, mock_connection: Mock, rows: list[SelectHabitRow], expected_habits: list[Habit]):
        """
        Tests HabitRepository.read_all.

        :param mock_connection: Mock database connection.
        :param rows: Mock habit SELECT rows.
        :param expected_habits: Expected parsed habits.
        :return: Nothing.
        """
        mock_cursor = mock_connection.cursor()
        mock_cursor.fetchall.return_value = rows
        repository = HabitRepository(mock_connection)

        actual_habits = repository.read_all()

        mock_connection.execute.assert_called_once()
        select_query, = mock_connection.execute.mock_calls[0].args
        check_select_habit_query_text(select_query)
        assert actual_habits == expected_habits
