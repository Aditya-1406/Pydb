from pydb.database import Database


def test_merge_is_blocked_inside_transaction_without_state_change(
    tmp_path
):
    """
    A merge attempted during an active transaction must fail before
    changing the database, history, branch heads, or transaction state.
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

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.switch_branch(
        "main"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    history_count_before = len(
        db.get_history()
    )

    rows_before = (
        db.get_table("users").rows.copy()
    )

    db.begin()

    try:
        db.merge_branch(
            "experiment"
        )
        assert False
    except RuntimeError as exc:
        assert (
            str(exc)
            == "Cannot merge during an active transaction"
        )

    # The transaction must still be active after the rejected merge.
    assert db._snapshot is not None

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
        db.get_table("users").rows
        == rows_before
    )

    # Clean up the transaction.
    db.rollback()

    assert db._snapshot is None


def test_transaction_commit_then_merge_creates_expected_history(
    tmp_path
):
    """
    A transaction should first create its single transaction-commit
    version. A subsequent merge should then create a separate
    two-parent version.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1
    db.execute(
        "CREATE TABLE users "
        "(id INT, name TEXT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 'Base');"
    )

    db.create_branch(
        "experiment"
    )

    # --------------------------------------------------
    # Main transaction.
    # --------------------------------------------------

    db.begin()

    db.execute(
        "INSERT INTO users VALUES (2, 'Main A');"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Main B');"
    )

    # No individual versions should appear while the transaction
    # is active.
    assert len(
        db.get_history()
    ) == 3

    db.commit()

    main_head = (
        db.get_branch_head("main")
    )

    main_commit = (
        db.history.get_version(
            main_head
        )
    )

    assert (
        main_commit.operation
        == "TRANSACTION COMMIT"
    )

    # --------------------------------------------------
    # Experiment transaction.
    # --------------------------------------------------

    db.switch_branch(
        "experiment"
    )

    db.begin()

    db.execute(
        "INSERT INTO users VALUES (4, 'Experiment A');"
    )

    db.execute(
        "INSERT INTO users VALUES (5, 'Experiment B');"
    )

    # Again, mutations inside the transaction have not individually
    # expanded history.
    history_before_experiment_commit = len(
        db.get_history()
    )

    assert (
        history_before_experiment_commit
        == 4
    )

    db.commit()

    experiment_head = (
        db.get_branch_head("experiment")
    )

    experiment_commit = (
        db.history.get_version(
            experiment_head
        )
    )

    assert (
        experiment_commit.operation
        == "TRANSACTION COMMIT"
    )

    # --------------------------------------------------
    # Merge after both transactions are committed.
    # --------------------------------------------------

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

    merge_version = (
        db.history.get_version(
            merge_version_id
        )
    )

    assert (
        merge_version.parent_version_id
        == main_head
    )

    assert (
        merge_version.merge_parent_version_id
        == experiment_head
    )

    assert (
        merge_version.operation
        == "MERGE experiment INTO main"
    )

    # Verify logical rows independent of internal Record ID ordering.
    rows = (
        db.get_table("users").rows
    )

    assert {
        tuple(row)
        for row in rows
    } == {
        (1, "Base"),
        (2, "Main A"),
        (3, "Main B"),
        (4, "Experiment A"),
        (5, "Experiment B")
    }


def test_transaction_rollback_before_merge_preserves_branch_head(
    tmp_path
):
    """
    Rolling back a transaction before a merge must discard the
    transaction changes completely. The later merge must see only
    committed branch history.
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

    committed_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    db.begin()

    db.execute(
        "INSERT INTO users VALUES (2, 'Should Roll Back');"
    )

    # The branch head must not move during the transaction.
    assert (
        db.get_branch_head(
            "experiment"
        )
        == committed_head
    )

    db.rollback()

    assert db._snapshot is None

    assert (
        db.get_branch_head(
            "experiment"
        )
        == committed_head
    )

    assert db.get_table(
        "users"
    ).rows == [
        [1, "Base"]
    ]

    # There is nothing new to merge because the transaction was
    # rolled back.
    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert (
        result["status"]
        == "UP_TO_DATE"
    )

    assert (
        result["source_version"]
        == committed_head
    )


def test_merge_after_transaction_preserves_transaction_history(
    tmp_path
):
    """
    A merge must not replace or rewrite an existing transaction
    commit. The transaction commit remains the target branch's
    first parent.
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

    # Main transaction.
    db.begin()

    db.execute(
        "INSERT INTO users VALUES (1, 'Main');"
    )

    db.commit()

    main_transaction_head = (
        db.get_branch_head(
            "main"
        )
    )

    assert (
        db.history.get_version(
            main_transaction_head
        ).operation
        == "TRANSACTION COMMIT"
    )

    # Experiment transaction.
    db.switch_branch(
        "experiment"
    )

    db.begin()

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    db.commit()

    experiment_transaction_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    assert (
        db.history.get_version(
            experiment_transaction_head
        ).operation
        == "TRANSACTION COMMIT"
    )

    # Merge.
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

    merge_version = (
        db.history.get_version(
            result["merged_version"]
        )
    )

    # The transaction commit remains the target parent.
    assert (
        merge_version.parent_version_id
        == main_transaction_head
    )

    # The experiment transaction commit is the merge parent.
    assert (
        merge_version.merge_parent_version_id
        == experiment_transaction_head
    )

    # Both transaction commits must remain ancestors.
    assert db._is_ancestor(
        main_transaction_head,
        result["merged_version"]
    )

    assert db._is_ancestor(
        experiment_transaction_head,
        result["merged_version"]
    )


def test_failed_merge_does_not_end_active_transaction(
    tmp_path
):
    """
    A rejected merge must not accidentally clear an active
    transaction context.

    The merge should fail immediately and leave the transaction
    active.
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

    db.create_branch(
        "experiment"
    )

    db.begin()

    assert db._snapshot is not None

    history_count_before = len(
        db.get_history()
    )

    try:
        db.merge_branch(
            "experiment"
        )
        assert False
    except RuntimeError:
        pass

    assert db._snapshot is not None

    assert (
        len(db.get_history())
        == history_count_before
    )

    db.rollback()

    assert db._snapshot is None