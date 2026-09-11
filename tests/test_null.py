import pytest

from pydb.column import Column
from pydb.database import Database
from pydb.lexer import Lexer
from pydb.parser import Parser


def test_column_accepts_none():
    """
    Verify that a column accepts None as the internal
    representation of SQL NULL.
    """
    column = Column("age", "INT")

    assert column.validate(None) is True


def test_lexer_recognizes_null():
    """
    Verify that NULL is recognized as a SQL keyword.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "NULL"
    )

    assert len(tokens) == 1
    assert tokens[0].token_type == "KEYWORD"
    assert tokens[0].value == "NULL"


def test_insert_parser_converts_null_to_none():
    """
    Verify that the INSERT parser converts SQL NULL into
    Python None.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (1, NULL);"
    )

    assert query.row == [1, None]


def test_update_parser_converts_null_to_none():
    """
    Verify that the UPDATE parser converts SQL NULL into
    Python None.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users SET name = NULL;"
    )

    assert query.updates == {
        "name": None
    }


def test_insert_null_into_table():
    """
    Verify that a row containing SQL NULL can be inserted.
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

    database.execute(
        "INSERT INTO users VALUES (1, NULL);"
    )

    result = database.execute(
        "SELECT * FROM users;"
    )

    assert result == [
        [1, None]
    ]


def test_insert_multiple_null_values():
    """
    Verify that multiple NULL values can exist in the same row.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT,
            age INT,
            salary FLOAT,
            active BOOL
        );
        """
    )

    database.execute(
        "INSERT INTO users VALUES (1, NULL, NULL, NULL, NULL);"
    )

    result = database.execute(
        "SELECT * FROM users;"
    )

    assert result == [
        [1, None, None, None, None]
    ]


def test_update_value_to_null():
    """
    Verify that an existing column value can be changed to NULL.
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

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute(
        "UPDATE users SET name = NULL;"
    )

    result = database.execute(
        "SELECT * FROM users;"
    )

    assert result == [
        [1, None]
    ]


def test_null_persists_to_storage(tmp_path):
    """
    Verify that NULL values are correctly persisted and
    loaded from disk.
    """
    database_file = tmp_path / "pydb.json"

    database = Database(str(database_file))

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT
        );
        """
    )

    database.execute(
        "INSERT INTO users VALUES (1, NULL);"
    )

    database.save()

    loaded_database = Database(
        str(database_file)
    )

    result = loaded_database.execute(
        "SELECT * FROM users;"
    )

    assert result == [
        [1, None]
    ]


def test_null_is_allowed_for_all_data_types():
    """
    Verify that SQL NULL can be stored in every supported
    data type.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE values_test (
            int_value INT,
            text_value TEXT,
            float_value FLOAT,
            bool_value BOOL
        );
        """
    )

    database.execute(
        """
        INSERT INTO values_test
        VALUES (NULL, NULL, NULL, NULL);
        """
    )

    result = database.execute(
        "SELECT * FROM values_test;"
    )

    assert result == [
        [None, None, None, None]
    ]