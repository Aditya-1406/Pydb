import pytest

from pydb.table import Table
from pydb.database import Database
from pydb.condition import Condition


@pytest.fixture
def users_table():
    return Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )


def test_table_creation(users_table):
    assert users_table.name == "users"
    assert len(users_table.columns) == 3
    assert users_table.rows == []


def test_insert_valid_row(users_table):
    users_table.insert([1, "Aditya", 22])

    assert users_table.rows == [
        [1, "Aditya", 22]
    ]


def test_insert_multiple_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 23])

    assert len(users_table.rows) == 2


def test_insert_wrong_number_of_values(users_table):
    with pytest.raises(ValueError):
        users_table.insert([1, "Aditya"])


def test_insert_wrong_data_type(users_table):
    with pytest.raises(TypeError):
        users_table.insert(["one", "Aditya", 22])


def test_nullable_column_allows_null():
    table = Table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT", True)
        ]
    )

    table.insert([1, None])

    assert table.rows == [
        [1, None]
    ]


def test_not_null_column_rejects_null_on_insert():
    table = Table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT")
        ]
    )

    with pytest.raises(TypeError):
        table.insert([None, "Aditya"])


def test_not_null_column_rejects_null_on_update():
    table = Table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT")
        ]
    )

    table.insert([1, "Aditya"])

    with pytest.raises(TypeError):
        table.update({"id": None})


def test_nullable_metadata_is_stored_in_columns():
    table = Table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT", True),
            ("age", "INT")
        ]
    )

    assert table.columns[0].nullable is False
    assert table.columns[1].nullable is True
    assert table.columns[2].nullable is True


def test_unique_metadata_is_stored_in_columns():
    """
    Verify that UNIQUE metadata is stored correctly
    on the corresponding columns.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True),
            ("name", "TEXT")
        ]
    )

    assert table.columns[0].unique is False
    assert table.columns[1].unique is True
    assert table.columns[2].unique is False


def test_unique_column_rejects_duplicate_values():
    """
    Verify that a UNIQUE column rejects duplicate
    non-NULL values during INSERT.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, "aditya@example.com"])

    with pytest.raises(ValueError):
        table.insert([2, "aditya@example.com"])


def test_unique_column_allows_different_values():
    """
    Verify that different values can be inserted into
    a UNIQUE column.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, "aditya@example.com"])
    table.insert([2, "rahul@example.com"])

    assert table.rows == [
        [1, "aditya@example.com"],
        [2, "rahul@example.com"]
    ]


def test_unique_nullable_column_allows_multiple_nulls():
    """
    Verify that a nullable UNIQUE column allows multiple
    NULL values.

    SQL NULL is represented internally by Python None.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, None])
    table.insert([2, None])

    assert table.rows == [
        [1, None],
        [2, None]
    ]


def test_unique_column_rejects_duplicate_on_update():
    """
    Verify that UPDATE cannot change a UNIQUE column
    to a value already used by another row.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, "aditya@example.com"])
    table.insert([2, "rahul@example.com"])

    with pytest.raises(ValueError):
        table.update(
            {"email": "rahul@example.com"},
            Condition("id", "=", 1)
        )


def test_unique_column_allows_updating_row_to_same_value():
    """
    Verify that a row can be updated with its own existing
    UNIQUE value.

    The row should not be considered a duplicate of itself.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, "aditya@example.com"])

    affected = table.update(
        {"email": "aditya@example.com"},
        Condition("id", "=", 1)
    )

    assert affected == 1

    assert table.rows == [
        [1, "aditya@example.com"]
    ]


def test_unique_constraint_survives_reload(tmp_path):
    """
    Verify that a UNIQUE constraint remains enforced
    after the database is saved and loaded again.
    """
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("email", "TEXT", True, True)
        ]
    )

    table.insert([1, "aditya@example.com"])

    db.save()

    new_db = Database(db_file)

    reloaded_table = new_db.get_table("users")

    with pytest.raises(ValueError):
        reloaded_table.insert(
            [2, "aditya@example.com"]
        )


