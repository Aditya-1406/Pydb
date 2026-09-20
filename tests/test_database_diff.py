from pydb.database import Database


def test_diff_detects_added_rows(tmp_path):
    """
    Diff should detect rows that exist only in the later version.
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

    diff = db.diff_versions(
        1,
        2
    )

    table_diff = diff[
        "tables_changed"
    ]["users"]

    assert table_diff[
        "rows_added"
    ] == [
        {
            "record_id": 1,
            "row": [1, "Aditya"]
        }
    ]

    assert table_diff[
        "rows_removed"
    ] == []

    assert table_diff[
        "rows_updated"
    ] == []


def test_diff_detects_removed_rows(tmp_path):
    """
    Diff should detect rows that existed in the earlier version
    but not in the later version.
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

    # V3
    db.execute(
        "DELETE FROM users WHERE id = 1;"
    )

    diff = db.diff_versions(
        2,
        3
    )

    table_diff = diff[
        "tables_changed"
    ]["users"]

    assert table_diff[
        "rows_removed"
    ] == [
        {
            "record_id": 1,
            "row": [1, "Aditya"]
        }
    ]

    assert table_diff[
        "rows_added"
    ] == []

    assert table_diff[
        "rows_updated"
    ] == []


def test_diff_detects_updated_rows(tmp_path):
    """
    Diff should detect a row whose values changed while its
    Record ID remained the same.
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

    # V3
    db.execute(
        "UPDATE users SET name = 'Garg' WHERE id = 1;"
    )

    diff = db.diff_versions(
        2,
        3
    )

    table_diff = diff[
        "tables_changed"
    ]["users"]

    assert table_diff[
        "rows_updated"
    ] == [
        {
            "record_id": 1,
            "before": [1, "Aditya"],
            "after": [1, "Garg"]
        }
    ]

    assert table_diff[
        "rows_added"
    ] == []

    assert table_diff[
        "rows_removed"
    ] == []


def test_diff_detects_added_table(tmp_path):
    """
    Diff should detect tables introduced by the later version.
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
        "CREATE TABLE books (id INT, title TEXT);"
    )

    diff = db.diff_versions(
        1,
        2
    )

    assert diff[
        "tables_added"
    ] == [
        "books"
    ]

    assert diff[
        "tables_removed"
    ] == []

    assert diff[
        "tables_changed"
    ] == {}


def test_diff_detects_removed_table(tmp_path):
    """
    Diff should detect tables removed by the later version.
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
        "DROP TABLE users;"
    )

    diff = db.diff_versions(
        1,
        2
    )

    assert diff[
        "tables_removed"
    ] == [
        "users"
    ]

    assert diff[
        "tables_added"
    ] == []

    assert diff[
        "tables_changed"
    ] == {}


def test_diff_detects_schema_change(tmp_path):
    """
    Diff should report a schema change between versions.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT);"
    )

    # V2
    #
    # PyDB currently changes schema through recreated table
    # state in historical versions, so create another table
    # here to verify that the diff engine handles schema
    # differences in serialized states.
    #
    # Build the second state directly through the existing table
    # representation rather than expanding SQL ALTER TABLE in V2.
    table = db.get_table(
        "users"
    )

    original_state = table.to_dict()

    modified_state = dict(
        original_state
    )

    modified_state[
        "columns"
    ] = [
        {
            "name": "id",
            "data_type": "INT"
        },
        {
            "name": "name",
            "data_type": "TEXT"
        }
    ]

    db.history.create_version(
        state={
            "tables": {
                "users": modified_state
            }
        },
        operation="SCHEMA CHANGE"
    )

    diff = db.diff_versions(
        1,
        2
    )

    assert diff[
        "tables_changed"
    ]["users"]["schema_changed"] is True


def test_diff_detects_index_change(tmp_path):
    """
    Diff should detect changes to persisted index definitions.
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
        "CREATE INDEX name_idx ON users(name);"
    )

    diff = db.diff_versions(
        1,
        2
    )

    assert diff[
        "tables_changed"
    ]["users"]["indexes_changed"] is True


def test_diff_same_version_returns_no_changes(tmp_path):
    """
    Comparing a version with itself should report no changes.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    diff = db.diff_versions(
        1,
        1
    )

    assert diff[
        "tables_added"
    ] == []

    assert diff[
        "tables_removed"
    ] == []

    assert diff[
        "tables_changed"
    ] == {}

def test_diff_works_across_branches(tmp_path):
    """
    Diff should correctly distinguish independently created rows
    on different branches, even when their internal Record IDs
    happen to match.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1 main
    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # V2 main
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.create_branch(
        "experiment",
        from_version_id=1
    )

    db.switch_branch(
        "experiment"
    )

    # V3 experiment.
    #
    # This row receives internal Record ID 1 because the branch
    # started from V1, before any rows existed.
    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    diff = db.diff_versions(
        2,
        3
    )

    table_diff = diff[
        "tables_changed"
    ]["users"]

    assert table_diff[
        "rows_added"
    ] == [
        {
            "record_id": 1,
            "row": [2, "Ravi"]
        }
    ]

    assert table_diff[
        "rows_removed"
    ] == [
        {
            "record_id": 1,
            "row": [1, "Aditya"]
        }
    ]

    assert table_diff[
        "rows_updated"
    ] == []