from pydb.database import Database


def test_merge_independent_rows_with_same_primary_key_conflicts(
    tmp_path
):
    """
    Independently inserted rows with the same primary-key value
    cannot coexist after a merge.

    Record IDs may differ between branches, but the primary key
    represents logical row identity and must remain unique.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT PRIMARY KEY, name TEXT);"
    )

    # Create experiment from the initial table state.
    db.create_branch(
        "experiment"
    )

    # Main branch inserts a row.
    db.execute(
        "INSERT INTO users VALUES (1, 'Main');"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Switch to experiment and independently insert the same
    # logical primary-key value.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    # Return to main and attempt the merge.
    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result["status"] == "CONFLICT"

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
        is None
    )

    assert any(
        conflict["type"]
        == "constraint_conflict"
        for conflict
        in result["conflicts"]
    )

    # Conflict must not modify the target database.
    assert db.get_table(
        "users"
    ).rows == [
        [1, "Main"]
    ]


def test_merge_identical_independent_rows_deduplicates(
    tmp_path
):
    """
    When both branches independently insert an identical row,
    the merge should keep one logical copy rather than creating
    a duplicate.
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

    # Create experiment from the empty table state.
    db.create_branch(
        "experiment"
    )

    # Main independently inserts the row.
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment independently inserts the identical row.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
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

    assert result["status"] == "MERGED"

    assert (
        result["target_version"]
        == main_head
    )

    assert (
        result["source_version"]
        == experiment_head
    )

    assert db.get_table(
        "users"
    ).rows == [
        [1, "Aditya"]
    ]


def test_merge_different_independent_rows_with_colliding_record_ids(
    tmp_path
):
    """
    Different independently inserted rows may receive the same
    internal Record ID on different branches.

    The source branch keeps the original internal Record ID and
    the target row is remapped to a fresh Record ID.

    Both logical rows must survive the merge.
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

    db.create_branch(
        "experiment"
    )

    # Main creates a row.
    db.execute(
        "INSERT INTO users VALUES (1, 'Main');"
    )

    main_table = db.get_table(
        "users"
    )

    assert main_table.record_ids == [
        1
    ]

    # Experiment starts from the same ancestor, so its first
    # independently inserted row also receives internal Record ID 1.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    experiment_table = db.get_table(
        "users"
    )

    assert experiment_table.record_ids == [
        1
    ]

    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result["status"] == "MERGED"

    merged_table = db.get_table(
        "users"
    )

    # Source keeps internal Record ID 1.
    # Target is remapped to internal Record ID 2.
    assert merged_table.record_ids == [
        1,
        2
    ]

    assert merged_table.rows == [
        [2, "Experiment"],
        [1, "Main"]
    ]

    # Verify the logical data independently of internal ordering.
    assert sorted(
        merged_table.rows,
        key=lambda row: row[0]
    ) == [
        [1, "Main"],
        [2, "Experiment"]
    ]

def test_merge_source_branch_remains_unchanged_after_success(
    tmp_path
):
    """
    A successful merge must not modify the source branch's
    historical state or branch head.
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

    db.create_branch(
        "experiment"
    )

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Experiment');"
    )

    source_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    source_state_before = (
        db.history
        .get_version(
            source_head
        )
        .state
    )

    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result["status"] == "MERGED"

    assert (
        db.get_branch_head(
            "experiment"
        )
        == source_head
    )

    source_state_after = (
        db.history
        .get_version(
            source_head
        )
        .state
    )

    assert (
        source_state_after
        == source_state_before
    )