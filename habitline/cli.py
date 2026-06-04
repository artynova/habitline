from datetime import datetime
from enum import Enum
from sqlite3 import Connection

import click

from fixtures.seed import make_test_habits, insert_raw, clear_database
from habitline.analytics import AnalysisRange, HabitAnalysisFilter, HabitAnalysisOrder, HabitAnalysis
from habitline.database import get_connection
from habitline.repository import HabitIdentifier, Periodicity
from habitline.service import HabitService

DEFAULT_DB_PATH = "database.db"

pass_connection = click.make_pass_decorator(Connection)


def parse_identifier_input(identifier: str, use_id: bool) -> HabitIdentifier:
    """
    Processes habit identifier input.
    Raises an error if use_id is True and the identifier string is not an integer.

    :param identifier: Identifier input string.
    :param use_id: Numeric ID usage flag.
    :return: Identifier string itself if use_id is False, parsed integer from the string if use_id is True.
    """
    if not use_id:
        return identifier
    if not identifier.isdigit():
        raise click.BadParameter(f'Identifier "{identifier}" is not an integer.')
    return int(identifier)


@click.group(help="A simple CLI application for managing, tracking, and analysing habits.")
@click.option("--path", envvar="HABITLINE_PATH", default=DEFAULT_DB_PATH, help="Specify custom database file path.",
              type=click.Path())
@click.pass_context
def cli(context: click.Context, path: str):
    """
    Prepares a database connection to be used by nested commands, serves as the root Click command group.

    :return: Nothing.
    """
    context.ensure_object(dict)
    connection = get_connection(path)
    context.obj = connection
    context.call_on_close(connection.close)


@cli.command(help="Create a new habit.")
@click.argument("name")
@click.argument("periodicity", type=click.Choice(Periodicity, case_sensitive=False))
@pass_connection
def create(connection: Connection, name: str, periodicity: Periodicity):
    """
    Creates a habit.

    :return: Nothing.
    """
    service = HabitService(connection)
    service.create(name, periodicity)


@cli.command(help="Log habit completion.")
@click.argument("identifier")
@click.option("--use-id", is_flag=True,
              help="Interpret the identifier as habit's numeric ID. In this case the identifier must be an integer.")
@pass_connection
def complete(connection: Connection, identifier: str, use_id: bool):
    """
    Logs a habit completion.

    :param connection: Database connection.
    :param identifier: Habit identifier.
    :param use_id: Whether to interpret the identifier as a numeric ID.
    :return: Nothing.
    """
    habit_id = parse_identifier_input(identifier, use_id)
    service = HabitService(connection)
    service.complete(habit_id)


@cli.command(help="Edit a habit.")
@click.argument("identifier")
@click.argument("name")
@click.option("--use-id", is_flag=True,
              help="Interpret the identifier as habit's numeric ID. In this case the identifier must be an integer.")
@pass_connection
def edit(connection: Connection, identifier: str, name: str, use_id: bool):
    """
    Edits a habit.

    :param connection: Database connection.
    :param identifier: Habit identifier.
    :param name: New habit name.
    :param use_id: Whether to interpret the identifier as a numeric ID.
    :return: Nothing.
    """
    habit_id = parse_identifier_input(identifier, use_id)
    service = HabitService(connection)
    service.edit(habit_id, name)


@cli.command(help="Delete a habit.")
@click.argument("identifier")
@click.option("--use-id", is_flag=True,
              help="Interpret the identifier as habit's numeric ID. In this case the identifier must be an integer.")
@pass_connection
def delete(connection: Connection, identifier: str, use_id: bool):
    """
    Deletes a habit.

    :param connection: Database connection.
    :param identifier: Habit identifier.
    :param use_id: Whether to interpret the identifier as a numeric ID.
    :return: Nothing.
    """
    habit_id = parse_identifier_input(identifier, use_id)
    service = HabitService(connection)
    service.delete(habit_id)


def format_percentage(percentage: float) -> str:
    """
    Format percentage for user-facing output, with 1 decimal digit.

    :param percentage: Float percentage from 0 to 1, e.g., 0.5627.
    :return: Formatted percentage, e.g., 56.3%.
    """
    return f"{percentage:.1%}"


