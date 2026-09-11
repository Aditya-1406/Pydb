import pytest

from pydb.database import Database
from pydb.parser import Parser
from pydb.query import DropTableQuery


def test_parse_drop_table():
    """
    Verify that DROP TABLE is converted into a DropTableQuery.
    """
    parser = Parser()

    query = parser.parse(
        "DROP TABLE users;"
    )

    assert isinstance(query, DropTableQuery)
    assert query.table_name == "users"


def test_drop_table():
    """
    Verify that DROP TABLE removes an existing table.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT
        );
        """
    )

    assert "users" in database.list_tables()

    database.execute(
        "DROP TABLE users;"
    )

    assert "users" not in database.list_tables()


def test_drop_table_with_data():
    """
    Verify that DROP TABLE removes the table together with
    all rows stored inside it.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name TEXT
        );
        """
    )

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute(
        "DROP TABLE users;"
    )

    assert "users" not in database.list_tables()


def test_drop_nonexistent_table():
    """
    Verify that attempting to drop a table that does not
    exist raises an error.
    """
    database = Database(":memory:")

    with pytest.raises(ValueError):
        database.execute(
            "DROP TABLE users;"
        )


def test_drop_table_missing_table_keyword():
    """
    Verify that DROP without TABLE is rejected by the parser.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "DROP users;"
        )


def test_drop_table_missing_name():
    """
    Verify that DROP TABLE without a table name is rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "DROP TABLE;"
        )


def test_drop_table_unexpected_token():
    """
    Verify that unexpected tokens after the table name
    are rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "DROP TABLE users something;"
        )