from datetime import datetime, date
from unittest.mock import Mock, call

import pytest
from click import BadParameter
from click.testing import CliRunner
from pytest_mock import MockerFixture

from habitline.analytics import HabitAnalysis, AnalysisRange, AggregateAnalysis
from habitline.cli import cli, represent_habit, parse_identifier_input, OrderOption, CLI_OUTPUT_SEPARATOR, \
    represent_aggregate_analysis, DEFAULT_DB_PATH
from habitline.repository import Periodicity, HabitNameTakenException, HabitIdentifier, HabitNotFoundException, Habit
from habitline.util import maybe_pluralise
from tests.conftest import make_mock_analysis, MOCK_NOW


@pytest.fixture()
def runner():
    """
    Creates a CLI runner for testing CLI commands.

    :return: CLI Runner.
    """
    return CliRunner()


@pytest.fixture()
def patched_get_connection(mocker: MockerFixture, mock_connection):
    """
    Patches the get_connection function to return the mock connection.

    :param mocker: Mocker fixture.
    :param mock_connection: Mock database connection.
    :return: Patched get_connection function.
    """
    return mocker.patch("habitline.cli.get_connection", return_value=mock_connection)


@pytest.fixture()
def patched_create_service(mocker: MockerFixture, mock_service: Mock):
    """
    Patches the HabitService class to create the mock service object.

    :param mocker: Mocker fixture.
    :param mock_service: Mock habit service.
    :return: Mock class.
    """
    return mocker.patch("habitline.cli.HabitService", return_value=mock_service)


def make_args(path: str | None = None, base: str | None = None, identifier: HabitIdentifier | None = None,
              args: str = "", periodicity_filter: Periodicity | None = None, name_filter: str | None = None,
              pending_filter: bool | None = None, order: OrderOption | None = None, asc: bool | None = None,
              analysis_range: AnalysisRange | None = None, show_completions: bool = False):
    """
    Makes arguments for the application command call based on parameters. Any parameter that is not specified will not
    be included in the command.

    :param path: Database path (--path option of the root group).
    :param base: Base command (e.g., list).
    :param identifier: Habit identifier (argument and --use-id flag if it is an integer).
    :param args: Freeform arguments.
    :param periodicity_filter: Periodicity filter (--periodicity option).
    :param name_filter: Name search string filter (--search option).
    :param pending_filter: Pending filter (--pending/--completed flag).
    :param order: Order filter (--sort option).
    :param asc: Whether the order is ascending (--asc/--desc flag).
    :param analysis_range: Analysis range (--analyse-from and --analyse-until options).
    :param show_completions: Whether to show completions (--show-completions flag).
    :return: Corresponding command.
    """
    command_elements: list[str] = []
    if path is not None:
        command_elements.append(f'--path "{path}"')
    if base:
        command_elements.append(base)
    if identifier is not None:
        command_elements.append((str(identifier) + " --use-id") if type(identifier) is int else f'"{identifier}"')
    if args:
        command_elements.append(args)
    if periodicity_filter is not None:
        command_elements.append(f"--periodicity {periodicity_filter.name}")
    if name_filter is not None:
        command_elements.append(f'--search "{name_filter}"')
    if pending_filter is not None:
        command_elements.append("--pending" if pending_filter else "--completed")
    if order is not None:
        command_elements.append(f"--sort {order.name}")
    if asc is not None:
        command_elements.append("--asc" if asc else "--desc")
    if analysis_range is not None:
        if analysis_range.start:
            command_elements.append(f"--analyse-from {analysis_range.start}")
        if analysis_range.end:
            command_elements.append(f"--analyse-until {analysis_range.end}")
    if show_completions:
        command_elements.append(f"--show-completions")
    return " ".join(command_elements)


@pytest.fixture()
def spied_parse_identifier_input(mocker: MockerFixture):
    """
    Patches the parse_identifier_input function with a mock that behaves exactly the same but allows to spy on its
    calls.

    :param mocker: Mocker fixture.
    :return: Spied function.
    """
    return mocker.patch("habitline.cli.parse_identifier_input", side_effect=parse_identifier_input)


@pytest.fixture()
def patched_represent_habit(mocker: MockerFixture):
    """
    Patches the represent_habit function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched represent_habit function.
    """
    return mocker.patch("habitline.cli.represent_habit")


@pytest.fixture()
def patched_habit_analysis_filter(mocker: MockerFixture):
    """
    Patches the HabitAnalysisFilter class with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched HabitAnalysisFilter class.
    """
    return mocker.patch("habitline.cli.HabitAnalysisFilter")


def prepare_filter_expects(patched_habit_analysis_filter: Mock, periodicity_filter: Periodicity | None,
                           name_filter: str | None, pending_filter: bool | None):
    """
    Prepares a list of expected filter creation function calls and expected filters that should be obtained by calling
    all the required filter creation functions. Also configures the mock functions on  the provided HabitAnalysisFilter
    mock to return the statically expected outputs (correctness of inputs is to be verified via calls). The outputs are
    mocks that just mirror the filter parameter.

    :param patched_habit_analysis_filter: Patched HabitAnalysisFilter class.
    :param periodicity_filter: Periodicity to filter with, or None if should not filter.
    :param name_filter: Name search string to filter with, or None if should not filter.
    :param pending_filter: Pending value to filter with, or None if should not filter.
    :return: Tuple of a list of expected filter calls (which themselves are tuple of the mock function and expected argument) and a set of expected filters.
    """
    expected_filter_calls: list[tuple[Mock, any]] = []
    expected_filters = set()
    if periodicity_filter is not None:
        expected_filter_calls.append((patched_habit_analysis_filter.by_periodicity, periodicity_filter))
        patched_habit_analysis_filter.by_periodicity.return_value = periodicity_filter
        expected_filters.add(periodicity_filter)
    if name_filter is not None:
        expected_filter_calls.append((patched_habit_analysis_filter.by_search_match, name_filter))
        patched_habit_analysis_filter.by_search_match.return_value = name_filter
        expected_filters.add(name_filter)
    if pending_filter is not None:
        expected_filter_calls.append((patched_habit_analysis_filter.by_pending, pending_filter))
        patched_habit_analysis_filter.by_pending.return_value = pending_filter
        expected_filters.add(pending_filter)
    return expected_filter_calls, expected_filters


def prepare_order_expects(patched_habit_analysis_order: Mock, order_option: OrderOption | None, asc: bool | None):
    """

    Prepares the expected order call and expected order that should be obtained by calling the required order creation
    function. Also configures the mock function on the provided HabitAnalysisOrder mock to return the statically
    outputs (correctness of input is to be verified via the call). The output is a mock that is a tuple with the sort
    type (via OrderOption) and ascending flag value.

    :param patched_habit_analysis_order: Patched HabitAnalysisOrder class.
    :param order_option: Order option to use, or None if should use default
    :param asc: Whether to use ascending or descending order, or None if should use default.
    :return: Tuple of a list of expected order call (which itself is a tuple of the mock function and expected argument) and the expected order (which is a tuple of actual OrderOption and actual ascending flag value).
    """
    expected_order_option = order_option if order_option is not None else OrderOption.CREATED_AT
    expected_asc = asc if asc is not None else True
    expected_order_call: tuple[Mock, bool]
    expected_order: tuple[OrderOption, bool]
    match expected_order_option:
        case OrderOption.NAME:
            expected_order_call = (patched_habit_analysis_order.by_name, expected_asc)
            expected_order = OrderOption.NAME, asc
            patched_habit_analysis_order.by_name.return_value = expected_order
        case OrderOption.CREATED_AT:
            expected_order_call = (patched_habit_analysis_order.by_created_at, expected_asc)
            expected_order = OrderOption.CREATED_AT, asc
            patched_habit_analysis_order.by_created_at.return_value = expected_order
        case OrderOption.STREAK:
            expected_order_call = (patched_habit_analysis_order.by_streak, expected_asc)
            expected_order = OrderOption.STREAK, asc
            patched_habit_analysis_order.by_streak.return_value = expected_order
        case OrderOption.LONGEST_STREAK:
            expected_order_call = (patched_habit_analysis_order.by_longest_streak, expected_asc)
            expected_order = OrderOption.LONGEST_STREAK, asc
            patched_habit_analysis_order.by_longest_streak.return_value = expected_order
        case OrderOption.FAILURE_RATE:
            expected_order_call = (patched_habit_analysis_order.by_failure_rate, expected_asc)
            expected_order = OrderOption.FAILURE_RATE, asc
            patched_habit_analysis_order.by_failure_rate.return_value = expected_order
        case _:
            raise NotImplementedError
    return expected_order_call, expected_order


@pytest.fixture()
def patched_habit_analysis_order(mocker: MockerFixture):
    """
    Patches the HabitAnalysisOrder class with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched HabitAnalysisFilter class.
    """
    return mocker.patch("habitline.cli.HabitAnalysisOrder")


@pytest.fixture()
def patched_represent_aggregate_analysis(mocker: MockerFixture):
    """
    Patches the represent_aggregate_analysis function with a mock and returns the mock.

    :param mocker: Mocker fixture.
    :return: Patched represent_aggregate_analysis function.
    """
    return mocker.patch("habitline.cli.represent_aggregate_analysis")


