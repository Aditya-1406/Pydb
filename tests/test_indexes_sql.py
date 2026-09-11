from pydb.database import Database
from pydb.query import (
    CreateIndexQuery,
    DropIndexQuery
)


def test_create_hash_index(tmp_path):
    """
    CREATE INDEX should create a named hash index.
    """
    db = Database(
        file_path=str(tmp_path / "db.json")
    )

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    result = db.execute(
        "CREATE INDEX age_idx ON users(age);"
    )

    assert result is None

    table = db.get_table("users")

    assert "age" in table.indexes

    assert table.has_named_index(
        "age_idx"
    )

    assert table.index_definitions[
        "age_idx"
    ] == {
        "type": "HASH",
        "column": "age"
    }


def test_create_btree_index(tmp_path):
    """
    CREATE INDEX ... USING BTREE should create a B+Tree index.
    """
    db = Database(
        file_path=str(tmp_path / "db.json")
    )

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    db.execute(
        "CREATE INDEX age_idx "
        "ON users(age) USING BTREE;"
    )

    table = db.get_table("users")

    assert "age" in table.bplus_indexes

    assert table.has_named_index(
        "age_idx"
    )

    assert table.index_definitions[
        "age_idx"
    ] == {
        "type": "BTREE",
        "column": "age"
    }


def test_create_index_defaults_to_hash(tmp_path):
    """
    CREATE INDEX without USING defaults to HASH.
    """
    db = Database(
        file_path=str(tmp_path / "db.json")
    )

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    db.execute(
        "CREATE INDEX age_idx ON users(age);"
    )

    table = db.get_table("users")

    assert "age" in table.indexes


def test_drop_index(tmp_path):
    """
    DROP INDEX should remove the named index.
    """
    db = Database(
        file_path=str(tmp_path / "db.json")
    )

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    db.execute(
        "CREATE INDEX age_idx ON users(age);"
    )

    db.execute(
        "DROP INDEX age_idx;"
    )

    table = db.get_table("users")

    assert "age" not in table.indexes

    assert not table.has_named_index(
        "age_idx"
    )


def test_index_persistence(tmp_path):
    """
    Named indexes should survive persistence and reload.
    """
    file_path = str(
        tmp_path / "db.json"
    )

    db = Database(
        file_path=file_path
    )

    db.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    db.execute(
        "CREATE INDEX age_idx "
        "ON users(age) USING BTREE;"
    )

    db.save()

    db2 = Database(
        file_path=file_path
    )

    table = db2.get_table(
        "users"
    )

    assert table.has_named_index(
        "age_idx"
    )

    assert "age" in table.bplus_indexes