def test_multiple_tables_persistence(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    products = db.create_table(
        "products",
        [
            ("id", "INT"),
            ("price", "FLOAT")
        ]
    )

    users.insert([1, "Aditya"])
    products.insert([101, 499.99])

    db.save()

    new_db = Database(db_file)

    assert new_db.list_tables() == ["users", "products"]

    assert new_db.get_table("users").rows == [
        [1, "Aditya"]
    ]

    assert new_db.get_table("products").rows == [
        [101, 499.99]
    ]


def test_order_by_ascending(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])
    users_table.insert([3, "Karan", 20])

    result = users_table.select(order_by="age")

    assert result == [
        [3, "Karan", 20],
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_order_by_descending(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])
    users_table.insert([3, "Karan", 20])

    result = users_table.select(
        order_by="age",
        descending=True
    )

    assert result == [
        [2, "Rahul", 25],
        [1, "Aditya", 22],
        [3, "Karan", 20]
    ]


def test_limit(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])
    users_table.insert([3, "Karan", 20])

    result = users_table.select(limit=2)

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_order_by_and_limit(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])
    users_table.insert([3, "Karan", 20])

    result = users_table.select(
        order_by="age",
        descending=True,
        limit=2
    )

    assert result == [
        [2, "Rahul", 25],
        [1, "Aditya", 22]
    ]


def test_negative_limit(users_table):
    with pytest.raises(ValueError):
        users_table.select(limit=-1)


def test_invalid_order_by_column(users_table):
    with pytest.raises(ValueError):
        users_table.select(order_by="salary")


def test_update_matching_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])

    condition = Condition("name", "=", "Aditya")

    affected = users_table.update(
        {"age": 23},
        condition
    )

    assert affected == 1

    assert users_table.rows == [
        [1, "Aditya", 23],
        [2, "Rahul", 25]
    ]


def test_update_all_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])

    affected = users_table.update({"age": 30})

    assert affected == 2

    assert users_table.rows == [
        [1, "Aditya", 30],
        [2, "Rahul", 30]
    ]


def test_update_multiple_columns(users_table):
    users_table.insert([1, "Aditya", 22])

    affected = users_table.update({
        "name": "Aditi",
        "age": 23
    })

    assert affected == 1

    assert users_table.rows == [
        [1, "Aditi", 23]
    ]


def test_update_invalid_type(users_table):
    users_table.insert([1, "Aditya", 22])

    with pytest.raises(TypeError):
        users_table.update({"age": "twenty"})


def test_update_invalid_column(users_table):
    users_table.insert([1, "Aditya", 22])

    with pytest.raises(ValueError):
        users_table.update({"salary": 50000})


def test_delete_matching_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])
    users_table.insert([3, "Karan", 20])

    condition = Condition("age", "<", 21)

    affected = users_table.delete(condition)

    assert affected == 1

    assert users_table.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_delete_all_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])

    affected = users_table.delete()

    assert affected == 2
    assert users_table.rows == []


def test_delete_no_matching_rows(users_table):
    users_table.insert([1, "Aditya", 22])
    users_table.insert([2, "Rahul", 25])

    condition = Condition("age", ">", 100)

    affected = users_table.delete(condition)

    assert affected == 0

    assert users_table.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25
    ]
    ]


def test_delete_invalid_column(users_table):
    users_table.insert([1, "Aditya", 22])

    condition = Condition("salary", ">", 50000)

    with pytest.raises(ValueError):
        users_table.delete(condition)


def test_not_null_metadata_persists(tmp_path):
    """
    Verify that a NOT NULL column remains NOT NULL
    after the database is saved and loaded again.
    """
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    db.create_table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT", True)
        ]
    )

    db.save()

    new_db = Database(db_file)

    table = new_db.get_table("users")

    assert table.columns[0].nullable is False
    assert table.columns[1].nullable is True


def test_not_null_constraint_survives_reload(tmp_path):
    """
    Verify that a NOT NULL constraint is still enforced
    after the database is reloaded from disk.
    """
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    table = db.create_table(
        "users",
        [
            ("id", "INT", False),
            ("name", "TEXT")
        ]
    )

    table.insert([1, "Aditya"])

    db.save()

    new_db = Database(db_file)

    reloaded_table = new_db.get_table("users")

    with pytest.raises(TypeError):
        reloaded_table.insert([None, "Rahul"])