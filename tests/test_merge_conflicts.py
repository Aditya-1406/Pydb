from pydb.database import Database


def test_table_delete_vs_source_update_is_conflict(
    tmp_path
):
    """
    Deleting a table on the target branch while the source branch
    changes that same table must produce a table_delete_conflict.
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

    # Main deletes the table.
    db.execute(
        "DROP TABLE users;"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment modifies the table instead of deleting it.
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

    assert len(
        result["conflicts"]
    ) == 1

    conflict = result[
        "conflicts"
    ][0]

    assert (
        conflict["type"]
        == "table_delete_conflict"
    )

    assert (
        conflict["table"]
        == "users"
    )

    # The deleted target state must remain untouched.
    assert (
        "users"
        not in db.list_tables()
    )

    # No merge version should have been created.
    assert (
        len(db.get_history())
        == history_count_before
    )


def test_table_delete_vs_source_unchanged_is_not_conflict(
    tmp_path
):
    """
    If the target deletes a table and the source leaves that table
    completely unchanged, the deletion can be accepted automatically.
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

    db.execute(
        "INSERT INTO users VALUES (1);"
    )

    db.create_branch(
        "experiment"
    )

    # Main deletes the table.
    db.execute(
        "DROP TABLE users;"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
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
        == "UP_TO_DATE"
    )

    assert (
        result["source_version"]
        == experiment_head
    )

    assert (
        result["merged_version"]
        == main_head
    )

    assert (
        "users"
        not in db.list_tables()
    )


def test_same_table_added_differently_is_conflict(
    tmp_path
):
    """
    If both branches independently create a table with the same
    name but different definitions, the merge must report a
    table_add_conflict.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # Start from an empty database.
    db.create_branch(
        "experiment"
    )

    # Main creates one definition.
    db.execute(
        "CREATE TABLE users "
        "(id INT);"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment independently creates another definition.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "CREATE TABLE users "
        "(name TEXT);"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
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

    assert len(
        result["conflicts"]
    ) == 1

    conflict = result[
        "conflicts"
    ][0]

    assert (
        conflict["type"]
        == "table_add_conflict"
    )

    assert (
        conflict["table"]
        == "users"
    )

    # Main's original table must remain untouched.
    table = db.get_table(
        "users"
    )

    assert [
        column.name
        for column in table.columns
    ] == [
        "id"
    ]

    # No merge version should have been created.
    assert (
        len(db.get_history())
        == history_count_before
    )


def test_same_index_name_with_different_definitions_is_conflict(
    tmp_path
):
    """
    If both branches independently create the same index name with
    different definitions, the merge must report an index_conflict.

    PyDB CREATE INDEX syntax is:

        CREATE INDEX <name>
        ON <table>(<column>)
        USING <HASH|BTREE>
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

    db.execute(
        "INSERT INTO users VALUES (1, 50000);"
    )

    # Create experiment from the common ancestor.
    db.create_branch(
        "experiment"
    )

    # Main creates a HASH index.
    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING HASH;"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment creates a BTREE index with the same name.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING BTREE;"
    )

    experiment_head = (
        db.get_branch_head(
            "experiment"
        )
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

    assert len(
        result["conflicts"]
    ) == 1

    conflict = result[
        "conflicts"
    ][0]

    assert (
        conflict["type"]
        == "index_conflict"
    )

    assert (
        conflict["table"]
        == "users"
    )

    assert (
        conflict["property"]
        == "index_definitions"
    )

    # The target branch retains its original index.
    table = db.get_table(
        "users"
    )

    assert (
        table.index_definitions[
            "salary_idx"
        ]["type"]
        == "HASH"
    )

    # No merge version should have been created.
    assert (
        len(db.get_history())
        == history_count_before
    )


def test_identical_index_changes_merge_cleanly(
    tmp_path
):
    """
    If both branches independently create the exact same index
    definition, the merge should recognize that both branches agree.
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

    # Main creates the index.
    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING HASH;"
    )

    main_head = (
        db.get_branch_head(
            "main"
        )
    )

    # Experiment independently creates the identical index.
    db.switch_branch(
        "experiment"
    )

    db.execute(
        "CREATE INDEX salary_idx "
        "ON users(salary) "
        "USING HASH;"
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

    table = db.get_table(
        "users"
    )

    assert (
        table.index_definitions[
            "salary_idx"
        ]["type"]
        == "HASH"
    )

    assert (
        table.index_definitions[
            "salary_idx"
        ]["column"]
        == "salary"
    )