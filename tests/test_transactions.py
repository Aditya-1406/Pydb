import pytest

from pydb.database import Database


def test_begin_and_rollback_restore_insert(tmp_path):
    """
    ROLLBACK should remove rows inserted during a transaction.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute("BEGIN;")

    database.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    database.execute("ROLLBACK;")

    assert database.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_begin_and_commit_persist_insert(tmp_path):
    """
    COMMIT should persist changes made during a transaction.
    """
    database_path = str(
        tmp_path / "test.json"
    )

    database = Database(database_path)

    database.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    database.execute("BEGIN;")

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute("COMMIT;")

    assert database.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]

    # Verify persistence by creating a new Database instance.
    reloaded_database = Database(database_path)

    assert reloaded_database.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_rollback_restores_update(tmp_path):
    """
    ROLLBACK should restore values changed during a transaction.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute("BEGIN;")

    database.execute(
        "UPDATE users "
        "SET name = 'Rajat' "
        "WHERE id = 1;"
    )

    database.execute("ROLLBACK;")

    assert database.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_rollback_restores_delete(tmp_path):
    """
    ROLLBACK should restore rows deleted during a transaction.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    database.execute("BEGIN;")

    database.execute(
        "DELETE FROM users WHERE id = 1;"
    )

    database.execute("ROLLBACK;")

    assert database.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_rollback_restores_created_table(tmp_path):
    """
    ROLLBACK should remove tables created during a transaction.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN;")

    database.execute(
        "CREATE TABLE users (id INT);"
    )

    assert database.execute(
        "SHOW TABLES;"
    ) == [
        "users"
    ]

    database.execute("ROLLBACK;")

    assert database.execute(
        "SHOW TABLES;"
    ) == []


def test_rollback_restores_dropped_table(tmp_path):
    """
    ROLLBACK should restore tables dropped during a transaction.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute(
        "CREATE TABLE users (id INT);"
    )

    # Persist the table before starting the transaction.
    database.save()

    database.execute("BEGIN;")

    database.execute(
        "DROP TABLE users;"
    )

    assert database.execute(
        "SHOW TABLES;"
    ) == []

    database.execute("ROLLBACK;")

    assert database.execute(
        "SHOW TABLES;"
    ) == [
        "users"
    ]


def test_nested_begin_is_rejected(tmp_path):
    """
    PyDB currently supports one active transaction at a time.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN;")

    with pytest.raises(
        RuntimeError,
        match="Transaction already active"
    ):
        database.execute("BEGIN;")


def test_commit_without_transaction_is_rejected(tmp_path):
    """
    COMMIT without BEGIN should fail.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    with pytest.raises(
        RuntimeError,
        match="No active transaction"
    ):
        database.execute("COMMIT;")


def test_rollback_without_transaction_is_rejected(tmp_path):
    """
    ROLLBACK without BEGIN should fail.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    with pytest.raises(
        RuntimeError,
        match="No active transaction"
    ):
        database.execute("ROLLBACK;")


def test_transaction_can_start_again_after_rollback(tmp_path):
    """
    A new transaction should be allowed after ROLLBACK.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN;")
    database.execute("ROLLBACK;")

    database.execute("BEGIN;")
    database.execute("COMMIT;")


def test_transaction_can_start_again_after_commit(tmp_path):
    """
    A new transaction should be allowed after COMMIT.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN;")
    database.execute("COMMIT;")

    database.execute("BEGIN;")
    database.execute("ROLLBACK;")


def test_transaction_restores_indexes_after_rollback(tmp_path):
    """
    ROLLBACK should restore both table data and index state.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    table = database.get_table("users")

    table.create_index("age")

    database.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    database.execute("BEGIN;")

    database.execute(
        "UPDATE users SET age = 30 WHERE id = 1;"
    )

    database.execute("ROLLBACK;")

    assert database.execute(
        "SELECT * FROM users WHERE age = 22;"
    ) == [
        [1, 22]
    ]

    assert database.execute(
        "SELECT * FROM users WHERE age = 30;"
    ) == []


def test_begin_without_semicolon_is_supported(tmp_path):
    """
    Transaction statements may omit the semicolon.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN")
    database.execute("ROLLBACK")


def test_commit_without_semicolon_is_supported(tmp_path):
    """
    COMMIT may omit the semicolon.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN")
    database.execute("COMMIT")


def test_rollback_without_semicolon_is_supported(tmp_path):
    """
    ROLLBACK may omit the semicolon.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    database.execute("BEGIN")
    database.execute("ROLLBACK")


def test_invalid_begin_statement_is_rejected(tmp_path):
    """
    BEGIN must be a complete single SQL statement.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    with pytest.raises(
        ValueError,
        match="Unexpected token"
    ):
        database.execute("BEGIN something;")


def test_invalid_commit_statement_is_rejected(tmp_path):
    """
    COMMIT must be a complete single SQL statement.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    with pytest.raises(
        ValueError,
        match="Unexpected token"
    ):
        database.execute("COMMIT something;")


def test_invalid_rollback_statement_is_rejected(tmp_path):
    """
    ROLLBACK must be a complete single SQL statement.
    """
    database = Database(
        str(tmp_path / "test.json")
    )

    with pytest.raises(
        ValueError,
        match="Unexpected token"
    ):
        database.execute("ROLLBACK something;")

import pytest

from pydb.database import Database


