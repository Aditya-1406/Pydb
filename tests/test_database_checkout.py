from pydb.database import Database


def test_checkout_restores_historical_database_state(tmp_path):
    """
    Checkout should restore the database to a previous version.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # V3
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    assert (
        db.get_current_version().version_id
        == 3
    )

    # Restore the state immediately after CREATE TABLE.
    db.checkout(1)

    table = db.get_table(
        "users"
    )

    assert table.rows == []

    assert (
        db.get_current_version().version_id
        == 1
    )


def test_checkout_does_not_delete_history(tmp_path):
    """
    Checkout should change the active database state without
    deleting newer historical versions.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # V3
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    db.checkout(1)

    history = db.get_history()

    assert [
        version.version_id
        for version in history
    ] == [
        0,
        1,
        2,
        3
    ]


def test_checkout_persists_across_restart(tmp_path):
    """
    A checked-out database state should survive a restart.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # V3
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    db.checkout(1)

    db.save()

    restarted_db = Database(
        file_path=file_path
    )

    table = restarted_db.get_table(
        "users"
    )

    assert table.rows == []

    assert (
        restarted_db.get_current_version().version_id
        == 1
    )


def test_checkout_invalid_version(tmp_path):
    """
    Checkout should fail when the requested version does not exist.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    try:
        db.checkout(99)
        assert False
    except ValueError as exc:
        assert (
            "Version '99' does not exist"
            in str(exc)
        )


def test_checkout_rejects_non_integer_version(tmp_path):
    """
    Checkout should require an integer version ID.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    try:
        db.checkout("abc")
        assert False
    except ValueError as exc:
        assert (
            "Version ID must be an integer"
            in str(exc)
        )


def test_checkout_blocked_during_transaction(tmp_path):
    """
    Checkout should not be allowed while a transaction is active.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.begin()

    try:
        db.checkout(0)
        assert False
    except RuntimeError as exc:
        assert (
            "Cannot checkout during an active transaction"
            in str(exc)
        )