class TestCLI:
    """
    Tests the CLI layer with unit tests.
    """

    def test_cli_default_path(self, runner: CliRunner, mock_connection: Mock, patched_get_connection: Mock,
                              patched_create_service: Mock):
        """
        Tests the base command group that is responsible for obtaining the database connection, without providing a
        custom path.

        :param runner: CLI runner.
        :param mock_connection: Mock database connection.
        :param patched_get_connection: Patched get_connection function.
        :param patched_create_service: Patched habit service class.
        :return: Nothing.
        """
        expected_path = DEFAULT_DB_PATH

        # Have to invoke a subcommand because invoking the main group (cli) without subcommands just skips the command
        # and prints help.
        runner.invoke(cli, make_args(base="list"))

        patched_get_connection.assert_called_once_with(expected_path)
        patched_create_service.assert_called_once_with(patched_get_connection.return_value)
        # Cleanup after command execution.
        mock_connection.close.assert_called_once()

    def test_cli_path_arg(self, runner: CliRunner, mock_connection: Mock, patched_get_connection: Mock,
                          patched_create_service: Mock):
        """
        Tests the base command group that is responsible for obtaining the database connection, with a custom path
        provided through command options.

        :param runner: CLI runner.
        :param mock_connection: Mock database connection.
        :param patched_get_connection: Patched get_connection function.
        :param patched_create_service: Patched habit service class.
        :return: Nothing.
        """
        path = "lorem_ipsum.db"

        runner.invoke(cli, make_args(path=path, base="list"))

        patched_get_connection.assert_called_once_with(path)
        patched_create_service.assert_called_once_with(patched_get_connection.return_value)
        mock_connection.close.assert_called_once()

    def test_cli_path_env(self, runner: CliRunner, mock_connection: Mock, patched_get_connection: Mock,
                          patched_create_service: Mock):
        """
        Tests the base command group that is responsible for obtaining the database connection, with a custom path
        provided through an environment variable.

        :param runner: CLI runner.
        :param mock_connection: Mock database connection.
        :param patched_get_connection: Patched get_connection function.
        :param patched_create_service: Patched habit service class.
        :return: Nothing.
        """
        path = "lorem_ipsum.db"

        runner.invoke(cli, make_args(base="list"), env={"HABITLINE_PATH": path})

        patched_get_connection.assert_called_once_with(path)
        patched_create_service.assert_called_once_with(patched_get_connection.return_value)
        mock_connection.close.assert_called_once()

    def test_create_failure_name_taken(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                       patched_create_service: Mock):
        """
        Tests the create command failure outcome when the provided name is already assigned to another habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY
        mock_service.create.side_effect = HabitNameTakenException(name)

        result = runner.invoke(cli, make_args(base="create", args='"Journal" daIlY'))

        mock_service.create.assert_called_once_with(name, periodicity)
        assert "taken" in result.output
        assert name in result.output

    def test_create_success(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                            patched_create_service: Mock):
        """
        Tests the create command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :return: Nothing.
        """
        name = "Journal"
        periodicity = Periodicity.DAILY

        result = runner.invoke(cli, make_args(base="create", args='"Journal" daIlY'))

        mock_service.create.assert_called_once_with(name, periodicity)
        assert "created successfully" in result.output

    def test_parse_identifier_input_failure_not_integer(self):
        """
        Tests the parse_identifier_input function failure outcome when the provided input is not an integer and it is
        meant to be interpreted as a numeric ID.

        :return: Nothing.
        """
        with pytest.raises(BadParameter) as exception:
            parse_identifier_input("Journal", True)

        assert "Journal" in exception.value.message
        assert "not an integer" in exception.value.message

    @pytest.mark.parametrize(["identifier_input", "use_id"], [
        pytest.param("Journal", False, id="name_no_use_id"),
        pytest.param("1", True, id="number_use_id"),
        # The user may have a habit that is named with just an integer. If --use-id is not specified, the program
        # should still interpret a number string identifier argument as a name.
        pytest.param("1", False, id="number_no_use_id"),
    ])
    def test_parse_identifier_input_success(self, identifier_input: str, use_id: bool):
        """
        Tests the parse_identifier_input function success outcome.

        :param identifier_input: Identifier input string.
        :param use_id: Whether to interpret the input as a numeric ID.
        :return: Nothing.
        """
        expected_type = int if use_id else str

        result = parse_identifier_input(identifier_input, use_id)

        assert type(result) is expected_type

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_failure_habit_not_found(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                          patched_create_service: Mock, spied_parse_identifier_input: Mock,
                                          identifier: HabitIdentifier):
        """
        Tests the edit command failure outcome when trying to change the name of a non-existent habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"
        mock_service.edit.side_effect = HabitNotFoundException(identifier)

        result = runner.invoke(cli, make_args(base="edit", identifier=identifier, args=f'"{name}"'))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.edit.assert_called_once_with(identifier, name)
        assert "Could not find" in result.output
        assert str(identifier) in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_failure_name_taken(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                     patched_create_service: Mock, spied_parse_identifier_input: Mock,
                                     identifier: HabitIdentifier):
        """
        Tests the edit command failure outcome when the provided new name is already assigned to another habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"
        mock_service.edit.side_effect = HabitNameTakenException(name)

        result = runner.invoke(cli, make_args(base="edit", identifier=identifier, args=f'"{name}"'))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.edit.assert_called_once_with(identifier, name)
        assert "already taken" in result.output
        assert name in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_edit_success(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                          patched_create_service: Mock, spied_parse_identifier_input: Mock,
                          identifier: HabitIdentifier):
        """
        Tests the edit command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        name = "Take a walk"

        result = runner.invoke(cli, make_args(base="edit", identifier=identifier, args=f'"{name}"'))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.edit.assert_called_once_with(identifier, name)
        assert "edited successfully" in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_delete_failure_habit_not_found(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                            patched_create_service: Mock, spied_parse_identifier_input: Mock,
                                            identifier: HabitIdentifier):
        """
        Tests the delete command failure outcome when trying to delete a non-existent habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_service.delete.side_effect = HabitNotFoundException(identifier)

        result = runner.invoke(cli, make_args(base="delete", identifier=identifier))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.delete.assert_called_once_with(identifier)
        assert "Could not find" in result.output
        assert str(identifier) in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_delete_success(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                            patched_create_service: Mock, spied_parse_identifier_input: Mock,
                            identifier: HabitIdentifier):
        """
        Tests the delete command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        result = runner.invoke(cli, make_args(base="delete", identifier=identifier))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.delete.assert_called_once_with(identifier)
        assert "deleted successfully" in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_failure_habit_not_found(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                              patched_create_service: Mock, spied_parse_identifier_input: Mock,
                                              identifier: HabitIdentifier):
        """
        Tests the complete command failure outcome when trying to complete a non-existent habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        mock_service.complete.side_effect = HabitNotFoundException(identifier)

        result = runner.invoke(cli, make_args(base="complete", identifier=identifier))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.complete.assert_called_once_with(identifier)
        assert "Could not find" in result.output
        assert str(identifier) in result.output

    @pytest.mark.parametrize(["identifier"], [
        pytest.param(1, id="identifier_id"),
        pytest.param("Journal", id="identifier_name"),
    ])
    def test_complete_success(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                              patched_create_service: Mock, spied_parse_identifier_input: Mock,
                              identifier: HabitIdentifier):
        """
        Tests the complete command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param identifier: Habit identifier.
        :return: Nothing.
        """
        result = runner.invoke(cli, make_args(base="complete", identifier=identifier))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.complete.assert_called_once_with(identifier)
        assert "completion logged successfully" in result.output

    # The represent_habit function is tested separately to assure its validity and then mocked in habit-printing
    # commands in order to simplify their testing (transparently verifying correct data being passed to represent_habit
    # rather than opaquely verifying correct output to console).
    @pytest.mark.parametrize(["habit_analysis", "analysis_limited", "show_completions", "expected"], [
        pytest.param(HabitAnalysis(Habit(1, "Journal", Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16),
                                         completions=()), 0, 0, 1.0, True), False, False, "\n".join([
            "ID:\t\t1",
            "Name:\t\tJournal",
            "Periodicity:\tDaily",
            "Created at:\t2026-05-10 13:30:16",
            "Current streak:\t0 days",
            "Longest streak:\t0 days",
            "Failure rate:\t100.0%",
            "Pending:\tYes",
        ]), id="daily_no_completions"),
        pytest.param(HabitAnalysis(Habit(1, "Journal", Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16),
                                         completions=(
                                                 datetime(2026, 5, 12, 14, 56, 23),
                                         )), 0, 1, 0.75, True), False, True, "\n".join([
            "ID:\t\t1",
            "Name:\t\tJournal",
            "Periodicity:\tDaily",
            "Created at:\t2026-05-10 13:30:16",
            "Current streak:\t0 days",
            "Longest streak:\t1 day",
            "Failure rate:\t75.0%",
            "Pending:\tYes",
            "Completions:",
            "- 2026-05-12 14:56:23",
        ]), id="daily_one_completion_show_completions"),
        pytest.param(HabitAnalysis(Habit(1, "Journal", Periodicity.DAILY, created_at=datetime(2026, 5, 10, 13, 30, 16),
                                         completions=(
                                                 datetime(2026, 5, 11, 12, 15, 40),
                                                 datetime(2026, 5, 12, 14, 56, 23),
                                                 datetime(2026, 5, 13, 13, 42, 21),
                                                 datetime(2026, 5, 14, 16, 20, 49),
                                         )), 4, 4, 0.25, False), True, True, "\n".join([
            "ID:\t\t\t\t\t1",
            "Name:\t\t\t\t\tJournal",
            "Periodicity:\t\t\t\tDaily",
            "Created at:\t\t\t\t2026-05-10 13:30:16",
            "Current streak in target time range:\t4 days",
            "Longest streak in target time range:\t4 days",
            "Failure rate in target time range:\t25.0%",
            "Pending:\t\t\t\tNo",
            "All completions:",
            "- 2026-05-11 12:15:40",
            "- 2026-05-12 14:56:23",
            "- 2026-05-13 13:42:21",
            "- 2026-05-14 16:20:49",
        ]), id="daily_streak_completed_limited_show_completions"),
        pytest.param(HabitAnalysis(
            Habit(1, "Call grandparents", Periodicity.WEEKLY, created_at=datetime(2026, 5, 13, 13, 30, 16),
                  completions=()), 0, 0, 0.0, True), False, True, "\n".join([
            "ID:\t\t1",
            "Name:\t\tCall grandparents",
            "Periodicity:\tWeekly",
            "Created at:\t2026-05-13 13:30:16",
            "Current streak:\t0 weeks",
            "Longest streak:\t0 weeks",
            "Failure rate:\t0.0%",
            "Pending:\tYes",
            "No completions"
        ]), id="weekly_new"),
        pytest.param(HabitAnalysis(
            Habit(1, "Call grandparents", Periodicity.WEEKLY, created_at=datetime(2026, 4, 17, 13, 30, 16),
                  completions=(
                          datetime(2026, 4, 17, 16, 18, 9),
                          datetime(2026, 4, 22, 12, 15, 40),
                          datetime(2026, 5, 6, 13, 42, 21),
                  )), 1, 2, 1.0 / 3.0, True), True, False, "\n".join([
            "ID:\t\t\t\t\t1",
            "Name:\t\t\t\t\tCall grandparents",
            "Periodicity:\t\t\t\tWeekly",
            "Created at:\t\t\t\t2026-04-17 13:30:16",
            "Current streak in target time range:\t1 week",
            "Longest streak in target time range:\t2 weeks",
            "Failure rate in target time range:\t33.3%",
            "Pending:\t\t\t\tYes",
        ]), id="weekly_streak_one_limited"),
    ])
    def test_represent_habit(self, habit_analysis: HabitAnalysis, analysis_limited: bool, show_completions: bool,
                             expected: str):
        """
        Tests the represent_habit function.

        :param habit_analysis: Habit analysis to represent.
        :param analysis_limited: Whether the time range of the analysis is limited at least on one side.
        :param show_completions: Whether to show completions.
        :param expected: Expected representation given the parameters.
        :return: Nothing.
        """
        result = represent_habit(habit_analysis, analysis_limited, show_completions)

        assert result == expected

    @pytest.mark.parametrize(["identifier", "habit_analysis", "analysis_range"], [
        pytest.param(1, make_mock_analysis(id=1, name="Journal"), AnalysisRange(None, None), id="identifier_id"),
        pytest.param("Journal", make_mock_analysis(id=1, name="Journal"),
                     AnalysisRange(date(2026, 5, 11), date(2026, 5, 13)), id="identifier_name_limit"),
    ])
    def test_show_failure_habit_not_found(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                                          patched_create_service: Mock, spied_parse_identifier_input: Mock,
                                          patched_represent_habit: Mock, identifier: HabitIdentifier,
                                          habit_analysis: HabitAnalysis,
                                          analysis_range: AnalysisRange):
        """
        Tests the show command failure outcome when trying to show a non-existent habit.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param patched_represent_habit: Patched represent_habit function.
        :param identifier: Habit identifier.
        :param habit_analysis: Habit analysis the service should return.
        :param analysis_range: Habit analysis time range.
        :return: Nothing.
        """
        mock_service.get_one.side_effect = HabitNotFoundException(identifier)

        result = runner.invoke(cli, make_args(base="show", identifier=identifier, analysis_range=analysis_range))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.get_one.assert_called_once_with(identifier, analysis_range)
        assert "Could not find" in result.output
        assert str(identifier) in result.output

    @pytest.mark.parametrize(["identifier", "habit_analysis", "analysis_range", "show_completions"], [
        pytest.param(1, make_mock_analysis(id=1, name="Journal"), AnalysisRange(None, None), False,
                     id="identifier_id"),
        pytest.param("Journal", make_mock_analysis(id=1, name="Journal"), AnalysisRange(date(2026, 5, 11), None), True,
                     id="identifier_name_limit_start_show_completions"),
        pytest.param("Journal", make_mock_analysis(id=1, name="Journal"), AnalysisRange(None, date(2026, 5, 13)), False,
                     id="identifier_name_limit_end"),
        pytest.param(1, make_mock_analysis(id=1, name="Journal"), AnalysisRange(date(2026, 5, 11), date(2026, 5, 13)),
                     True,
                     id="identifier_id_limit_show_completions"),
    ])
    def test_show_success(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                          patched_create_service: Mock, spied_parse_identifier_input: Mock,
                          patched_represent_habit: Mock, identifier: HabitIdentifier, habit_analysis: HabitAnalysis,
                          analysis_range: AnalysisRange, show_completions: bool):
        """
        Tests the show command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param spied_parse_identifier_input: Spied parse_identifier_input function.
        :param patched_represent_habit: Patched represent_habit function.
        :param identifier: Habit identifier.
        :param habit_analysis: Habit analysis the service should return.
        :param analysis_range: Habit analysis time range.
        :param show_completions: Whether to show completions.
        :return: Nothing.
        """
        mock_service.get_one.return_value = habit_analysis
        range_specified = bool(analysis_range.start or analysis_range.end)
        patched_represent_habit.return_value = "Lorem ipsum"
        expected_output = "Lorem ipsum"

        result = runner.invoke(cli, make_args(base="show", identifier=identifier, analysis_range=analysis_range,
                                              show_completions=show_completions))

        spied_parse_identifier_input.assert_called_once_with(str(identifier), type(identifier) is int)
        mock_service.get_one.assert_called_once_with(identifier, analysis_range)
        patched_represent_habit.assert_called_once_with(habit_analysis, range_specified, show_completions)
        assert result.output == expected_output + "\n"

    @pytest.mark.parametrize(
        ["periodicity_filter", "name_filter", "pending_filter", "order_option", "asc", "analysis_range",
         "habit_analyses"], [
            pytest.param(None, None, None, None, None, AnalysisRange(None, None), [], id="no_results"),
            pytest.param(Periodicity.DAILY, None, None, None, False, AnalysisRange(date(2026, 5, 9), None), [
                make_mock_analysis(id=1, name="Journal", periodicity=Periodicity.DAILY),
            ], id="daily_desc_limit_start"),
            pytest.param(None, "", None, None, True, AnalysisRange(None, date(2026, 5, 13)), [
                make_mock_analysis(id=1, name="Call grandparents", periodicity=Periodicity.WEEKLY,
                                   created_at=datetime(2026, 4, 17, 16, 54, 40)),
                make_mock_analysis(id=2, name="Journal", periodicity=Periodicity.DAILY,
                                   created_at=datetime(2026, 5, 10, 13, 15, 25)),
            ], id="name_empty_asc_limit_end"),
            pytest.param(None, "write", None, OrderOption.NAME, None,
                         AnalysisRange(date(2026, 4, 17), date(2026, 5, 13)), [
                             make_mock_analysis(id=1, name="Write to grandparents", periodicity=Periodicity.WEEKLY,
                                                created_at=datetime(2026, 5, 10, 16, 54, 40)),
                             make_mock_analysis(id=2, name="Write in journal", periodicity=Periodicity.DAILY,
                                                created_at=datetime(2026, 4, 17, 13, 15, 25)),

                         ], id="name_order_name_limit"),
            pytest.param(None, None, True, OrderOption.STREAK, True, AnalysisRange(date(2026, 4, 17), None), [
                make_mock_analysis(id=1, name="Call grandparents", periodicity=Periodicity.WEEKLY, streak=2),
                make_mock_analysis(id=3, name="Journal", periodicity=Periodicity.DAILY, streak=5),
                make_mock_analysis(id=2, name="Go to gym", periodicity=Periodicity.WEEKLY, streak=6)
            ], id="pending_order_streak_asc_limit_start"),
            pytest.param(None, None, False, OrderOption.LONGEST_STREAK, False, AnalysisRange(None, date(2026, 5, 12)),
                         [
                             make_mock_analysis(id=1, name="Call grandparents", periodicity=Periodicity.WEEKLY,
                                                completions=(MOCK_NOW,), longest_streak=6),
                             make_mock_analysis(id=3, name="Journal", periodicity=Periodicity.DAILY,
                                                completions=(MOCK_NOW,), longest_streak=3),
                             make_mock_analysis(id=2, name="Go to gym", periodicity=Periodicity.WEEKLY,
                                                completions=(MOCK_NOW,), longest_streak=2),
                         ], id="completed_order_longest_streak_desc_limit_end"),
            pytest.param(Periodicity.WEEKLY, "go", True, OrderOption.FAILURE_RATE, None,
                         AnalysisRange(date(2026, 4, 22), date(2026, 5, 12)), [
                             make_mock_analysis(id=1, name="Go shopping for groceries", periodicity=Periodicity.WEEKLY,
                                                failure_rate=0.0),
                             make_mock_analysis(id=2, name="Go to gym", periodicity=Periodicity.WEEKLY,
                                                completions=(MOCK_NOW,), failure_rate=0.5),
                         ], id="weekly_name_pending_order_failure_rate_limit"),
            pytest.param(Periodicity.DAILY, "a", None, OrderOption.CREATED_AT, False, AnalysisRange(None, None),
                         [
                             make_mock_analysis(id=2, name="Journal", periodicity=Periodicity.DAILY,
                                                created_at=datetime(2026, 5, 10, 13, 15, 25)),
                             make_mock_analysis(id=1, name="Take a walk", periodicity=Periodicity.DAILY,
                                                created_at=datetime(2026, 4, 17, 16, 54, 40)),
                         ], id="daily_name_order_created_at_desc"),
        ])
    def test_list(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                  patched_create_service: Mock, patched_represent_habit: Mock, patched_habit_analysis_filter: Mock,
                  patched_habit_analysis_order: Mock, periodicity_filter: Periodicity | None,
                  name_filter: str | None, pending_filter: bool | None, order_option: OrderOption | None,
                  asc: bool | None,
                  analysis_range: AnalysisRange, habit_analyses: list[HabitAnalysis]):
        """
        Tests the show command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param patched_represent_habit: Patched represent_habit function.
        :param patched_habit_analysis_filter: Patched HabitAnalysisFilter class.
        :param patched_habit_analysis_order: Patched HabitAnalysisOrder class.
        :param periodicity_filter: Periodicity to filter with, or None if should not filter.
        :param name_filter: Name search string to filter with, or None if should not filter.
        :param pending_filter: Pending value to filter with, or None if should not filter.
        :param order_option: Order option value, or None if should not be specified.
        :param asc: Whether the order should be ascending, or None if should not be specified.
        :param analysis_range: Habit analysis time range.
        :param habit_analyses: Habit analyses list the service should return.
        :return: Nothing.
        """
        mock_service.get_many.return_value = habit_analyses
        range_specified = bool(analysis_range.start or analysis_range.end)
        expected_filter_calls, expected_filters = prepare_filter_expects(patched_habit_analysis_filter,
                                                                         periodicity_filter, name_filter,
                                                                         pending_filter)
        expected_order_call, expected_order = prepare_order_expects(patched_habit_analysis_order, order_option, asc)
        fake_represent_habit = lambda analysis, _analysis_limited: repr(analysis)
        patched_represent_habit.side_effect = fake_represent_habit
        expected_represent_habit_calls = [call(habit_analysis, range_specified) for habit_analysis in
                                          habit_analyses]
        expected_output = "Found 0 habits" if len(habit_analyses) == 0 else ("\n" + CLI_OUTPUT_SEPARATOR + "\n").join([
            # Heading.
            f"Found {len(habit_analyses)} {maybe_pluralise('habit', len(habit_analyses))}:",
            # One item for every returned habit, in order.
            *[fake_represent_habit(habit_analysis, False) for habit_analysis in habit_analyses]
        ])

        result = runner.invoke(cli,
                               make_args(base="list", periodicity_filter=periodicity_filter, name_filter=name_filter,
                                         pending_filter=pending_filter, order=order_option, asc=asc,
                                         analysis_range=analysis_range))

        for expected_filter_call in expected_filter_calls:
            expected_filter_call[0].assert_called_once_with(expected_filter_call[1])
        expected_order_call[0].assert_called_once_with(expected_order_call[1])
        mock_service.get_many.assert_called_once()
        assert set(mock_service.get_many.call_args[0][0]) == expected_filters
        assert mock_service.get_many.call_args[0][1] == expected_order
        assert mock_service.get_many.call_args[0][2] == analysis_range
        patched_represent_habit.assert_has_calls(expected_represent_habit_calls, any_order=True)
        assert result.output == expected_output + "\n"

    @pytest.mark.parametrize(["aggregate_analysis", "analysis_limited", "expected"], [
        pytest.param(AggregateAnalysis(0, 0, 0, 0.0), False, "\n".join([
            "Analysed habits:\t\t0",
            "Current longest streak:\t\t0 periods",
            "Longest logged streak:\t\t0 periods",
            "Average failure rate:\t\t0.0%",
        ]), id="no_habits"),
        pytest.param(AggregateAnalysis(5, 1, 3, 6.0 / 7.0), True, "\n".join([
            "Analysed habits:\t\t\t\t\t5",
            "Current longest streak in target time range:\t\t1 period",
            "Longest logged streak in target time range:\t\t3 periods",
            "Average failure rate in target time range:\t\t85.7%",
        ]), id="limit")
    ])
    def test_represent_aggregate_analysis(self, aggregate_analysis: AggregateAnalysis, analysis_limited: bool,
                                          expected: str):
        """
        Tests the represent_aggregate_analysis function.

        :param aggregate_analysis: Aggregate analysis.
        :param analysis_limited: Whether the time range of the analysis is limited at least on one side.
        :param expected: Expected representation given the parameters.
        :return: Nothing.
        """
        result = represent_aggregate_analysis(aggregate_analysis, analysis_limited)

        assert result == expected

    @pytest.mark.parametrize(
        ["periodicity_filter", "name_filter", "pending_filter", "analysis_range", "aggregate_analysis"], [
            pytest.param(None, None, None, AnalysisRange(None, None), AggregateAnalysis(0, 0, 0, 0.0), id="no_results"),
            pytest.param(Periodicity.DAILY, None, None, AnalysisRange(date(2026, 5, 9), None),
                         AggregateAnalysis(3, 1, 5, 6.0 / 7.0), id="daily_limit_start"),
            pytest.param(None, "", None, AnalysisRange(None, date(2026, 5, 13)), AggregateAnalysis(5, 4, 4, 0.0),
                         id="name_empty_limit_end"),
            pytest.param(None, "journal", None, AnalysisRange(date(2026, 5, 10), date(2026, 5, 13)),
                         AggregateAnalysis(0, 0, 0, 0.0), id="name_limit_no_results"),
            pytest.param(None, None, True, AnalysisRange(None, None), AggregateAnalysis(4, 2, 6, 5.0 / 6.0),
                         id="pending"),
            pytest.param(None, None, False, AnalysisRange(date(2026, 4, 17), None),
                         AggregateAnalysis(7, 20, 22, 0.25), id="completed_limit_start"),
            pytest.param(Periodicity.WEEKLY, "write", True, AnalysisRange(date(2026, 4, 19), date(2026, 5, 12)),
                         AggregateAnalysis(3, 4, 4, 0.35), id="weekly_name_pending_limit"),
        ])
    def test_analyse(self, runner: CliRunner, patched_get_connection: Mock, mock_service: Mock,
                     patched_create_service: Mock, patched_habit_analysis_filter: Mock,
                     patched_represent_aggregate_analysis: Mock, periodicity_filter: Periodicity | None,
                     name_filter: str | None, pending_filter: bool | None, analysis_range: AnalysisRange,
                     aggregate_analysis: AggregateAnalysis):
        """
        Tests the show command success outcome.

        :param runner: CLI runner.
        :param patched_get_connection: Patched get_connection function.
        :param mock_service: Mock habit service.
        :param patched_create_service: Patched habit service class.
        :param patched_habit_analysis_filter: Patched HabitAnalysisFilter class.
        :param patched_represent_aggregate_analysis: Patched represent_aggregate_analysis function.
        :param periodicity_filter: Periodicity to filter with, or None if should not filter.
        :param name_filter: Name search string to filter with, or None if should not filter.
        :param pending_filter: Pending value to filter with, or None if should not filter.
        :param analysis_range: Habit analysis time range.
        :param aggregate_analysis: Aggregate analysis the service should return.
        :return: Nothing.
        """
        mock_service.analyse.return_value = aggregate_analysis
        range_specified = bool(analysis_range.start or analysis_range.end)
        expected_filter_calls, expected_filters = prepare_filter_expects(patched_habit_analysis_filter,
                                                                         periodicity_filter, name_filter,
                                                                         pending_filter)
        fake_represent_aggregate_analysis = lambda analysis, analysis_limited: repr(analysis)
        patched_represent_aggregate_analysis.side_effect = fake_represent_aggregate_analysis
        expected_output = fake_represent_aggregate_analysis(aggregate_analysis, range_specified)

        result = runner.invoke(cli,
                               make_args(base="analyse", periodicity_filter=periodicity_filter, name_filter=name_filter,
                                         pending_filter=pending_filter, analysis_range=analysis_range))

        for expected_filter_call in expected_filter_calls:
            expected_filter_call[0].assert_called_once_with(expected_filter_call[1])
        mock_service.analyse.assert_called_once()
        assert set(mock_service.analyse.call_args[0][0]) == expected_filters
        assert mock_service.analyse.call_args[0][1] == analysis_range
        patched_represent_aggregate_analysis.assert_called_once_with(aggregate_analysis, range_specified)
        assert result.output == expected_output + "\n"

# The debug seed command is itself a testing utility (for manual testing), so it is not covered by the test suite.
