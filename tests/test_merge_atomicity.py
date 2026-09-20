from copy import deepcopy

from pydb.database import Database


def test_row_conflict_is_fully_atomic(
    tmp_path
):
    """
    A row conflict must not partially modify the target database
    or create a history version.
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

    # Main changes the shared row.
    db.execute(
        "UPDATE users "
        "SET name = 'Main' "
        "WHERE id = 1;"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment changes the same shared row differently.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "UPDATE users "
        "SET name = 'Experiment' "
        "WHERE id = 1;"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    db.switch_branch(
        "main"
    )

    rows_before = deepcopy(
        db.get_table("users").rows
    )

    record_ids_before = deepcopy(
        db.get_table("users").record_ids
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    history_count_before = len(
        db.get_history()
    )

    dirty_before = db.dirty

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "CONFLICT"
    )

    # ----------------------------------------------
    # Live state must remain unchanged.
    # ----------------------------------------------

    assert (
        db.get_table("users").rows
        == rows_before
    )

    assert (
        db.get_table("users").record_ids
        == record_ids_before
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    # ----------------------------------------------
    # Branch heads must remain unchanged.
    # ----------------------------------------------

    assert (
        db.get_branch_head("main")
        == main_head
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    # ----------------------------------------------
    # History must remain unchanged.
    # ----------------------------------------------

    assert (
        len(db.get_history())
        == history_count_before
    )

    # Dirty state must not be modified by conflict detection.
    assert (
        db.dirty
        == dirty_before
    )


def test_primary_key_conflict_is_fully_atomic(
    tmp_path
):
    """
    A logical primary-key conflict must leave the target database
    completely untouched.
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

    db.create_branch(
        "experiment"
    )

    # Main inserts primary-key value 1.
    db.execute(
        "INSERT INTO users VALUES (1, 'Main');"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment independently inserts the same primary key.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    db.switch_branch(
        "main"
    )

    rows_before = deepcopy(
        db.get_table("users").rows
    )

    ids_before = deepcopy(
        db.get_table("users").record_ids
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    history_count_before = len(
        db.get_history()
    )

    dirty_before = db.dirty

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "CONFLICT"
    )

    assert any(
        conflict["type"]
        == "constraint_conflict"
        for conflict
        in result["conflicts"]
    )

    assert (
        db.get_table("users").rows
        == rows_before
    )

    assert (
        db.get_table("users").record_ids
        == ids_before
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    assert (
        db.get_branch_head("main")
        == main_head
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    assert (
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )


def test_table_conflict_is_fully_atomic(
    tmp_path
):
    """
    A conflicting independently-created table must not partially
    alter the target database.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.create_branch(
        "experiment"
    )

    # Main creates users(id INT).
    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment creates users(name TEXT).
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "CREATE TABLE users "
        "(name TEXT);"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    db.switch_branch(
        "main"
    )

    table_before = deepcopy(
        db.get_table("users").to_dict()
    )

    history_count_before = len(
        db.get_history()
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    dirty_before = db.dirty

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "CONFLICT"
    )

    assert (
        result["conflicts"][0]["type"]
        == "table_add_conflict"
    )

    # Main table must remain exactly the same.
    assert (
        db.get_table("users").to_dict()
        == table_before
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    assert (
        db.get_branch_head("main")
        == main_head
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    assert (
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )


def test_index_conflict_is_fully_atomic(
    tmp_path
):
    """
    A conflicting index definition must not alter the target table
    or history.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT, salary INT);"
    )

    db.create_branch(
        "experiment"
    )

    # Main creates HASH index.
    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING HASH;"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment creates BTREE index with same name.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING BTREE;"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    db.switch_branch(
        "main"
    )

    indexes_before = deepcopy(
        db.get_table("users").to_dict()
    )

    history_count_before = len(
        db.get_history()
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    dirty_before = db.dirty

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "CONFLICT"
    )

    assert (
        result["conflicts"][0]["type"]
        == "index_conflict"
    )

    assert (
        db.get_table("users").to_dict()
        == indexes_before
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    assert (
        db.get_branch_head("main")
        == main_head
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    assert (
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )


def test_unknown_source_branch_does_not_change_state(
    tmp_path
):
    """
    Attempting to merge an unknown source branch must fail without
    modifying any database state.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    main_head = (
        db.get_branch_head("main")
    )

    rows_before = deepcopy(
        db.get_table("users").rows
    )

    history_count_before = len(
        db.get_history()
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    dirty_before = db.dirty

    try:
        db.merge_branch(
            "unknown"
        )
        assert False
    except ValueError as exc:
        assert (
            str(exc)
            == "Branch 'unknown' does not exist"
        )

    assert (
        db.get_branch_head("main")
        == main_head
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
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )


def test_self_merge_does_not_change_state(
    tmp_path
):
    """
    Attempting to merge a branch into itself must fail without
    modifying the database or history.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    main_head = (
        db.get_branch_head("main")
    )

    rows_before = deepcopy(
        db.get_table("users").rows
    )

    history_count_before = len(
        db.get_history()
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    dirty_before = db.dirty

    try:
        db.merge_branch(
            "main"
        )
        assert False
    except ValueError as exc:
        assert (
            str(exc)
            == "Cannot merge a branch into itself"
        )

    assert (
        db.get_branch_head("main")
        == main_head
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
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )