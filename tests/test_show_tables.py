import pytest

from pydb.database import Database
from pydb.parser import Parser
from pydb.query import ShowTablesQuery


def test_parse_show_tables():
    """
    Verify that SHOW TABLES is converted into a
    ShowTablesQuery object.
    """
    parser = Parser()

    query = parser.parse(
        "SHOW TABLES;"
    )

    assert isinstance(query, ShowTablesQuery)


def test_show_tables_empty_database():
    """
    Verify that SHOW TABLES returns an empty list when
    the database contains no tables.
    """
    database = Database(":memory:")

    result = database.execute(
        "SHOW TABLES;"
    )

    assert result == []


def test_show_one_table():
    """
    Verify that SHOW TABLES returns the name of an
    existing table.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    result = database.execute(
        "SHOW TABLES;"
    )

    assert result == ["users"]


def test_show_multiple_tables():
    """
    Verify that SHOW TABLES returns all existing tables.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    database.execute(
        """
        CREATE TABLE products (
            id INT,
            name TEXT
        );
        """
    )

    result = database.execute(
        "SHOW TABLES;"
    )

    assert result == [
        "users",
        "products"
    ]


def test_show_tables_after_drop():
    """
    Verify that SHOW TABLES reflects a table that has
    been dropped.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    database.execute(
        """
        CREATE TABLE products (
            id INT
        );
        """
    )

    database.execute(
        "DROP TABLE users;"
    )

    result = database.execute(
        "SHOW TABLES;"
    )

    assert result == ["products"]


def test_show_tables_does_not_modify_database():
    """
    Verify that SHOW TABLES does not mark the database
    as having unsaved changes.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    database.save()

    assert database.dirty is False

    database.execute(
        "SHOW TABLES;"
    )

    assert database.dirty is False


def test_show_tables_missing_tables_keyword():
    """
    Verify that SHOW without TABLES is rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SHOW;"
        )


def test_show_tables_unexpected_token():
    """
    Verify that unexpected tokens after SHOW TABLES
    are rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SHOW TABLES users;"
        )