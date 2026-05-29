import click

DEFAULT_DB_PATH = "database.db"


@click.group(help="A simple CLI application for managing, tracking, and analysing habits.")
def cli():
    """
    Prepares a database connection to be used by nested commands, serves as the root Click command group.

    :return: Nothing.
    """
    click.echo("Prepare database connection...")


@cli.command(help="Create a new habit.")
def create():
    """
    Creates a habit.

    :return: Nothing.
    """
    click.echo("Create a habit...")


@cli.command(help="Log habit completion.")
def complete():
    """
    Logs a habit completion.

    :return: Nothing.
    """
    click.echo("Mark habit completion...")


@cli.command(help="Edit a habit.")
def edit():
    """
    Edits a habit.

    :return: Nothing.
    """
    click.echo("Edit a habit...")


@cli.command(help="Delete a habit.")
def delete():
    """
    Deletes a habit.

    :return: Nothing.
    """
    click.echo("Delete a habit...")


@cli.command(help="View a habit.")
def view():
    """
    Shows detailed data of a specific habit.

    :return: Nothing.
    """
    click.echo("View a habit...")


@cli.command("list", help="View a list of habits.")
def list_habits():
    """
    Shows data of multiple habits.

    :return: Nothing.
    """
    click.echo("View a list of habits...")


@cli.command(help="Generate aggregate analysis of multiple habits.")
def analyse():
    """
    Shows an aggregate analysis of multiple habits.

    :return: Nothing.
    """
    click.echo("Analyse habits...")


@cli.group(help="Special debugging commands, not for regular usage.")
def debug():
    """
    Does nothing, serves as the Click command group for debug commands.

    :return: Nothing.
    """
    pass


@debug.command(help="Fill the database with predefined habits that have example tracking data.")
def seed():
    """
    Seeds the database with predefined example habits for manual testing purposes.

    :return: Nothing.
    """
    click.echo("Seeding the database...")
