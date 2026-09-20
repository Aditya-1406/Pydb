from copy import deepcopy

from pydb.database import Database


def test_branch_head_state_is_immutable_after_later_commit(
    tmp_path
):
    """
    A branch head version must remain unchanged after a later commit
    is created on that same branch.
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
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    branch_head = (
        db.get_branch_head("main")
    )

    head_version = (
        db.history.get_version(
            branch_head
        )
    )

    state_before = deepcopy(
        head_version.state
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    assert (
        db.get_branch_head("main")
        != branch_head
    )

    assert (
        head_version.state
        == state_before
    )

    assert head_version.state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Aditya"]
    ]


def test_branch_head_does_not_move_when_another_branch_changes(
    tmp_path
):
    """
    A branch's head must remain fixed while another branch evolves.
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

    main_head_before = (
        db.get_branch_head("main")
    )

    main_state_before = deepcopy(
        db.history
        .get_version(main_head_before)
        .state
    )

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    assert (
        experiment_head
        != main_head_before
    )

    assert (
        db.get_branch_head("main")
        == main_head_before
    )

    assert (
        db.history
        .get_version(main_head_before)
        .state
        == main_state_before
    )

    assert db.history.get_version(
        main_head_before
    ).state[
        "tables"
    ]["users"]["rows"] == [
        [1, "Base"]
    ]


def test_checkout_does_not_move_branch_head(
    tmp_path
):
    """
    Checking out an older version changes the active historical
    position but must not rewrite the branch head.
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
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    branch_head = (
        db.get_branch_head("main")
    )

    assert (
        branch_head
        == db.get_current_version().version_id
    )

    db.checkout(2)

    assert (
        db.get_current_version().version_id
        == 2
    )

    assert (
        db.get_branch_head("main")
        == branch_head
    )

    assert db.get_table(
        "users"
    ).rows == [
        [1, "Aditya"]
    ]


def test_conflicted_merge_preserves_both_branch_heads(
    tmp_path
):
    """
    A conflicted merge must not move either branch head.
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
        "INSERT INTO users VALUES (1, 'Aditya');"
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

    history_count_before = len(
        db.get_history()
    )

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "CONFLICT"
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
        db.get_current_version().version_id
        == main_head
    )

    assert db.get_table(
        "users"
    ).rows == [
        [1, "Main"]
    ]


def test_successful_merge_moves_only_target_branch_head(
    tmp_path
):
    """
    A successful merge must advance only the target branch head.

    The source branch head must remain exactly where it was before
    the merge.
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

    # Main branch.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    main_head_before = (
        db.get_branch_head("main")
    )

    # Experiment branch.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head("experiment")
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

    merge_version_id = (
        result["merged_version"]
    )

    assert (
        db.get_branch_head("main")
        == merge_version_id
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    assert (
        merge_version_id
        != main_head_before
    )

    merge_version = (
        db.history.get_version(
            merge_version_id
        )
    )

    assert (
        merge_version.parent_version_id
        == main_head_before
    )

    assert (
        merge_version.merge_parent_version_id
        == experiment_head
    )