def represent_habit(analysis: HabitAnalysis, show_completions: bool = False) -> str:
    """
    Represent the given habit analysis for user-facing output.

    :param analysis: Habit analysis.
    :param show_completions: Whether to show the logged habit completions.
    :return: Representation string.
    """
    habit = analysis.habit
    representation = f"ID:\t\t{habit.id}\n" + \
                     f"Name:\t\t{habit.name}\n" + \
                     f"Periodicity:\t{habit.periodicity.name.capitalize()}\n" + \
                     f"Created at:\t{habit.created_at}\n" + \
                     f"Current streak:\t{analysis.streak}\n" + \
                     f"Longest streak:\t{analysis.longest_streak}\n" + \
                     f"Failure rate:\t{format_percentage(analysis.failure_rate)}\n" + \
                     f"Pending:\t{analysis.pending}"
    if show_completions:
        representation += "\nCompletions:\n" + "\n".join([f"- {completion}" for completion in habit.completions])

    return representation


@cli.command(help="View a habit.")
@click.argument("identifier")
@click.option("--use-id", is_flag=True,
              help="Interpret the identifier as habit's numeric ID. In this case the identifier must be an integer.")
@click.option("--show-completions", is_flag=True, help="Show logged habit completions.")
@pass_connection
def view(connection: Connection, identifier: str, use_id: bool, show_completions: bool):
    """
    Shows detailed data of a specific habit.

    :param connection: Database connection.
    :param identifier: Habit identifier.
    :param use_id: Whether to interpret the identifier as a numeric ID.
    :param show_completions: Whether to show the logged habit completions.
    :return: Nothing.
    """
    habit_id = parse_identifier_input(identifier, use_id)
    service = HabitService(connection)
    habit = service.get_one(habit_id, AnalysisRange(None, None))

    click.echo(represent_habit(habit, show_completions))


class OrderOption(Enum):
    """
    Habit analysis order option.
    """
    NAME = 0
    CREATED_AT = 1
    STREAK = 2
    LONGEST_STREAK = 3
    FAILURE_RATE = 4


def make_habit_filters(periodicity: Periodicity | None, pending: bool | None, search: str | None) -> list[
    HabitAnalysisFilter]:
    """
    Creates habit analysis filters based on given inputs.

    :param periodicity: Habit periodicity to filter by, if any.
    :param pending: Habit pending state to filter by, if any.
    :param search: Habit name search string to filter by, if any.
    :return: List of habit analysis filters.
    """
    filters: list[HabitAnalysisFilter] = []
    if periodicity is not None:
        filters.append(HabitAnalysisFilter.by_periodicity(periodicity))
    if pending is not None:
        filters.append(HabitAnalysisFilter.by_pending(pending))
    if search is not None:
        filters.append(HabitAnalysisFilter.by_search_match(search))
    return filters


def make_habit_order(option: OrderOption, asc: bool) -> HabitAnalysisOrder:
    """
    Creates the habit analysis sort order based on given options.

    :param option: Order option.
    :param asc: Whether to sort in ascending order.
    :return: Habit analysis sort order.
    """
    match option:
        case OrderOption.NAME:
            return HabitAnalysisOrder.by_name(asc)
        case OrderOption.CREATED_AT:
            return HabitAnalysisOrder.by_created_at(asc)
        case OrderOption.STREAK:
            return HabitAnalysisOrder.by_streak(asc)
        case OrderOption.LONGEST_STREAK:
            return HabitAnalysisOrder.by_longest_streak(asc)
        case OrderOption.FAILURE_RATE:
            return HabitAnalysisOrder.by_failure_rate(asc)
        case _:
            raise NotImplementedError


@cli.command("list", help="View a list of multiple habits.")
@click.option("--periodicity", type=click.Choice(Periodicity, case_sensitive=False),
              help="Filter habits to those with given periodicity.")
@click.option("--pending/--completed", "pending", is_flag=True, default=None,
              help="Filter habits to those that are yet to be completed in the current period or have already been completed, respectively.")
@click.option("--search", help="Filter habits to those whose names include the given string, case-insensitive.")
@click.option("--sort", type=click.Choice(OrderOption, case_sensitive=False), default=OrderOption.NAME,
              help='Sort habits using the given order. "Created at" order is used by default.')
