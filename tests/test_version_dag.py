from pydb.database import Database


def test_repeated_merge_is_up_to_date(
    tmp_path
):
    """
    After a successful merge, attempting to merge the same source
    branch again should detect that the source branch is already
    contained in the target history.

    No additional merge version should be created.
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
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    # Create experiment from V2.
    db.create_branch(
        "experiment"
    )

    # Main branch change.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment branch change.
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

    # Merge experiment into main.
    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert first_merge["status"] == "MERGED"

    first_merge_version = (
        first_merge["merged_version"]
    )

    # The merge commit now contains the experiment version in its
    # ancestry through merge_parent_version_id.
    assert db._is_ancestor(
        experiment_head,
        first_merge_version
    )

    history_count_before = len(
        db.get_history()
    )

    # Attempt the exact same merge again.
    second_merge = db.merge_branch(
        "experiment"
    )

    assert second_merge["status"] == "UP_TO_DATE"

    assert (
        second_merge["target_version"]
        == first_merge_version
    )

    assert (
        second_merge["source_version"]
        == experiment_head
    )

    assert (
        second_merge["ancestor_version"]
        == experiment_head
    )

    assert (
        second_merge["merged_version"]
        == first_merge_version
    )

    # No new version should have been created.
    assert len(
        db.get_history()
    ) == history_count_before

    # The original branch heads remain unchanged.
    assert (
        db.get_branch_head("main")
        == first_merge_version
    )

    assert (
        db.get_branch_head("experiment")
        == experiment_head
    )

    # These variables make it explicit that both branches
    # actually diverged before the merge.
    assert main_head != experiment_head


def test_merge_commit_has_two_parent_ancestry(
    tmp_path
):
    """
    A merge commit must expose both of its parents to the DAG
    traversal logic.

    Both the original target parent and source parent must be
    recognized as ancestors of the merge commit.
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

    # Main branch.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    target_head = (
        db.get_branch_head(
            "main"
        )
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

    result = db.merge_branch(
        "experiment"
    )

    assert result["status"] == "MERGED"

    merge_version_id = (
        result["merged_version"]
    )

    merge_version = (
        db.history.get_version(
            merge_version_id
        )
    )

    # The target branch is the normal parent.
    assert (
        merge_version.parent_version_id
        == target_head
    )

    # The source branch is the second parent.
    assert (
        merge_version.merge_parent_version_id
        == source_head
    )

    # Both parents must be reachable from the merge commit.
    ancestor_ids = db._get_ancestor_ids(
        merge_version_id
    )

    assert (
        target_head
        in ancestor_ids
    )

    assert (
        source_head
        in ancestor_ids
    )


def test_common_ancestor_after_previous_merge(
    tmp_path
):
    """
    After a previous merge, the DAG must still identify the correct
    common ancestor when both branches continue evolving.

    History shape:

        V2
       /  \
     main  experiment
       \\    /
        V5  <- first merge
         |
       main continues

    The second merge must use the experiment branch's post-fork
    version before its later change as the common ancestor.
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

    # Create experiment from V2.
    db.create_branch(
        "experiment"
    )

    # --------------------------------------------------
    # Main diverges.
    # --------------------------------------------------

    db.execute(
        "INSERT INTO users VALUES (3, 'Main');"
    )

    main_first_head = (
        db.get_branch_head(
            "main"
        )
    )

    # --------------------------------------------------
    # Experiment diverges independently.
    # --------------------------------------------------

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Experiment');"
    )

    experiment_first_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    # This version should become the common ancestor of the
    # branches' next round of independent changes.
    expected_second_ancestor = (
        experiment_first_head
    )

    # --------------------------------------------------
    # First merge.
    # --------------------------------------------------

    db.switch_branch(
        "main"
    )

    first_merge = db.merge_branch(
        "experiment"
    )

    assert first_merge["status"] == "MERGED"

    first_merge_version = (
        first_merge["merged_version"]
    )

    assert (
        first_merge["ancestor_version"]
        == 2
    )

    # --------------------------------------------------
    # Experiment continues from its own original branch head.
    # --------------------------------------------------

    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (4, 'Experiment Later');"
    )

    experiment_second_head = (
        db.get_branch_head(
            "experiment"
        )
    )

    # --------------------------------------------------
    # Main continues from the previous merge commit.
    # --------------------------------------------------

    db.switch_branch(
        "main"
    )

    db.execute(
        "INSERT INTO users VALUES (5, 'Main Later');"
    )

    main_second_head = (
        db.get_branch_head(
            "main"
        )
    )

    # --------------------------------------------------
    # Second merge.
    # --------------------------------------------------

    second_merge = db.merge_branch(
        "experiment"
    )

    assert second_merge["status"] == "MERGED"

    assert (
        second_merge["target_version"]
        == main_second_head
    )

    assert (
        second_merge["source_version"]
        == experiment_second_head
    )

    # The common ancestor must be experiment_first_head.
    assert (
        second_merge["ancestor_version"]
        == expected_second_ancestor
    )

    second_merge_version = (
        second_merge["merged_version"]
    )

    merged_version = (
        db.history.get_version(
            second_merge_version
        )
    )

    # The previous merge must remain in the target ancestry.
    assert db._is_ancestor(
        first_merge_version,
        second_merge_version
    )

    # The original experiment ancestor must also remain
    # reachable through the DAG.
    assert db._is_ancestor(
        experiment_first_head,
        second_merge_version
    )

    # --------------------------------------------------
    # Verify that all logical rows survived.
    #
    # Internal Record IDs can be remapped during a merge, so
    # assertions are made against logical row contents rather than
    # assuming a particular internal ordering.
    # --------------------------------------------------

    rows = (
        db.get_table("users").rows
    )

    assert {
        tuple(row)
        for row in rows
    } == {
        (1, "Base"),
        (2, "Experiment"),
        (3, "Main"),
        (4, "Experiment Later"),
        (5, "Main Later")
    }