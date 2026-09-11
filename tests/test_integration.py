from pydb.database import Database


def test_insert_select_update_delete_pipeline(tmp_path):
    """
    Verify that INSERT, SELECT, UPDATE, and DELETE
    work together through the complete SQL execution pipeline.
    """

    database_file = tmp_path / "test_db.json"

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

    # INSERT through SQL.
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya', 22);"
    )

    # SELECT through SQL.
    rows = db.execute(
        "SELECT * FROM users;"
    )

    assert rows == [
        [1, "Aditya", 22]
    ]

    # UPDATE through SQL.
    affected_rows = db.execute(
        "UPDATE users SET age = 23 WHERE name = 'Aditya';"
    )

    assert affected_rows == 1

    # Verify UPDATE.
    rows = db.execute(
        "SELECT * FROM users;"
    )

    assert rows == [
        [1, "Aditya", 23]
    ]

    # DELETE through SQL.
    affected_rows = db.execute(
        "DELETE FROM users WHERE age = 23;"
    )

    assert affected_rows == 1

    # Verify DELETE.
    rows = db.execute(
        "SELECT * FROM users;"
    )

    assert rows == []