@click.option("--asc/--desc", "asc", is_flag=True, default=True,
              help="Sort in ascending or descending order. Ascending order is used by default.")
@click.option("--analyse-from", type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Limit habit completion analysis to the time period starting at the given date. Date format is YYYY-MM-DD.")
@click.option("--analyse-until", type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Limit habit completion analysis to the time period ending at the given date. Date format is YYYY-MM-DD.")
@pass_connection
def list_habits(connection: Connection, periodicity: Periodicity | None, pending: bool | None, search: str | None,
                sort: OrderOption, asc: bool, analyse_from: datetime | None, analyse_until: datetime | None):
    """
    Shows data of multiple habits.

    :param connection: Database connection.
    :param periodicity: Habit periodicity to filter by, if any.
    :param pending: Habit pending state to filter by, if any.
    :param search: Habit name search string to filter by, if any.
    :param sort: Habit order option.
    :param asc: Whether to sort in ascending order.
    :param analyse_from: Date and time from which to start the habit completion analysis period, if any.
    :param analyse_until: Date and time at which to end the habit completion analysis period, if any.
    :return: Nothing.
    """
    filters = make_habit_filters(periodicity, pending, search)
    order = make_habit_order(sort, asc)
    analysis_range = AnalysisRange(analyse_from, analyse_until)

    service = HabitService(connection)
    habits = service.get_many(filters, order, analysis_range)

    click.echo(f"Found {len(habits)} habits" + (":" if len(habits) > 1 else ""))
    for habit in habits:
        click.echo("-" * 20 + "\n" + represent_habit(habit))


@cli.command(help="Generate aggregate analysis of multiple habits.")
@click.option("--periodicity", type=click.Choice(Periodicity, case_sensitive=False),
              help="Filter habits to those with given periodicity.")
@click.option("--pending/--completed", "pending", is_flag=True, default=None,
              help="Filter habits to those that are yet to be completed in the current period or have already been completed, respectively.")
@click.option("--search", help="Filter habits to those whose names include the given string, case-insensitive.")
@click.option("--analyse-from", type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Limit habit completion analysis to the time period starting at the given date. Date format is YYYY-MM-DD.")
@click.option("--analyse-until", type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Limit habit completion analysis to the time period ending at the given date. Date format is YYYY-MM-DD.")
@pass_connection
def analyse(connection: Connection, periodicity: Periodicity | None, pending: bool | None, search: str | None,
            analyse_from: datetime | None, analyse_until: datetime | None):
    """
    Shows an aggregate analysis of multiple habits.

    :param connection: Database connection.
    :param periodicity: Habit periodicity to filter by, if any.
    :param pending: Habit pending state to filter by, if any.
    :param search: Habit name search string to filter by, if any.
    :param analyse_from: Date and time from which to start the habit completion analysis period, if any.
    :param analyse_until: Date and time at which to end the habit completion analysis period, if any.
    :return: Nothing.
    """
    filters = make_habit_filters(periodicity, pending, search)
    analysis_range = AnalysisRange(analyse_from.date() if analyse_from else None,
                                   analyse_until.date() if analyse_until else None)

    service = HabitService(connection)
    analysis = service.analyse(filters, analysis_range)

    click.echo(f"Analysed habits:\t\t{analysis.habit_count}")
    click.echo(f"Current longest streak:\t\t{analysis.current_longest_streak} periods")
    click.echo(f"Longest recorded streak:\t{analysis.longest_streak} periods")
    click.echo(f"Average failure rate:\t\t{format_percentage(analysis.avg_failure_rate)}")


@cli.group(help="Special debugging commands, not for regular usage.")
def debug():
    """
    Does nothing, serves as the Click command group for debug commands.

    :return: Nothing.
    """
    pass


@debug.command(
    help="Fill the database with predefined habits that have example tracking data, clearing any previous application data.")
@pass_connection
def seed(connection: Connection):
    """
    Seeds the database with predefined example habits for manual testing purposes.
    Clears any other application data from the database.

    :param connection: Database connection.
    :return: Nothing.
    """
    clear_database(connection)
    insert_raw(connection, make_test_habits(datetime.now()))
