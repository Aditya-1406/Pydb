from pydb.database import Database


def test_conflict_free_merge_combines_rows(tmp_path):
    """
    Independent row additions should merge successfully.
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

    # V2 main
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # Create experiment from V2.
    db.create_branch(
        "experiment"
    )

    # V3 experiment
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    # Switch back to main V2.
    db.switch_branch(
        "main"
    )

    # V4 main.
    db.execute(
        "INSERT INTO users VALUES (3, 'Neha');"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result[
        "status"
    ] == "MERGED"

    assert (
        result[
            "ancestor_version"
        ]
        == 2
    )

    assert (
        result[
            "target_version"
        ]
        == main_head
    )

    assert (
        result[
            "source_version"
        ]
        == experiment_head
    )

    merged_version = (
        db.get_current_version()
    )

    assert (
        merged_version.parent_version_id
        == main_head
    )

    assert (
        merged_version.merge_parent_version_id
        == experiment_head
    )

    assert (
        merged_version.branch_name
        == "main"
    )

    assert (
        db.get_table("users").rows
        == [
            [1, "Aditya"],
            [2, "Ravi"],
            [3, "Neha"]
        ]
    )


def test_merge_conflict_does_not_modify_database(
    tmp_path
):
    """
    Conflicting changes should leave the active database and
    history untouched.
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

    # Create experiment from V2.
    db.create_branch(
        "experiment"
    )

    # Change main.
    db.execute(
        "UPDATE users "
        "SET name = 'Main' "
        "WHERE id = 1;"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Change experiment from V2.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "UPDATE users "
        "SET name = 'Experiment' "
        "WHERE id = 1;"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    # Return to main.
    db.switch_branch(
        "main"
    )

    history_count_before = len(
        db.get_history()
    )

    rows_before = (
        db.get_table("users").rows.copy()
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result[
        "status"
    ] == "CONFLICT"

    assert (
        result[
            "target_version"
        ]
        == main_head
    )

    assert (
        result[
            "source_version"
        ]
        == experiment_head
    )

    assert (
        result[
            "merged_version"
        ]
        is None
    )

    assert len(
        result["conflicts"]
    ) == 1

    conflict = result[
        "conflicts"
    ][0]

    assert conflict[
        "type"
    ] == "row_conflict"

    assert conflict[
        "table"
    ] == "users"

    assert conflict[
        "record_id"
    ] == 1

    assert conflict[
        "target"
    ] == [1, "Main"]

    assert conflict[
        "source"
    ] == [1, "Experiment"]

    assert (
        db.get_table("users").rows
        == rows_before
    )

    assert (
        len(db.get_history())
        == history_count_before
    )


def test_merge_preserves_source_branch_head(
    tmp_path
):
    """
    Merging into main should not move the source branch head.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    db.create_branch(
        "experiment"
    )

    source_head_before = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    # The INSERT happened on main because create_branch does
    # not automatically switch branches.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2);"
    )

    source_head_before_merge = (
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
        db.get_branch_head("experiment")
        == source_head_before_merge
    )

    assert (
        source_head_before
        != source_head_before_merge
    )


def test_merge_unknown_branch_rejected(
    tmp_path
):
    """
    Merging an unknown source branch should fail.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.merge_branch(
            "experiment"
        )
        assert False
    except ValueError as exc:
        assert (
            "Branch 'experiment' does not exist"
            in str(exc)
        )


def test_merge_branch_into_itself_rejected(
    tmp_path
):
    """
    A branch cannot be merged into itself.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.merge_branch(
            "main"
        )
        assert False
    except ValueError as exc:
        assert (
            "Cannot merge a branch into itself"
            in str(exc)
        )


def test_merge_blocked_during_transaction(
    tmp_path
):
    """
    Merge should be blocked while a transaction is active.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.create_branch(
        "experiment"
    )

    db.begin()

    try:
        db.merge_branch(
            "experiment"
        )
        assert False
    except RuntimeError as exc:
        assert (
            "Cannot merge during an active transaction"
            in str(exc)
        )

def test_merge_requires_target_branch_head(
    tmp_path
):
    """
    A merge must start from the current branch head rather than
    from an arbitrary checked-out historical version.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    db.create_branch(
        "experiment",
        from_version_id=1
    )

    db.checkout(1)

    try:
        db.merge_branch(
            "experiment"
        )
        assert False
    except RuntimeError as exc:
        assert (
            "Current branch is not at its head"
            in str(exc)
        )


def test_merge_persists_two_parents(
    tmp_path
):
    """
    A successful merge should persist both parent references
    across restart.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    db.create_branch(
        "experiment"
    )

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2);"
    )

    source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    db.execute(
        "INSERT INTO users VALUES (3);"
    )

    target_head = (
        db.get_branch_head(
            "main"
        )
    )

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "MERGED"
    )

    merged_version_id = (
        result["merged_version"]
    )

    db.save()

    restarted = Database(
        file_path=file_path
    )

    merged = restarted.history.get_version(
        merged_version_id
    )

    assert (
        merged.parent_version_id
        == target_head
    )

    assert (
        merged.merge_parent_version_id
        == source_head
    )