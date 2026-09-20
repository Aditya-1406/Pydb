from pydb.version import Version


def test_version_round_trip():
    """
    Version objects should serialize and reconstruct correctly.
    """
    version = Version(
        version_id=3,
        parent_version_id=2,
        branch_name="main",
        operation="INSERT INTO users",
        timestamp="2026-09-20T12:00:00+00:00",
        state={
            "tables": {
                "users": {
                    "rows": [
                        [1, "Aditya"]
                    ]
                }
            }
        }
    )

    data = version.to_dict()

    restored = Version.from_dict(
        data
    )

    assert restored.version_id == 3
    assert restored.parent_version_id == 2
    assert restored.branch_name == "main"
    assert restored.operation == (
        "INSERT INTO users"
    )
    assert restored.state == (
        version.state
    )

def test_version_stores_sql():
    """
    Version should preserve the original SQL statement.
    """
    version = Version(
        version_id=1,
        parent_version_id=0,
        branch_name="main",
        operation="INSERT INTO users",
        timestamp="timestamp",
        state={
            "tables": {}
        },
        sql="INSERT INTO users VALUES (1, 'Aditya');"
    )

    assert (
        version.sql
        == "INSERT INTO users VALUES (1, 'Aditya');"
    )


def test_version_sql_round_trip():
    """
    SQL should survive serialization and reconstruction.
    """
    original = Version(
        version_id=1,
        parent_version_id=0,
        branch_name="main",
        operation="INSERT INTO users",
        timestamp="timestamp",
        state={
            "tables": {}
        },
        sql="INSERT INTO users VALUES (1, 'Aditya');"
    )

    restored = Version.from_dict(
        original.to_dict()
    )

    assert (
        restored.sql
        == "INSERT INTO users VALUES (1, 'Aditya');"
    )


def test_old_version_without_sql_remains_compatible():
    """
    Versions created before SQL replay support should load with
    sql=None.
    """
    version = Version.from_dict(
        {
            "version_id": 1,
            "parent_version_id": 0,
            "branch_name": "main",
            "operation": "INSERT INTO users",
            "timestamp": "timestamp",
            "state": {
                "tables": {}
            }
        }
    )

    assert version.sql is None


def test_version_without_sql_preserves_old_serialized_shape():
    """
    A version without SQL should not require an sql field in its
    serialized representation.
    """
    version = Version(
        version_id=1,
        parent_version_id=0,
        branch_name="main",
        operation="INSERT INTO users",
        timestamp="timestamp",
        state={
            "tables": {}
        }
    )

    data = version.to_dict()

    assert "sql" not in data