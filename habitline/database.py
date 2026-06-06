from sqlite3 import connect, Connection


def get_connection(string: str) -> Connection:
    """
    Obtains the database connection based on the given database connection string.
    Ensures that the database is ready for use.

    :param string: Connection string, such as a path to the database file or ":memory:".
    :return: Database connection.
    """
    connection = connect(string)
    prepare_database(connection)
    return connection


def prepare_database(connection: Connection) -> None:
    """
    Ensures that the database is ready for use.

    :param connection: Database connection.
    :return: Nothing.
    """
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            periodicity INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS completion (
            id INTEGER PRIMARY KEY,
            habit_id INTEGER NOT NULL REFERENCES habit (id) ON DELETE CASCADE,
            completed_at INTEGER NOT NULL
        )""")
