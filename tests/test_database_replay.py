from pydb.database import Database


def test_replay_reexecutes_historical_sql(tmp_path):
    """
    Replay should execute the SQL stored in a historical version
    against the current database state.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    assert db.get_current_version().version_id == 2

    replay_result = db.replay(2)

    assert (
        replay_result["source_version_id"]
        == 2
    )

    assert (
        replay_result["new_version_id"]
        == 3
    )

    rows = db.execute(
        "SELECT * FROM users;"
    )

    assert rows == [
        [1, "Aditya"],
        [1, "Aditya"]
    ]


def test_replay_stores_sql_on_new_version(tmp_path):
    """
    The replayed mutation should itself become a normal version
    containing the executed SQL.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    source_version = (
        db.get_history()[2]
    )

    db.replay(2)

    replayed_version = (
        db.get_current_version()
    )

    assert (
        replayed_version.version_id
        == 3
    )

    assert (
        replayed_version.sql
        == source_version.sql
    )


def test_replay_works_across_branches(tmp_path):
    """
    Replay should execute historical SQL against the current
    branch rather than restoring the source branch's state.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1 main
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2 main
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # Create experiment from V1.
    db.create_branch(
        "experiment",
        from_version_id=1
    )

    db.switch_branch(
        "experiment"
    )

    assert (
        db.get_current_version().version_id
        == 1
    )

    # Replay V2's INSERT into experiment.
    replay_result = db.replay(2)

    assert (
        replay_result["source_version_id"]
        == 2
    )

    new_version_id = (
        replay_result["new_version_id"]
    )

    new_version = (
        db.get_current_version()
    )

    assert (
        new_version.version_id
        == new_version_id
    )

    assert (
        new_version.parent_version_id
        == 1
    )

    assert (
        new_version.branch_name
        == "experiment"
    )

    assert (
        db.get_table("users").rows
        == [[1, "Aditya"]]
    )


def test_replay_version_zero_is_rejected(tmp_path):
    """
    Version 0 represents initial state and has no SQL to replay.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.replay(0)
        assert False
    except ValueError as exc:
        assert (
            "Version '0' does not contain replayable SQL"
            in str(exc)
        )


def test_replay_transaction_commit_version_is_rejected(tmp_path):
    """
    A transaction commit version represents multiple statements,
    so it is not replayable through the single-SQL replay mechanism.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.begin()

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute(
        "UPDATE users SET name = 'Garg' WHERE id = 1;"
    )

    db.commit()

    current_version = (
        db.get_current_version()
    )

    assert (
        current_version.sql
        is None
    )

    try:
        db.replay(
            current_version.version_id
        )
        assert False
    except ValueError as exc:
        assert (
            f"Version '{current_version.version_id}' "
            f"does not contain replayable SQL"
            in str(exc)
        )


def test_replay_unknown_version_is_rejected(tmp_path):
    """
    Replay should fail for an unknown version.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.replay(99)
        assert False
    except ValueError as exc:
        assert (
            "Version '99' does not exist"
            in str(exc)
        )


def test_replay_rejects_non_integer_version(tmp_path):
    """
    Replay should require an integer version ID.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.replay("abc")
        assert False
    except ValueError as exc:
        assert (
            "Version ID must be an integer"
            in str(exc)
        )


def test_replay_failed_sql_does_not_create_new_version(tmp_path):
    """
    When replayed SQL fails, no new historical version should
    be created.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT PRIMARY KEY, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    version_count_before = len(
        db.get_history()
    )

    # Replaying the same INSERT violates the primary key.
    try:
        db.replay(2)
        assert False
    except ValueError:
        pass

    assert (
        len(db.get_history())
        == version_count_before
    )