import pytest

from pydb.database import Database
from pydb.condition import Condition
from pydb.executor import QueryExecutor
from pydb.query import (
    InsertQuery,
    SelectQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    DescribeTableQuery
)


def test_insert():
    """
    Verify that the executor can insert a row into a table.
    """

    db = Database()

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    executor = QueryExecutor(db)

    executor.insert(
        "users",
        [1, "Aditya", 22]
    )

    assert table.rows == [
        [1, "Aditya", 22]
    ]


def test_select():
    """
    Verify that the executor can retrieve rows from a table.
    """

    db = Database()

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])

    executor = QueryExecutor(db)

    result = executor.select("users")

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_update():
    """
    Verify that the executor can update matching rows.
    """

    db = Database()

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])

    executor = QueryExecutor(db)

    affected = executor.update(
        "users",
        {"age": 23},
        Condition("name", "=", "Aditya")
    )

    assert affected == 1
    assert table.rows == [
        [1, "Aditya", 23]
    ]


def test_delete():
    """
    Verify that the executor can delete matching rows.
    """

    db = Database()

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])

    executor = QueryExecutor(db)

    affected = executor.delete(
        "users",
        Condition("name", "=", "Aditya")
    )

    assert affected == 1

    assert table.rows == [
        [2, "Rahul", 25]
    ]


def test_begin_transaction(tmp_path):
    """
    Verify that the executor can start a database transaction.
    """

    db = Database(tmp_path / "test.json")
    executor = QueryExecutor(db)

    executor.begin()

    assert db._snapshot is not None


def test_commit_transaction(tmp_path):
    """
    Verify that the executor can commit a transaction
    and persist the changes.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    executor = QueryExecutor(db)

    table.insert([1, "Aditya", 22])

    executor.begin()

    executor.update(
        "users",
        {"age": 23},
        Condition("name", "=", "Aditya")
    )

    executor.commit()

    # Create a new database instance to verify persistence
    new_db = Database(tmp_path / "test.json")

    users = new_db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 23]
    ]


def test_rollback_transaction(tmp_path):
    """
    Verify that the executor can roll back changes
    made during a transaction.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])

    executor = QueryExecutor(db)

    executor.begin()

    executor.update(
        "users",
        {"age": 30},
        Condition("name", "=", "Aditya")
    )

    executor.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22]
    ]


def test_execute_insert(tmp_path):
    """
    Verify that execute() can execute an InsertQuery.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    executor = QueryExecutor(db)

    query = InsertQuery(
        "users",
        [1, "Aditya", 22]
    )

    executor.execute(query)

    assert table.rows == [
        [1, "Aditya", 22]
    ]


def test_execute_select(tmp_path):
    """
    Verify that execute() can execute a SelectQuery.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])

    executor = QueryExecutor(db)

    query = SelectQuery(
        "users",
        columns=["name", "age"]
    )

    result = executor.execute(query)

    assert result == [
        ["Aditya", 22],
        ["Rahul", 25]
    ]


def test_execute_update(tmp_path):
    """
    Verify that execute() can execute an UpdateQuery.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])

    executor = QueryExecutor(db)

    query = UpdateQuery(
        "users",
        {"age": 25},
        Condition("name", "=", "Aditya")
    )

    affected = executor.execute(query)

    assert affected == 1
    assert table.rows == [
        [1, "Aditya", 25]
    ]


def test_execute_delete(tmp_path):
    """
    Verify that execute() can execute a DeleteQuery.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])

    executor = QueryExecutor(db)

    query = DeleteQuery(
        "users",
        Condition("name", "=", "Aditya")
    )

    affected = executor.execute(query)

    assert affected == 1
    assert table.rows == [
        [2, "Rahul", 25]
    ]


def test_execute_begin(tmp_path):
    """
    Verify that execute() can start a transaction.
    """

    db = Database(tmp_path / "test.json")
    executor = QueryExecutor(db)

    executor.begin()

    assert db._snapshot is not None


def test_execute_commit(tmp_path):
    """
    Verify that a transaction can be committed through
    the executor.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])

    executor = QueryExecutor(db)

    executor.begin()

    executor.update(
        "users",
        {"age": 25},
        Condition("name", "=", "Aditya")
    )

    executor.commit()

    new_db = Database(tmp_path / "test.json")

    assert new_db.get_table("users").rows == [
        [1, "Aditya", 25]
    ]


def test_execute_rollback(tmp_path):
    """
    Verify that a transaction can be rolled back through
    the executor.
    """

    db = Database(tmp_path / "test.json")

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])

    executor = QueryExecutor(db)

    executor.begin()

    executor.update(
        "users",
        {"age": 30},
        Condition("name", "=", "Aditya")
    )

    executor.rollback()

    assert db.get_table("users").rows == [
        [1, "Aditya", 22]
    ]


def test_executor_create_table():
    """
    Verify that QueryExecutor can execute a CREATE TABLE query.
    """

    database = Database(":memory:")

    query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    result = database.executor.execute(query)

    assert result.name == "users"

    assert database.list_tables() == ["users"]


def test_executor_create_table_with_primary_key():
    """
    Verify that QueryExecutor correctly forwards the primary key.
    """

    database = Database(":memory:")

    query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    result = database.executor.execute(query)

    assert result.name == "users"

    assert result.primary_key == "id"

    assert database.list_tables() == ["users"]


def test_executor_create_table_preserves_columns():
    """
    Verify that the created table contains the expected columns.
    """

    database = Database(":memory:")

    query = CreateTableQuery(
        table_name="employees",
        columns=[
            ("id", "INT"),
            ("name", "TEXT"),
            ("salary", "FLOAT")
        ]
    )

    table = database.executor.execute(query)

    assert [
        (column.name, column.data_type)
        for column in table.columns
    ] == [
        ("id", "INT"),
        ("name", "TEXT"),
        ("salary", "FLOAT")
    ]


# ============================================================
# UNIQUE constraint tests
# ============================================================


def test_executor_create_table_with_unique_column():
    """
    Verify that QueryExecutor preserves UNIQUE metadata
    when creating a table.
    """

    database = Database(":memory:")

    query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table = database.executor.execute(query)

    assert table.columns[0].unique is False
    assert table.columns[1].unique is True


def test_executor_insert_rejects_duplicate_unique_value():
    """
    Verify that a duplicate value in a UNIQUE column is
    rejected when the INSERT is executed through the executor.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    database.executor.execute(create_query)

    first_insert = InsertQuery(
        "users",
        [1, "aditya@example.com"]
    )

    database.executor.execute(first_insert)

    duplicate_insert = InsertQuery(
        "users",
        [2, "aditya@example.com"]
    )

    with pytest.raises(ValueError, match="Duplicate value"):
        database.executor.execute(duplicate_insert)


