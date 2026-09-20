from pydb.database import Database


def test_merge_dag_persists_across_restart(
    tmp_path
):
    """
    A successful merge must preserve its complete two-parent DAG
    after the database is saved and reopened.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
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

    # Main branch gets its own change.
    db.execute(
        "INSERT INTO users VALUES (2, 'Main');"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment branch gets its own change.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3, 'Experiment');"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    # Merge experiment into main.
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

    assert (
        merge_version.parent_version_id
        == main_head
    )

    assert (
        merge_version.merge_parent_version_id
        == experiment_head
    )

    # Save the complete DAG.
    db.save()

    # --------------------------------------------------
    # Restart PyDB from persistent storage.
    # --------------------------------------------------

    restarted = Database(
        file_path=file_path
    )

    # The merge version must still exist.
    restarted_merge = (
        restarted.history.get_version(
            merge_version_id
        )
    )

    assert (
        restarted_merge.parent_version_id
        == main_head
    )

    assert (
        restarted_merge.merge_parent_version_id
        == experiment_head
    )

    # --------------------------------------------------
    # Both parents must still be reachable.
    # --------------------------------------------------

    ancestors = (
        restarted._get_ancestor_ids(
            merge_version_id
        )
    )

    assert (
        main_head
        in ancestors
    )

    assert (
        experiment_head
        in ancestors
    )

    # The original common ancestor must also remain reachable.
    assert 2 in ancestors


def test_branch_heads_persist_after_restart(
    tmp_path
):
    """
    Branch names and branch heads must survive a database restart.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    db.create_branch(
        "experiment"
    )

    # Main advances independently.
    db.execute(
        "INSERT INTO users VALUES (2);"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment advances independently.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3);"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    # Return to main and save.
    db.switch_branch(
        "main"
    )

    db.save()

    # Restart.
    restarted = Database(
        file_path=file_path
    )

    branches = (
        restarted.get_branches()
    )

    assert (
        branches["main"]
        == main_head
    )

    assert (
        branches["experiment"]
        == experiment_head
    )


def test_current_branch_persists_after_restart(
    tmp_path
):
    """
    The currently active branch must survive a restart.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    db.create_branch(
        "experiment"
    )

    db.switch_branch(
        "experiment"
    )

    assert (
        db.get_current_branch()
        == "experiment"
    )

    db.save()

    restarted = Database(
        file_path=file_path
    )

    assert (
        restarted.get_current_branch()
        == "experiment"
    )

def test_merge_version_state_persists_after_restart(
    tmp_path
):
    """
    The actual merged database state must be persisted alongside
    the merge DAG metadata.

    Logical row contents are verified independently of internal
    Record ID ordering.
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

    # Merge.
    db.switch_branch(
        "main"
    )

    result = db.merge_branch(
        "experiment"
    )

    assert result["status"] == "MERGED"

    merged_version_id = (
        result["merged_version"]
    )

    db.save()

    # Restart.
    restarted = Database(
        file_path=file_path
    )

    # The active branch should still be main.
    assert (
        restarted.get_current_branch()
        == "main"
    )

    # The persisted branch head should be the merge commit.
    assert (
        restarted.get_branch_head("main")
        == merged_version_id
    )

    # The persisted source branch should still point to its
    # pre-merge head.
    assert (
        restarted.get_branch_head("experiment")
        == result["source_version"]
    )

    # The merged state itself must be restored.
    rows = (
        restarted.get_table("users").rows
    )

    # Verify logical data rather than internal Record ID order.
    assert {
        tuple(row)
        for row in rows
    } == {
        (1, "Base"),
        (2, "Main"),
        (3, "Experiment")
    }

def test_common_ancestor_resolution_survives_restart(
    tmp_path
):
    """
    Common-ancestor resolution must continue to work after the
    version graph has been persisted and reconstructed.
    """
    file_path = str(
        tmp_path / "test.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    # V2 is the common ancestor.
    db.create_branch(
        "experiment"
    )

    # Main -> V3.
    db.execute(
        "INSERT INTO users VALUES (2);"
    )

    main_head = (
        db.get_branch_head("main")
    )

    # Experiment -> V4.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "INSERT INTO users VALUES (3);"
    )

    experiment_head = (
        db.get_branch_head("experiment")
    )

    db.switch_branch(
        "main"
    )

    # Persist before the merge.
    db.save()

    restarted = Database(
        file_path=file_path
    )

    ancestor = (
        restarted._find_common_ancestor_version_id(
            main_head,
            experiment_head
        )
    )

    assert ancestor == 2


def test_dag_ancestry_survives_second_merge_after_restart(
    tmp_path
):
    """
    After restarting from a persisted merge graph, PyDB must still
    be able to create another merge and retain ancestry from the
    earlier merge.
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

    experiment_first_head = (
        db.get_branch_head("experiment")
    )

    # First merge.
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

    db.save()

    # --------------------------------------------------
    # Restart after the first merge.
    # --------------------------------------------------

    restarted = Database(
        file_path=file_path
    )

    assert (
        restarted.get_branch_head("main")
        == first_merge_version
    )

    assert (
        restarted.get_branch_head("experiment")
        == experiment_first_head
    )

    # --------------------------------------------------
    # Continue experiment after restart.
    # --------------------------------------------------

    restarted.switch_branch(
        "experiment"
    )

    restarted.execute(
        "INSERT INTO users VALUES (4, 'Experiment Later');"
    )

    experiment_second_head = (
        restarted.get_branch_head("experiment")
    )

    # --------------------------------------------------
    # Continue main after restart.
    # --------------------------------------------------

    restarted.switch_branch(
        "main"
    )

    restarted.execute(
        "INSERT INTO users VALUES (5, 'Main Later');"
    )

    main_second_head = (
        restarted.get_branch_head("main")
    )

    # --------------------------------------------------
    # Second merge.
    # --------------------------------------------------

    second_merge = restarted.merge_branch(
        "experiment"
    )

    assert (
        second_merge["status"]
        == "MERGED"
    )

    assert (
        second_merge["target_version"]
        == main_second_head
    )

    assert (
        second_merge["source_version"]
        == experiment_second_head
    )

    # The old experiment head is still part of the DAG.
    assert restarted._is_ancestor(
        experiment_first_head,
        second_merge["merged_version"]
    )

    # The first merge is still part of main's ancestry.
    assert restarted._is_ancestor(
        first_merge_version,
        second_merge["merged_version"]
    )

    # All logical rows remain present.
    rows = (
        restarted.get_table("users").rows
    )

    assert {
        tuple(row)
        for row in rows
    } == {
        (1, "Base"),
        (2, "Main"),
        (3, "Experiment"),
        (4, "Experiment Later"),
        (5, "Main Later")
    }