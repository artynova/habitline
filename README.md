# HabitLine

## Context

The project is developed for a course at the [International University of Applied Sciences](https://www.iu.org/).

## Key Features

- Flexible command-line interface.
- Habit management and completion logging.
- Habit identification via either numeric ID or unique name.
- Analysis of habit completion statistics with possible restrictions to a specific time range. This affects
  the calculations of the streak (becomes "streak by the end of the range"), longest streak, and failure rate.
- Aggregate analysis of the habit collection.

# Technology Stack

- Click for CLI implementation.
- sqlite3 for database interactions.
- SQLite for persistence.
- pytest for testing.

# Running the Application

## As a Regular CLI Tool

- Have Python installed. Minimum version - 3.11.
- Clone the repository and navigate into its folder.
- Run `pip install -e .`.
- Start a new terminal session. The CLI tool should now be installed.
- Run `habitline` or `habitline --help` to print help about commands.

# As a Developer

- Have Python installed. Minimum version - 3.11.
- Clone the repository and navigate into its folder.
- Create a virtual environment and activate it via your method of choice. For example, run `python -m venv .venv` and
  `.venv/Scripts/activate`.
- Run `pip install -e .[dev]`. The CLI tool should now be installed with development-specific dependencies, particularly
  for testing.
- Run `habitline` or `habitline --help` to print help about commands.

# Testing the Application

Run `pytest` after installing the development version. This will all tests and a coverage report.
