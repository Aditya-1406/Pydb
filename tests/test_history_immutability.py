from pydb.database import Database


def test_historical_version_is_immutable_after_insert(
    tmp_path
):
    """
    A historical version must not change when the live database
    receives a later INSERT.
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

    # Capture the V2 historical version.
    version_2 = db.history.get_version(
        2
    )

    # Create a later live mutation.
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    # V2 must still contain only the original row.
    assert version_2.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Aditya"]
    ]


def test_historical_version_is_immutable_after_update(
    tmp_path
):
    """
    A historical version must not change when the live database
    receives a later UPDATE.
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

    # Capture the V2 historical version.
    version_2 = db.history.get_version(
        2
    )

    # Modify the live database after V2.
    db.execute(
        "UPDATE users "
        "SET name = 'Updated' "
        "WHERE id = 1;"
    )

    # V2 must retain its original value.
    assert version_2.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Aditya"]
    ]


def test_historical_version_is_immutable_after_delete(
    tmp_path
):
    """
    A historical version must retain its original row after a later
    DELETE.
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

    # Capture the V2 historical version.
    version_2 = db.history.get_version(
        2
    )

    # Delete the row from the live database.
    db.execute(
        "DELETE FROM users WHERE id = 1;"
    )

    # V2 must still contain the original row.
    assert version_2.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Aditya"]
    ]


def test_branch_history_keeps_common_ancestor_immutable(
    tmp_path
):
    """
    After branching, both branches must continue to reference
    the same unchanged ancestor state.

    Each branch must then evolve independently without modifying
    the common ancestor.
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

    # Capture the common ancestor.
    ancestor = db.history.get_version(
        2
    )

    # Create experiment from V2.
    db.create_branch(
        "experiment"
    )

    # Modify main.
    db.execute(
        "UPDATE users "
        "SET name = 'Main' "
        "WHERE id = 1;"
    )

    main_version = (
        db.get_current_version()
    )

    # Switch to experiment.
    db.switch_branch(
        "experiment"
    )

    # Modify experiment independently.
    db.execute(
        "UPDATE users "
        "SET name = 'Experiment' "
        "WHERE id = 1;"
    )

    experiment_version = (
        db.get_current_version()
    )

    # --------------------------------------------------
    # The common ancestor must remain unchanged.
    # --------------------------------------------------

    assert ancestor.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Aditya"]
    ]

    # --------------------------------------------------
    # Main must retain its own branch state.
    # --------------------------------------------------

    assert main_version.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Main"]
    ]

    # --------------------------------------------------
    # Experiment must retain its own branch state.
    # --------------------------------------------------

    assert experiment_version.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Experiment"]
    ]