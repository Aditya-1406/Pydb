from pydb.database import Database


def test_whatif_btree_index_changes_access_path(
    tmp_path
):
    """
    A hypothetical B+Tree index should be visible to the planner
    without creating a real index.
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

    db.execute(
        "INSERT INTO users VALUES (2, 30);"
    )

    analysis = db.what_if_index(
        """
        CREATE INDEX age_idx
        ON users(age)
        USING BTREE;
        """,
        """
        SELECT * FROM users
        WHERE age = 22;
        """
    )

    assert (
        analysis["index"]["name"]
        == "age_idx"
    )

    assert (
        analysis["index"]["type"]
        == "BTREE"
    )

    assert (
        analysis["without_index"]["stats"]["access_path"]
        == "FULL_SCAN"
    )

    assert (
        analysis["with_index"]["stats"]["access_path"]
        == "BTREE_INDEX"
    )

    assert (
        analysis["access_path_changed"]
        is True
    )


def test_whatif_hash_index_changes_equality_plan(
    tmp_path
):
    """
    A hypothetical hash index should be usable for equality
    predicates.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    analysis = db.what_if_index(
        """
        CREATE INDEX name_idx
        ON users(name)
        USING HASH;
        """,
        """
        SELECT * FROM users
        WHERE name = 'Aditya';
        """
    )

    assert (
        analysis["index"]["type"]
        == "HASH"
    )

    assert (
        analysis["without_index"]["stats"]["access_path"]
        == "FULL_SCAN"
    )

    assert (
        analysis["with_index"]["stats"]["access_path"]
        == "HASH_INDEX"
    )


def test_whatif_does_not_modify_database(
    tmp_path
):
    """
    What-if analysis must not create a real index, version, or
    otherwise modify the database.
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

    history_count_before = len(
        db.get_history()
    )

    dirty_before = db.dirty

    analysis = db.what_if_index(
        """
        CREATE INDEX age_idx
        ON users(age)
        USING BTREE;
        """,
        """
        SELECT * FROM users
        WHERE age = 22;
        """
    )

    assert analysis is not None

    table = db.get_table(
        "users"
    )

    assert not table.has_named_index(
        "age_idx"
    )

    assert (
        len(db.get_history())
        == history_count_before
    )

    assert (
        db.dirty
        == dirty_before
    )


def test_whatif_does_not_change_query_result(
    tmp_path
):
    """
    Adding a hypothetical index should not alter the logical
    SELECT result.
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
        "INSERT INTO users VALUES (1, 18);"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 25);"
    )

    analysis = db.what_if_index(
        """
        CREATE INDEX age_idx
        ON users(age)
        USING BTREE;
        """,
        """
        SELECT * FROM users
        WHERE age > 20;
        """
    )

    assert (
        analysis["without_index"]["result"]
        == analysis["with_index"]["result"]
    )

    assert (
        analysis["result_changed"]
        is False
    )


def test_whatif_requires_matching_table(
    tmp_path
):
    """
    The hypothetical index and SELECT must target the same table.
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
        "CREATE TABLE books (id INT);"
    )

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "SELECT * FROM books;"
        )

        assert False

    except ValueError as exc:
        assert (
            "CREATE INDEX and SELECT must target the same table"
            in str(exc)
        )


def test_whatif_rejects_non_create_index(
    tmp_path
):
    """
    The first statement must be CREATE INDEX.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    try:
        db.what_if_index(
            "DROP INDEX age_idx;",
            "SELECT * FROM users;"
        )

        assert False

    except ValueError as exc:
        assert (
            ".whatif requires a CREATE INDEX statement"
            in str(exc)
        )


def test_whatif_rejects_non_select_workload(
    tmp_path
):
    """
    The workload statement must be SELECT.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "DELETE FROM users;"
        )

        assert False

    except ValueError as exc:
        assert (
            ".whatif only supports SELECT workloads"
            in str(exc)
        )


def test_whatif_rejects_group_by(
    tmp_path
):
    """
    GROUP BY is not yet supported by the what-if statistics path.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "SELECT id FROM users GROUP BY id;"
        )

        assert False

    except ValueError as exc:
        assert (
            ".whatif does not yet support GROUP BY queries"
            in str(exc)
        )


def test_whatif_rejects_aggregate(
    tmp_path
):
    """
    Aggregate queries are not yet supported by the what-if
    statistics path.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "SELECT COUNT(*) FROM users;"
        )

        assert False

    except ValueError as exc:
        assert (
            ".whatif does not yet support aggregate queries"
            in str(exc)
        )


def test_whatif_rejects_existing_index(
    tmp_path
):
    """
    A hypothetical index cannot reuse an existing index name.
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
        "CREATE INDEX id_idx ON users(id);"
    )

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "SELECT * FROM users WHERE id = 1;"
        )

        assert False

    except ValueError as exc:
        assert (
            "Index 'id_idx' already exists"
            in str(exc)
        )


def test_whatif_blocked_during_transaction(
    tmp_path
):
    """
    What-if analysis is blocked while a transaction is active.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    db.begin()

    try:
        db.what_if_index(
            "CREATE INDEX id_idx ON users(id);",
            "SELECT * FROM users WHERE id = 1;"
        )

        assert False

    except RuntimeError as exc:
        assert (
            "Cannot run what-if analysis during an active transaction"
            in str(exc)
        )