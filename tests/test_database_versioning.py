from pydb.database import Database


def test_new_database_starts_with_version_zero(
    tmp_path
):
    """
    A fresh database should automatically have Version 0.
    """
    db = Database(
        file_path=str(
            tmp_path / "db.json"
        )
    )

    assert db.history.current_version_id == 0

    version = (
        db.history.get_version(0)
    )

    assert version.operation == "INITIAL"


def test_create_table_creates_version(
    tmp_path
):
    """
    A successful mutation outside a transaction creates
    one new version.
    """
    db = Database(
        file_path=str(
            tmp_path / "db.json"
        )
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    assert db.history.current_version_id == 1

    version = (
        db.history.get_version(1)
    )

    assert version.parent_version_id == 0
    assert version.operation == (
        "CREATE TABLE users"
    )


def test_multiple_mutations_create_multiple_versions(
    tmp_path
):
    """
    Independent mutations outside a transaction each create
    their own version.
    """
    db = Database(
        file_path=str(
            tmp_path / "db.json"
        )
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT
        );
        """
    )

    db.execute(
        """
        INSERT INTO users
        VALUES (1, 'Aditya');
        """
    )

    db.execute(
        """
        INSERT INTO users
        VALUES (2, 'Rahul');
        """
    )

    assert db.history.current_version_id == 3

    versions = db.get_history()

    assert len(versions) == 4

    assert versions[1].operation == (
        "CREATE TABLE users"
    )

    assert versions[2].operation == (
        "INSERT INTO users"
    )

    assert versions[3].operation == (
        "INSERT INTO users"
    )


def test_transaction_commit_creates_one_version(
    tmp_path
):
    """
    Multiple mutations inside a transaction should create
    exactly one version when committed.
    """
    db = Database(
        file_path=str(
            tmp_path / "db.json"
        )
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT,
            age INT
        );
        """
    )

    initial_version = (
        db.history.current_version_id
    )

    db.execute("BEGIN;")

    db.execute(
        """
        INSERT INTO users
        VALUES (1, 'Aditya', 22);
        """
    )

    db.execute(
        """
        INSERT INTO users
        VALUES (2, 'Rahul', 25);
        """
    )

    db.execute(
        """
        UPDATE users
        SET age = 23
        WHERE id = 1;
        """
    )

    # No version should have been created yet.
    assert (
        db.history.current_version_id
        == initial_version
    )

    db.execute("COMMIT;")

    assert (
        db.history.current_version_id
        == initial_version + 1
    )

    version = (
        db.history.get_current_version()
    )

    assert version.operation == (
        "TRANSACTION COMMIT"
    )


def test_transaction_rollback_creates_no_version(
    tmp_path
):
    """
    Rolled-back changes must not create a new version.
    """
    db = Database(
        file_path=str(
            tmp_path / "db.json"
        )
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT
        );
        """
    )

    initial_version = (
        db.history.current_version_id
    )

    db.execute("BEGIN;")

    db.execute(
        """
        INSERT INTO users
        VALUES (1, 'Temporary');
        """
    )

    db.execute("ROLLBACK;")

    assert (
        db.history.current_version_id
        == initial_version
    )

    result = db.execute(
        "SELECT * FROM users;"
    )

    assert result == []


def test_version_history_persists(
    tmp_path
):
    """
    Version history should survive a database reload.
    """
    file_path = str(
        tmp_path / "db.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT,
            name TEXT
        );
        """
    )

    db.execute(
        """
        INSERT INTO users
        VALUES (1, 'Aditya');
        """
    )

    db.save()

    db2 = Database(
        file_path=file_path
    )

    assert (
        db2.history.current_version_id
        == 2
    )

    versions = db2.get_history()

    assert len(versions) == 3

    assert versions[1].operation == (
        "CREATE TABLE users"
    )

    assert versions[2].operation == (
        "INSERT INTO users"
    )


def test_old_database_without_history_starts_version_zero(
    tmp_path
):
    """
    A V1 database without history should still load.

    Its existing state becomes the starting Version 0 for V2.
    """
    file_path = str(
        tmp_path / "db.json"
    )

    db = Database(
        file_path=file_path
    )

    db.execute(
        """
        CREATE TABLE users (
            id INT
        );
        """
    )

    db.save()

    # Remove history to simulate an older V1 database.
    import json

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    data.pop(
        "history",
        None
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2
        )

    restored = Database(
        file_path=file_path
    )

    assert (
        restored.history.current_version_id
        == 0
    )

    assert (
        restored.list_tables()
        == ["users"]
    )

def test_mutation_version_stores_original_sql(tmp_path):
    """
    A SQL mutation should store its exact SQL statement in the
    resulting historical version.
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

    version = db.get_current_version()

    assert (
        version.sql
        == "INSERT INTO users VALUES (1, 'Aditya');"
    )