def test_begin_and_rollback_restore_insert(tmp_path):
    """
    Verify that an INSERT performed inside a transaction
    is removed when the transaction is rolled back.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("ROLLBACK;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_begin_and_commit_persist_insert(tmp_path):
    """
    Verify that an INSERT performed inside a transaction
    remains after COMMIT and is persisted to disk.
    """
    path = tmp_path / "test.json"

    db = Database(path)

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("COMMIT;")

    # Create a fresh Database instance to verify
    # that COMMIT actually persisted the change.
    reloaded = Database(path)

    assert reloaded.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_nested_begin_is_rejected(tmp_path):
    """
    Verify that PyDB does not allow nested transactions.
    """
    db = Database(tmp_path / "test.json")

    db.execute("BEGIN;")

    with pytest.raises(
        RuntimeError,
        match="Transaction already active"
    ):
        db.execute("BEGIN;")


def test_commit_without_transaction_is_rejected(tmp_path):
    """
    Verify that COMMIT fails when no transaction is active.
    """
    db = Database(tmp_path / "test.json")

    with pytest.raises(
        RuntimeError,
        match="No active transaction"
    ):
        db.execute("COMMIT;")


def test_rollback_without_transaction_is_rejected(tmp_path):
    """
    Verify that ROLLBACK fails when no transaction is active.
    """
    db = Database(tmp_path / "test.json")

    with pytest.raises(
        RuntimeError,
        match="No active transaction"
    ):
        db.execute("ROLLBACK;")


def test_transaction_can_restart_after_rollback(tmp_path):
    """
    Verify that a new transaction can be started after
    the previous transaction has been rolled back.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute("BEGIN;")
    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )
    db.execute("ROLLBACK;")

    # A new transaction should now be allowed.
    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("COMMIT;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [2, "Rajat"]
    ]


def test_transaction_can_restart_after_commit(tmp_path):
    """
    Verify that a new transaction can be started after
    the previous transaction has been committed.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("COMMIT;")

    # Start another transaction.
    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("COMMIT;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"],
        [2, "Rajat"]
    ]

def test_rollback_restores_update(tmp_path):
    """
    Verify that an UPDATE performed inside a transaction
    is undone by ROLLBACK.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("BEGIN;")

    db.execute(
        "UPDATE users SET name = 'Rajat' WHERE id = 1;"
    )

    db.execute("ROLLBACK;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]


def test_rollback_restores_delete(tmp_path):
    """
    Verify that a DELETE performed inside a transaction
    is undone by ROLLBACK.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("BEGIN;")

    db.execute(
        "DELETE FROM users WHERE id = 1;"
    )

    db.execute("ROLLBACK;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"],
        [2, "Rajat"]
    ]


def test_rollback_restores_create_table(tmp_path):
    """
    Verify that a table created inside a transaction
    disappears after ROLLBACK.
    """
    db = Database(tmp_path / "test.json")

    db.execute("BEGIN;")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    assert "users" in db.list_tables()

    db.execute("ROLLBACK;")

    assert "users" not in db.list_tables()


def test_rollback_restores_dropped_table(tmp_path):
    """
    Verify that a table dropped inside a transaction
    is restored by ROLLBACK.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("BEGIN;")

    db.execute("DROP TABLE users;")

    assert "users" not in db.list_tables()

    db.execute("ROLLBACK;")

    assert db.execute(
        "SELECT * FROM users;"
    ) == [
        [1, "Aditya"]
    ]

def test_rollback_restores_indexes(tmp_path):
    """
    Verify that an index created before a transaction
    is correctly restored after a rollback.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    table = db.get_table("users")
    table.create_index("id")

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("ROLLBACK;")

    table = db.get_table("users")

    assert table.has_index("id")

    assert db.execute(
        "SELECT * FROM users WHERE id = 1;"
    ) == [
        [1, "Aditya"]
    ]

    assert db.execute(
        "SELECT * FROM users WHERE id = 2;"
    ) == []


def test_rollback_restores_record_ids(tmp_path):
    """
    Verify that rollback restores the stable internal
    Record ID state.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    table = db.get_table("users")

    original_record_ids = table.record_ids.copy()
    original_next_record_id = table.next_record_id

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    db.execute("ROLLBACK;")

    table = db.get_table("users")

    assert table.record_ids == original_record_ids

    assert table.next_record_id == original_next_record_id


def test_rollback_does_not_reuse_deleted_record_id(tmp_path):
    """
    Verify that Record IDs remain stable and are never reused
    after a committed DELETE followed by a new INSERT.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    table = db.get_table("users")

    original_record_id = table.record_ids[0]

    db.execute(
        "DELETE FROM users WHERE id = 1;"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Rajat');"
    )

    table = db.get_table("users")

    assert table.record_ids == [
        original_record_id + 1
    ]

def test_rollback_restores_clean_dirty_state(tmp_path):
    """
    Verify that ROLLBACK restores a clean database state
    when the database was clean before BEGIN.
    """
    path = tmp_path / "test.json"

    db = Database(path)

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.save()

    assert db.dirty is False

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    assert db.dirty is True

    db.execute("ROLLBACK;")

    assert db.dirty is False


def test_rollback_restores_existing_dirty_state(tmp_path):
    """
    Verify that ROLLBACK restores an already-dirty state
    that existed before BEGIN.
    """
    db = Database(tmp_path / "test.json")

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    # The CREATE TABLE operation makes the database dirty.
    assert db.dirty is True

    db.execute("BEGIN;")

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute("ROLLBACK;")

    # The database was already dirty before BEGIN,
    # so rollback must restore dirty=True.
    assert db.dirty is True