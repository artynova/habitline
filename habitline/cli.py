import click


@click.group(help="A simple CLI application for managing, tracking, and analysing habits.")
def cli():
    """Prepares a database connection to be used by nested commands."""
    click.echo("Prepare database connection...")


@cli.command(help="Create a new habit.")
def create():
    """Creates a habit."""
    click.echo("Create a habit...")


@cli.command(help="Log habit completion.")
def complete():
    """Logs a habit completion."""
    click.echo("Mark habit completion...")


@cli.command(help="Edit a habit.")
def edit():
    """Edits a habit."""
    click.echo("Edit a habit...")


@cli.command(help="Delete a habit.")
def delete():
    """Deletes a habit."""
    click.echo("Delete a habit...")


@cli.command(help="View a habit.")
def view():
    """Shows detailed data of a specific habit."""
    click.echo("View a habit...")


@cli.command("list", help="View a list of habits.")
def list_habits():
    """Shows data of multiple habits."""
    click.echo("View a list of habits...")


@cli.command(help="Generate aggregate analysis of multiple habits.")
def analyse():
    """Shows an aggregate analysis of multiple habits."""
    click.echo("Analyse habits...")
