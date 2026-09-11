from pydb.database import Database
import pytest


def test_create_table_through_sql():
    """
    Verify that a CREATE TABLE SQL statement passes through
    the complete SQL pipeline and creates a table.
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


def test_create_table_with_primary_key_through_sql():
    """
    Verify that CREATE TABLE correctly creates a table
    with a primary key through the complete SQL pipeline.
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

    table = database.get_table("users")

    assert table.primary_key == "id"


def test_create_table_with_multiple_columns_through_sql():
    """
    Verify that CREATE TABLE correctly creates all
    specified columns through the complete SQL pipeline.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE employees (
            id INT PRIMARY KEY,
            name TEXT,
            salary FLOAT,
            active BOOL
        );
        """
    )

    table = database.get_table("employees")

    assert len(table.columns) == 4

    assert table.columns[0].name == "id"
    assert table.columns[0].data_type == "INT"

    assert table.columns[1].name == "name"
    assert table.columns[1].data_type == "TEXT"

    assert table.columns[2].name == "salary"
    assert table.columns[2].data_type == "FLOAT"

    assert table.columns[3].name == "active"
    assert table.columns[3].data_type == "BOOL"

    assert table.primary_key == "id"


def test_create_table_then_insert_through_sql():
    """
    Verify that a table created using SQL can immediately
    be used by another SQL statement to insert data.
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
        """
        INSERT INTO users VALUES (1, 'Aditya');
        """
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, "Aditya"]
    ]


def test_create_table_then_select_through_sql():
    """
    Verify that a table created using SQL can be queried
    using SELECT through the complete SQL pipeline.
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
        """
        INSERT INTO users VALUES (1, 'Aditya');
        """
    )

    database.execute(
        """
        INSERT INTO users VALUES (2, 'Rahul');
        """
    )

    result = database.execute(
        """
        SELECT * FROM users;
        """
    )

    assert result == [
        [1, "Aditya"],
        [2, "Rahul"]
    ]


# ============================================================
# UNIQUE constraint SQL integration tests
# ============================================================


def test_create_table_with_unique_through_sql():
    """
    Verify that UNIQUE is correctly handled through the
    complete SQL pipeline.
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

    table = database.get_table("users")

    assert table.columns[0].unique is False
    assert table.columns[1].unique is True


def test_unique_rejects_duplicate_values_through_sql():
    """
    Verify that duplicate values in a UNIQUE column are
    rejected when using actual SQL statements.
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

    database.execute(
        """
        INSERT INTO users VALUES (1, 'aditya@example.com');
        """
    )

    with pytest.raises(ValueError, match="Duplicate value"):
        database.execute(
            """
            INSERT INTO users VALUES (2, 'aditya@example.com');
            """
        )


def test_unique_allows_different_values_through_sql():
    """
    Verify that different values can be inserted into a
    UNIQUE column through actual SQL statements.
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

    database.execute(
        """
        INSERT INTO users VALUES (1, 'aditya@example.com');
        """
    )

    database.execute(
        """
        INSERT INTO users VALUES (2, 'rahul@example.com');
        """
    )

    result = database.execute(
        """
        SELECT * FROM users;
        """
    )

    assert result == [
        [1, "aditya@example.com"],
        [2, "rahul@example.com"]
    ]


def test_nullable_unique_allows_multiple_nulls_through_sql():
    """
    Verify SQL NULL semantics for a nullable UNIQUE column.

    Multiple NULL values are allowed because NULL does not
    represent a duplicate concrete value.
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

    database.execute(
        """
        INSERT INTO users VALUES (1, NULL);
        """
    )

    database.execute(
        """
        INSERT INTO users VALUES (2, NULL);
        """
    )

    result = database.execute(
        """
        SELECT * FROM users;
        """
    )

    assert result == [
        [1, None],
        [2, None]
    ]


def test_not_null_unique_rejects_null_through_sql():
    """
    Verify that NOT NULL combined with UNIQUE rejects
    SQL NULL values.
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

    with pytest.raises(TypeError):
        database.execute(
            """
            INSERT INTO users VALUES (1, NULL);
            """
        )


def test_unique_not_null_order_through_sql():
    """
    Verify that UNIQUE followed by NOT NULL is also
    accepted by the SQL parser and enforced correctly.
    """
    database = Database(":memory:")

    database.execute(
        """
        CREATE TABLE users (
            id INT,
            email TEXT UNIQUE NOT NULL
        );
        """
    )

    table = database.get_table("users")

    assert table.columns[1].unique is True
    assert table.columns[1].nullable is False

    with pytest.raises(TypeError):
        database.execute(
            """
            INSERT INTO users VALUES (1, NULL);
            """
        )


def test_unique_with_primary_key_through_sql():
    """
    Verify that UNIQUE and PRIMARY KEY can coexist on
    the same column through the SQL pipeline.
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

    table = database.get_table("users")

    assert table.primary_key == "id"
    assert table.columns[0].unique is True

    database.execute(
        """
        INSERT INTO users VALUES (1, 'aditya@example.com');
        """
    )

    with pytest.raises(ValueError, match="Duplicate"):
        database.execute(
            """
            INSERT INTO users VALUES (1, 'rahul@example.com');
            """
        )