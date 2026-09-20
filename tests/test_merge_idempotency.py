from pydb.database import Database


def test_repeated_merge_does_not_create_duplicate_version(
    tmp_path
):
    """
    Once a source branch has been successfully merged, merging the
    same source again should return UP_TO_DATE and must not create
    another merge commit.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    # Main branch changes.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    # Experiment branch changes.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment');"
    )

    source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert (
        first_merge["status"]
        == "MERGED"
    )

    first_merge_version = (
        first_merge["merged_version"]
    )

    history_count = len(
        db.get_history()
    )

    # Repeat the same merge.
    second_merge = db.merge_branch(
        "experiment"
    )

    assert (
        second_merge["status"]
        == "UP_TO_DATE"
    )

    assert (
        second_merge["source_version"]
        == source_head
    )

    assert (
        second_merge["merged_version"]
        == first_merge_version
    )

    assert (
        len(db.get_history())
        == history_count
    )

    assert (
        db.get_branch_head("main")
        == first_merge_version
    )

    assert (
        db.get_branch_head("experiment")
        == source_head
    )


def test_repeated_merge_after_restart_is_up_to_date(
    tmp_path
):
    """
    Idempotent merge behavior must survive a database restart.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    # Main branch.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    # Experiment branch.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment');"
    )

    source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert (
        first_merge["status"]
        == "MERGED"
    )

    merge_version = (
        first_merge["merged_version"]
    )

    db.save()

    # Restart PyDB.
    restarted = Database(
        file_path=file_path
    )

    history_count = len(
        restarted.get_history()
    )

    second_merge = (
        restarted.merge_branch(
            "experiment"
        )
    )

    assert (
        second_merge["status"]
        == "UP_TO_DATE"
    )

    assert (
        second_merge["source_version"]
        == source_head
    )

    assert (
        second_merge["merged_version"]
        == merge_version
    )

    assert (
        len(restarted.get_history())
        == history_count
    )


def test_successful_merge_is_not_reported_as_up_to_date_before_merge(
    tmp_path
):
    """
    Two genuinely diverged branches must produce a new merge commit
    the first time they are merged.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    # Main diverges.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment diverges.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "MERGED"
    )

    assert (
        result["target_version"]
        == main_head
    )

    assert (
        result["source_version"]
        == experiment_head
    )

    assert (
        result["merged_version"]
        != main_head
    )

    assert (
        result["merged_version"]
        != experiment_head
    )


def test_merge_up_to_date_does_not_change_database_state(
    tmp_path
):
    """
    An UP_TO_DATE merge must leave the live database exactly as it
    was before the call.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert (
        first_merge["status"]
        == "MERGED"
    )

    rows_before = (
        db.get_table("users").rows.copy()
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    main_head_before = (
        db.get_branch_head("main")
    )

    experiment_head_before = (
        db.get_branch_head("experiment")
    )

    history_count_before = len(
        db.get_history()
    )

    second_merge = db.merge_branch(
        "experiment"
    )

    assert (
        second_merge["status"]
        == "UP_TO_DATE"
    )

    assert (
        db.get_table("users").rows
        == rows_before
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    assert (
        db.get_branch_head("main")
        == main_head_before
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head_before
    )

    assert (
        len(db.get_history())
        == history_count_before
    )


def test_source_branch_can_continue_after_merge(
    tmp_path
):
    """
    A source branch remains independent after being merged.

    New commits on the source branch should create new source
    versions, which can then be merged again later.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    # Experiment's first change.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    first_source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert (
        first_merge["status"]
        == "MERGED"
    )

    # The experiment branch can now continue independently.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment Later');"
    )

    second_source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    assert (
        second_source_head
        != first_source_head
    )

    # Return to main and merge the new source work.
    db.switch_branch(
        "main"
    )

    second_merge = db.merge_branch(
        "experiment"
    )

    assert (
        second_merge["status"]
        == "MERGED"
    )

    assert (
        second_merge["source_version"]
        == second_source_head
    )

    assert (
        second_merge["target_version"]
        == first_merge["merged_version"]
    )

    # Verify logical rows, not internal Record ID ordering.
    rows = (
        db.get_table("users").rows
    )

    assert {
        tuple(row)
        for row in rows
    } == {
        (1, "Base"),
        (2, "Experiment"),
        (3, "Experiment Later")
    }