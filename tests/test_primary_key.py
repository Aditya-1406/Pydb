from pydb.table import Table
from pydb.condition import Condition
from pydb.database import Database


def test_primary_key_is_stored():
    """
    Verify that a table stores its primary-key column name.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    assert table.primary_key == "id"


def test_primary_key_must_exist():
    """
    Verify that the primary key must reference an existing column.
    """
    try:
        Table(
            "users",
            [
                ("id", "INT"),
                ("name", "TEXT")
            ],
            primary_key="user_id"
        )
        assert False
    except ValueError:
        assert True


def test_primary_key_must_be_unique():
    """
    Verify that duplicate primary-key values are rejected.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    table.insert([1, "Aditya"])

    try:
        table.insert([1, "Rahul"])
        assert False
    except ValueError:
        assert True


def test_different_primary_keys_are_allowed():
    """
    Verify that rows with different primary-key values
    can be inserted.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    table.insert([1, "Aditya"])
    table.insert([2, "Rahul"])

    assert table.rows == [
        [1, "Aditya"],
        [2, "Rahul"]
    ]


def test_update_cannot_create_duplicate_primary_key():
    """
    Verify that updating a primary key to an existing value
    is rejected.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    table.insert([1, "Aditya"])
    table.insert([2, "Rahul"])

    condition = Condition("id", "=", 1)

    try:
        table.update(
            {"id": 2},
            condition
        )
        assert False
    except ValueError:
        assert True


def test_update_can_change_primary_key_to_unused_value():
    """
    Verify that a primary key can be changed when the new
    value does not already exist.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    table.insert([1, "Aditya"])
    table.insert([2, "Rahul"])

    condition = Condition("id", "=", 1)

    affected_rows = table.update(
        {"id": 3},
        condition
    )

    assert affected_rows == 1

    assert table.rows == [
        [3, "Aditya"],
        [2, "Rahul"]
    ]


def test_primary_key_persists_after_database_restart(tmp_path):
    """
    Verify that primary-key metadata survives saving the database
    and creating a new Database instance.
    """
    database_file = tmp_path / "test_db.json"

    db = Database(database_file)

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.save()

    new_db = Database(database_file)

    table = new_db.get_table("users")

    assert table.primary_key == "id"


def test_primary_key_constraint_survives_database_restart(tmp_path):
    """
    Verify that the restored table still rejects duplicate
    primary-key values after a database restart.
    """
    database_file = tmp_path / "test_db.json"

    db = Database(database_file)

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.save()

    new_db = Database(database_file)

    try:
        new_db.execute(
            "INSERT INTO users VALUES (1, 'Rahul');"
        )
        assert False
    except ValueError:
        assert True