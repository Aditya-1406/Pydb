from pydb.query import (
    InsertQuery,
    SelectQuery,
    UpdateQuery,
    DeleteQuery
)

from pydb.condition import Condition


def test_insert_query():
    """
    Verify that InsertQuery stores the required information.
    """

    query = InsertQuery(
        "users",
        [1, "Aditya", 22]
    )

    assert query.table_name == "users"
    assert query.row == [1, "Aditya", 22]


def test_select_query():
    """
    Verify that SelectQuery stores all SELECT parameters.
    """

    condition = Condition("age", ">=", 18)

    query = SelectQuery(
        "users",
        columns=["name", "age"],
        condition=condition,
        order_by="age",
        descending=True,
        limit=5
    )

    assert query.table_name == "users"
    assert query.columns == ["name", "age"]
    assert query.condition == condition
    assert query.order_by == "age"
    assert query.descending is True
    assert query.limit == 5


def test_update_query():
    """
    Verify that UpdateQuery stores update information.
    """

    condition = Condition("name", "=", "Aditya")

    query = UpdateQuery(
        "users",
        {"age": 30},
        condition
    )

    assert query.table_name == "users"
    assert query.updates == {"age": 30}
    assert query.condition == condition


def test_delete_query():
    """
    Verify that DeleteQuery stores deletion information.
    """

    condition = Condition("age", "<", 18)

    query = DeleteQuery(
        "users",
        condition
    )

    assert query.table_name == "users"
    assert query.condition == condition


from pydb.query import CreateTableQuery


def test_create_table_query():
    """
    Verify that CreateTableQuery stores table schema information.
    """
    query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    assert query.table_name == "users"

    assert query.columns == [
        ("id", "INT"),
        ("name", "TEXT"),
        ("age", "INT")
    ]

    assert query.primary_key == "id"


def test_create_table_query_with_nullable_columns():
    """
    Verify that CreateTableQuery can carry nullable metadata
    for NOT NULL column definitions.
    """
    query = CreateTableQuery(
        table_name="users",
        columns=[
            ("id", "INT", False),
            ("name", "TEXT", True)
        ]
    )

    assert query.columns == [
        ("id", "INT", False),
        ("name", "TEXT", True)
    ]