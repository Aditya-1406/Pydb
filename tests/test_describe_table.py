import pytest

from pydb.database import Database
from pydb.parser import Parser
from pydb.query import DescribeTableQuery


def test_parse_describe_table():
    """
    Verify that DESCRIBE is converted into a
    DescribeTableQuery object.
    """
    parser = Parser()

    query = parser.parse(
        "DESCRIBE users;"
    )

    assert isinstance(query, DescribeTableQuery)
    assert query.table_name == "users"


def test_describe_table():
    """
    Verify that DESCRIBE returns the schema of a table,
    including nullable and unique metadata.
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

    result = database.execute(
        "DESCRIBE users;"
    )

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        },
        {
            "name": "name",
            "type": "TEXT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        }
    ]


def test_describe_table_with_primary_key():
    """
    Verify that DESCRIBE correctly identifies the
    primary-key column and exposes nullable and unique metadata.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name TEXT,
            salary FLOAT,
            active BOOL
        );
        """
    )

    result = database.execute(
        "DESCRIBE users;"
    )

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": True,
            "nullable": True,
            "unique": False
        },
        {
            "name": "name",
            "type": "TEXT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        },
        {
            "name": "salary",
            "type": "FLOAT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        },
        {
            "name": "active",
            "type": "BOOL",
            "primary_key": False,
            "nullable": True,
            "unique": False
        }
    ]


def test_describe_table_with_unique():
    """
    Verify that DESCRIBE correctly exposes UNIQUE metadata.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            email TEXT UNIQUE
        );
        """
    )

    result = database.execute(
        "DESCRIBE users;"
    )

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        },
        {
            "name": "email",
            "type": "TEXT",
            "primary_key": False,
            "nullable": True,
            "unique": True
        }
    ]


def test_describe_table_with_not_null_unique():
    """
    Verify that DESCRIBE exposes both NOT NULL and UNIQUE
    metadata for the same column.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            email TEXT NOT NULL UNIQUE
        );
        """
    )

    result = database.execute(
        "DESCRIBE users;"
    )

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        },
        {
            "name": "email",
            "type": "TEXT",
            "primary_key": False,
            "nullable": False,
            "unique": True
        }
    ]


def test_describe_table_with_primary_key_and_unique():
    """
    Verify that DESCRIBE correctly exposes PRIMARY KEY
    and UNIQUE metadata when both apply to the same column.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY UNIQUE,
            email TEXT
        );
        """
    )

    result = database.execute(
        "DESCRIBE users;"
    )

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": True,
            "nullable": True,
            "unique": True
        },
        {
            "name": "email",
            "type": "TEXT",
            "primary_key": False,
            "nullable": True,
            "unique": False
        }
    ]


def test_describe_nonexistent_table():
    """
    Verify that DESCRIBE raises an error when the
    requested table does not exist.
    """
    database = Database(":memory:")

    with pytest.raises(ValueError):
        database.execute(
            "DESCRIBE users;"
        )


def test_describe_missing_table_name():
    """
    Verify that DESCRIBE without a table name is rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "DESCRIBE;"
        )


def test_describe_unexpected_token():
    """
    Verify that unexpected tokens after the table name
    are rejected.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "DESCRIBE users something;"
        )


def test_describe_does_not_modify_database():
    """
    Verify that DESCRIBE does not mark the database as dirty.
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

    database.save()

    assert database.dirty is False

    database.execute(
        "DESCRIBE users;"
    )

    assert database.dirty is False