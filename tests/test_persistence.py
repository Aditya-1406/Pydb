from pydb.database import Database


def test_table_persists_after_database_restart(tmp_path):
    """
    Verify that a table and its rows survive after the database
    is saved and a new Database instance is created.
    """

    database_file = tmp_path / "test_db.json"

    # Create the first database instance.
    db = Database(database_file)

    # Create a table.
    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    # Insert data.
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya', 22);"
    )

    # Save the database.
    db.save()

    # Create a completely new Database instance.
    new_db = Database(database_file)

    # Verify that the table was restored.
    assert "users" in new_db.list_tables()

    # Verify that the data was restored.
    rows = new_db.execute(
        "SELECT * FROM users;"
    )

    assert rows == [
        [1, "Aditya", 22]
    ]


def test_create_table_marks_database_dirty(tmp_path):
    """
    Verify that creating a table marks the database as dirty.
    """

    database_file = tmp_path / "test_db.json"

    db = Database(database_file)

    assert db.dirty is False

    db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    assert db.dirty is True


def test_drop_table_marks_database_dirty(tmp_path):
    """
    Verify that dropping a table marks the database as dirty.
    """

    database_file = tmp_path / "test_db.json"

    db = Database(database_file)

    db.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    db.save()

    assert db.dirty is False

    db.drop_table("users")

    assert db.dirty is True