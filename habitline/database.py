from sqlite3 import connect, Connection


def get_connection(path: str) -> Connection:
    """
    Obtains the database connection based on the given database file path.
    Ensures that the database is ready for use.

    :param path: Path to the database file.
    :return: Database connection.
    """
    connection = connect(path)
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
            habit_id INTEGER NOT NULL REFERENCES habit (id) ON DELETE CASCADE,
            completed_at INTEGER NOT NULL,
            PRIMARY KEY (habit_id, completed_at)
        )""")