def test_executor_insert_allows_different_unique_values():
    """
    Verify that different values can be inserted into a
    UNIQUE column.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, "aditya@example.com"]
        )
    )

    database.executor.execute(
        InsertQuery(
            "users",
            [2, "rahul@example.com"]
        )
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, "aditya@example.com"],
        [2, "rahul@example.com"]
    ]


def test_executor_nullable_unique_allows_multiple_nulls():
    """
    Verify that a nullable UNIQUE column can contain multiple
    NULL values.

    SQL NULL values are represented by Python None.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, None]
        )
    )

    database.executor.execute(
        InsertQuery(
            "users",
            [2, None]
        )
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, None],
        [2, None]
    ]


def test_executor_not_null_unique_rejects_null():
    """
    Verify that a NOT NULL + UNIQUE column rejects NULL values.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("email", "TEXT", False, True)
        ]
    )

    database.executor.execute(create_query)

    insert_query = InsertQuery(
        "users",
        [1, None]
    )

    with pytest.raises(TypeError):
        database.executor.execute(insert_query)


def test_executor_unique_with_primary_key():
    """
    Verify that UNIQUE metadata and primary-key metadata can
    coexist on the same column.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT", True, True),
            ("email", "TEXT")
        ],
        primary_key="id"
    )

    table = database.executor.execute(create_query)

    assert table.primary_key == "id"
    assert table.columns[0].unique is True

    database.executor.execute(
        InsertQuery(
            "users",
            [1, "aditya@example.com"]
        )
    )

    with pytest.raises(ValueError, match="Duplicate"):
        database.executor.execute(
            InsertQuery(
                "users",
                [1, "rahul@example.com"]
            )
        )


# ============================================================
# DESCRIBE TABLE tests
# ============================================================


def test_execute_describe_table_query_includes_nullable_metadata():
    """
    Verify that DescribeTableQuery execution exposes nullable
    metadata through the executor's execute() method.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT", False),
            ("name", "TEXT")
        ]
    )

    database.executor.execute(create_query)

    describe_query = DescribeTableQuery("users")

    result = database.executor.execute(describe_query)

    assert result == [
        {
            "name": "id",
            "type": "INT",
            "primary_key": False,
            "nullable": False,
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

# ============================================================
# DEFAULT constraint tests
# ============================================================


def test_executor_insert_uses_default_value():
    """
    Verify that INSERT with DEFAULT uses the column's
    configured default value.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT", True, False, 18)
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, "Aditya", InsertQuery.DEFAULT]
        )
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, "Aditya", 18]
    ]


def test_executor_insert_explicit_null_does_not_use_default():
    """
    Verify that an explicit SQL NULL remains NULL instead of
    being replaced by the column's default value.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT", True, False, 18)
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, "Aditya", None]
        )
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, "Aditya", None]
    ]


def test_executor_insert_default_with_not_null():
    """
    Verify that DEFAULT can satisfy a NOT NULL constraint when
    the configured default is a valid non-NULL value.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("age", "INT", False, False, 18)
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, InsertQuery.DEFAULT]
        )
    )

    table = database.get_table("users")

    assert table.rows == [
        [1, 18]
    ]


def test_executor_insert_default_without_configured_default_rejects():
    """
    Verify that DEFAULT cannot be used when the column has no
    configured default value.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("age", "INT", False)
        ]
    )

    database.executor.execute(create_query)

    with pytest.raises(ValueError, match="default"):
        database.executor.execute(
            InsertQuery(
                "users",
                [1, InsertQuery.DEFAULT]
            )
        )

def test_executor_default_respects_unique_constraint():
    """
    Verify that a DEFAULT value is still checked against
    UNIQUE constraints after it is resolved.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            (
                "email",
                "TEXT",
                True,
                True,
                "unknown@example.com"
            )
        ]
    )

    database.executor.execute(create_query)

    database.executor.execute(
        InsertQuery(
            "users",
            [1, InsertQuery.DEFAULT]
        )
    )

    with pytest.raises(ValueError, match="Duplicate value"):
        database.executor.execute(
            InsertQuery(
                "users",
                [2, InsertQuery.DEFAULT]
            )
        )


def test_executor_default_null_rejected_by_not_null():
    """
    Verify that DEFAULT NULL is rejected when the column
    is NOT NULL.
    """

    database = Database(":memory:")

    create_query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("age", "INT", False, False, None)
        ]
    )

    database.executor.execute(create_query)

    with pytest.raises(TypeError):
        database.executor.execute(
            InsertQuery(
                "users",
                [1, InsertQuery.DEFAULT]
            )
        )