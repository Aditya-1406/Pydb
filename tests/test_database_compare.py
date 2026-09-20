from pydb.database import Database


def test_compare_returns_same_results_for_same_version(tmp_path):
    """
    Comparing a version with itself should produce identical
    results and execution behavior.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    comparison = db.compare_versions(
        2,
        2,
        "SELECT * FROM users WHERE age > 20;"
    )

    assert comparison[
        "result_changed"
    ] is False

    assert comparison[
        "access_path_changed"
    ] is False

    assert comparison[
        "before"]["result"]== comparison[
        "after"
    ]["result"]


def test_compare_detects_result_change(tmp_path):
    """
    The same query should report different results when the
    historical database states contain different data.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 18);"
    )

    # V3
    db.execute(
        "INSERT INTO users VALUES (2, 25);"
    )

    comparison = db.compare_versions(
        2,
        3,
        "SELECT * FROM users WHERE age > 20;"
    )

    assert comparison[
        "result_changed"
    ] is True

    assert comparison[
        "before"
    ]["result"] == []

    assert comparison[
        "after"
    ]["result"] == [
        [2, 25]
    ]


def test_compare_detects_access_path_change(tmp_path):
    """
    Adding an index in a later version should be visible in
    query comparison.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    # V1
    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    # V2
    db.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    # V3
    db.execute(
        "CREATE INDEX age_idx "
        "ON users(age) USING BTREE;"
    )

    comparison = db.compare_versions(
        2,
        3,
        "SELECT * FROM users WHERE age = 22;"
    )

    assert comparison[
        "access_path_changed"
    ] is True

    assert (
        comparison[
            "after"
        ]["stats"]["access_path"]
        == "BTREE_INDEX"
    )


def test_compare_does_not_change_current_database(tmp_path):
    """
    Comparing historical versions must never modify the current
    live database state.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    current_version_before = (
        db.get_current_version().version_id
    )

    current_rows_before = (
        db.get_table("users").rows.copy()
    )

    db.compare_versions(
        1,
        2,
        "SELECT * FROM users WHERE age > 20;"
    )

    assert (
        db.get_current_version().version_id
        == current_version_before
    )

    assert (
        db.get_table("users").rows
        == current_rows_before
    )


def test_compare_rejects_non_select_query(tmp_path):
    """
    Comparison should accept only SELECT statements.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.compare_versions(
            0,
            0,
            "DELETE FROM users;"
        )
        assert False
    except ValueError as exc:
        assert (
            ".compare only supports SELECT statements"
            in str(exc)
        )


def test_compare_rejects_aggregate_query(tmp_path):
    """
    Aggregate queries are initially outside the comparison
    statistics path.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    try:
        db.compare_versions(
            1,
            1,
            "SELECT COUNT(*) FROM users;"
        )
        assert False
    except ValueError as exc:
        assert (
            ".compare does not yet support aggregate queries"
            in str(exc)
        )


def test_compare_rejects_group_by_query(tmp_path):
    """
    GROUP BY queries are initially outside the comparison
    statistics path.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    try:
        db.compare_versions(
            1,
            1,
            "SELECT age FROM users GROUP BY age;"
        )
        assert False
    except ValueError as exc:
        assert (
            ".compare does not yet support GROUP BY queries"
            in str(exc)
        )


def test_compare_reports_missing_table_in_version(tmp_path):
    """
    Comparison should clearly report when the requested SELECT
    table did not exist in one historical version.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    try:
        db.compare_versions(
            0,
            1,
            "SELECT * FROM users;"
        )
        assert False
    except ValueError as exc:
        assert (
            "Table 'users' does not exist in version '0'"
            in str(exc)
        )