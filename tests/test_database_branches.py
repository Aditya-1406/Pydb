from pydb.database import Database


def test_create_branch_from_current_version(tmp_path):
    """
    Database should expose branch creation through the
    HistoryManager.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.create_branch(
        "experiment"
    )

    assert db.get_branches() == {
        "main": 1,
        "experiment": 1
    }

    assert (
        db.get_current_branch()
        == "main"
    )


def test_create_branch_from_explicit_version(tmp_path):
    """
    A branch can be created from a specific historical version.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    db.create_branch(
        "experiment",
        from_version_id=1
    )

    assert (
        db.get_branch_head("experiment")
        == 1
    )

    assert (
        db.get_branch_head("main")
        == 3
    )


def test_switch_branch_restores_branch_state(tmp_path):
    """
    Switching branches should restore the state stored at the
    branch's head version.
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

    # Create experiment from V1.
    db.create_branch(
        "experiment",
        from_version_id=1
    )

    db.switch_branch(
        "experiment"
    )

    assert (
        db.get_current_branch()
        == "experiment"
    )

    assert (
        db.get_current_version().version_id
        == 1
    )

    assert (
        db.get_table("users").rows
        == []
    )


def test_new_mutation_uses_active_branch(tmp_path):
    """
    A mutation made after switching branches should create its
    version on that branch.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2 on main
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # Create experiment from V1.
    db.create_branch(
        "experiment",
        from_version_id=1
    )

    # Switch to experiment.
    db.switch_branch(
        "experiment"
    )

    # V3 on experiment.
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    current_version = (
        db.get_current_version()
    )

    assert (
        current_version.branch_name
        == "experiment"
    )

    assert (
        current_version.parent_version_id
        == 1
    )

    assert (
        db.get_branch_head("experiment")
        == current_version.version_id
    )

    assert (
        db.get_branch_head("main")
        == 2
    )


def test_main_and_experiment_have_independent_heads(tmp_path):
    """
    Advancing one branch should not move the other branch's head.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    # V1
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

    # Advance experiment.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    # Switch back to main.
    db.switch_branch(
        "main"
    )

    assert (
        db.get_branch_head("main")
        == 2
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    assert (
        db.get_current_branch()
        == "main"
    )

    assert (
        db.get_current_version().version_id
        == 2
    )

    # Main should contain only its own row.
    assert (
        db.get_table("users").rows
        == [[1, "Aditya"]]
    )


def test_branch_metadata_persists_across_restart(tmp_path):
    """
    Branch information and the active branch should survive
    database restart.
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

    db.create_branch(
        "experiment",
        from_version_id=1
    )

    db.switch_branch(
        "experiment"
    )

    # V2 experiment
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.save()

    restarted_db = Database(
        file_path=file_path
    )

    assert restarted_db.get_branches() == {
        "main": 1,
        "experiment": 2
    }

    assert (
        restarted_db.get_current_branch()
        == "experiment"
    )

    assert (
        restarted_db.get_current_version().version_id
        == 2
    )

    assert (
        restarted_db.get_table("users").rows
        == [[1, "Aditya"]]
    )


def test_duplicate_branch_is_rejected(tmp_path):
    """
    Creating a branch with an existing name should fail.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.create_branch(
        "experiment"
    )

    try:
        db.create_branch(
            "experiment"
        )
        assert False
    except ValueError as exc:
        assert (
            "Branch 'experiment' already exists"
            in str(exc)
        )


def test_switching_to_unknown_branch_is_rejected(tmp_path):
    """
    Switching to a branch that does not exist should fail.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    try:
        db.switch_branch(
            "experiment"
        )
        assert False
    except ValueError as exc:
        assert (
            "Branch 'experiment' does not exist"
            in str(exc)
        )


def test_branch_creation_blocked_during_transaction(tmp_path):
    """
    Branch creation should not be allowed during a transaction.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.begin()

    try:
        db.create_branch(
            "experiment"
        )
        assert False
    except RuntimeError as exc:
        assert (
            "Cannot create a branch during an active transaction"
            in str(exc)
        )


def test_branch_switch_blocked_during_transaction(tmp_path):
    """
    Branch switching should not be allowed during a transaction.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.begin()

    try:
        db.switch_branch(
            "main"
        )
        assert False
    except RuntimeError as exc:
        assert (
            "Cannot switch branches during an active transaction"
            in str(exc)
        )