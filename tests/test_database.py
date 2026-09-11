import pytest

from pydb.database import Database
from pydb.condition import Condition


def test_create_table():
    db = Database()

    table = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    assert table.name == "users"
    assert db.list_tables() == ["users"]


def test_create_multiple_tables():
    db = Database()

    db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    db.create_table(
        "products",
        [
            ("id", "INT"),
            ("price", "FLOAT")
        ]
    )

    assert db.list_tables() == ["users", "products"]


def test_duplicate_table():
    db = Database()

    db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    with pytest.raises(ValueError):
        db.create_table(
            "users",
            [
                ("id", "INT")
            ]
        )


def test_get_table():
    db = Database()

    created_table = db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    retrieved_table = db.get_table("users")

    assert retrieved_table is created_table


def test_get_nonexistent_table():
    db = Database()

    with pytest.raises(ValueError):
        db.get_table("users")


def test_drop_table():
    db = Database()

    db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    db.drop_table("users")

    assert db.list_tables() == []


def test_drop_nonexistent_table():
    db = Database()

    with pytest.raises(ValueError):
        db.drop_table("users")


def test_database_persistence(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 23])

    db.save()

    # Simulate restarting the database
    new_db = Database(db_file)

    assert new_db.list_tables() == ["users"]

    users = new_db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 23]
    ]


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


def test_update_persistence(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 25])

    db.save()

    # Update in memory
    affected = users.update(
        {"age": 23},
        Condition("name", "=", "Aditya")
    )

    assert affected == 1

    # Persist mutation
    db.save()

    # Simulate restart
    new_db = Database(db_file)

    assert new_db.get_table("users").rows == [
        [1, "Aditya", 23],
        [2, "Rahul", 25]
    ]


def test_delete_persistence(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 25])
    users.insert([3, "Karan", 20])

    db.save()

    affected = users.delete(
        Condition("age", "<", 21)
    )

    assert affected == 1

    db.save()

    new_db = Database(db_file)

    assert new_db.get_table("users").rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_mutation_requires_save(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    users.insert([1, "Aditya"])
    db.save()

    # Mutate only in memory
    users.update({"name": "Changed"})

    # Restart WITHOUT db.save()
    new_db = Database(db_file)

    assert new_db.get_table("users").rows == [
        [1, "Aditya"]
    ]


def test_database_starts_clean(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    assert db.dirty is False


def test_save_clears_dirty_flag(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    db.mark_dirty()

    assert db.dirty is True

    db.save()

    assert db.dirty is False


def test_mutation_marks_database_dirty(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    users.insert([1, "Aditya"])

    db.mark_dirty()

    assert db.dirty is True

    db.save()

    assert db.dirty is False


def test_rollback_update(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 25])

    db.save()

    db.begin()

    users = db.get_table("users")

    users.update(
        {"age": 30},
        Condition("name", "=", "Aditya")
    )

    db.mark_dirty()

    assert users.rows == [
        [1, "Aditya", 30],
        [2, "Rahul", 25]
    ]

    db.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_rollback_delete(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 25])
    users.insert([3, "Karan", 20])

    db.save()

    db.begin()

    users = db.get_table("users")

    users.delete(
        Condition("age", "<", 21)
    )

    db.mark_dirty()

    assert users.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]

    db.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25],
        [3, "Karan", 20]
    ]


def test_commit_persists_changes(tmp_path):
    db_file = tmp_path / "test_db.json"

    db = Database(db_file)

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])

    db.save()

    db.begin()

    users = db.get_table("users")

    users.update({"age": 23})

    db.mark_dirty()

    db.commit()

    new_db = Database(db_file)

    assert new_db.get_table("users").rows == [
        [1, "Aditya", 23]
    ]


def test_rollback_without_transaction(tmp_path):
    db = Database(tmp_path / "test_db.json")

    with pytest.raises(RuntimeError):
        db.rollback()


def test_commit_without_transaction(tmp_path):
    db = Database(tmp_path / "test_db.json")

    with pytest.raises(RuntimeError):
        db.commit()


def test_nested_transaction_not_allowed(tmp_path):
    db = Database(tmp_path / "test_db.json")

    db.begin()

    with pytest.raises(RuntimeError):
        db.begin()


def test_rollback_does_not_affect_original_data(tmp_path):
    """
    Verify that rollback restores the exact state from before
    the transaction started.
    """

    db = Database(tmp_path / "test.json")

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])

    # Start transaction and create a snapshot
    db.begin()

    # Modify the existing row
    users.update(
        {"age": 30},
        Condition("name", "=", "Aditya")
    )

    db.mark_dirty()

    # Undo the transaction
    db.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22]
    ]


def test_rollback_insert(tmp_path):
    """
    Verify that a row inserted during a transaction
    disappears after rollback.
    """

    db = Database(tmp_path / "test.json")

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])

    db.begin()

    # Insert a new row inside the transaction
    users.insert([2, "Rahul", 25])
    db.mark_dirty()

    # Undo the transaction
    db.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22]
    ]


def test_rollback_delete_again(tmp_path):
    """
    Verify that a deleted row is restored after rollback.
    """

    db = Database(tmp_path / "test.json")

    users = db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    users.insert([1, "Aditya", 22])
    users.insert([2, "Rahul", 25])

    db.begin()

    # Delete one row inside the transaction
    users.delete(
        Condition("name", "=", "Aditya")
    )

    db.mark_dirty()

    # Undo the transaction
    db.rollback()

    users = db.get_table("users")

    assert users.rows == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


# ============================================================
# NOT NULL integration tests
# ============================================================


def test_create_table_with_not_null_using_sql():
    """
    Verify that CREATE TABLE with NOT NULL creates a column
    with nullable=False through the complete SQL execution path.
    """
    db = Database()

    db.execute(
        "CREATE TABLE users ("
        "id INT NOT NULL, "
        "name TEXT"
        ");"
    )

    users = db.get_table("users")

    assert users.columns[0].name == "id"
    assert users.columns[0].data_type == "INT"
    assert users.columns[0].nullable is False

    assert users.columns[1].name == "name"
    assert users.columns[1].data_type == "TEXT"
    assert users.columns[1].nullable is True


def test_insert_null_into_not_null_column_fails():
    """
    Verify that INSERT rejects NULL for a NOT NULL column
    when executed through SQL.
    """
    db = Database()

    db.execute(
        "CREATE TABLE users ("
        "id INT NOT NULL, "
        "name TEXT"
        ");"
    )

    with pytest.raises(TypeError):
        db.execute(
            "INSERT INTO users VALUES (NULL, 'Aditya');"
        )


def test_insert_null_into_nullable_column_succeeds():
    """
    Verify that a column without NOT NULL continues to allow
    SQL NULL values.
    """
    db = Database()

    db.execute(
        "CREATE TABLE users ("
        "id INT, "
        "name TEXT"
        ");"
    )

    db.execute(
        "INSERT INTO users VALUES (NULL, 'Aditya');"
    )

    users = db.get_table("users")

    assert users.rows == [
        [None, "Aditya"]
    ]


def test_update_null_on_not_null_column_fails():
    """
    Verify that UPDATE rejects NULL when assigning it to a
    NOT NULL column through SQL.
    """
    db = Database()

    db.execute(
        "CREATE TABLE users ("
        "id INT NOT NULL, "
        "name TEXT"
        ");"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    with pytest.raises(TypeError):
        db.execute(
            "UPDATE users SET id = NULL;"
        )

    users = db.get_table("users")

    # The failed UPDATE must not replace the valid value.
    assert users.rows == [
        [1, "Aditya"]
    ]