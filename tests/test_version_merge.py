from pydb.version import Version


def test_merge_parent_round_trip():
    """
    A merge version should preserve its second parent through
    serialization.
    """
    version = Version(
        version_id=5,
        parent_version_id=2,
        branch_name="main",
        operation="MERGE experiment INTO main",
        timestamp="timestamp",
        state={
            "tables": {}
        },
        merge_parent_version_id=4
    )

    data = version.to_dict()

    assert (
        data["merge_parent_version_id"]
        == 4
    )

    restored = Version.from_dict(
        data
    )

    assert (
        restored.merge_parent_version_id
        == 4
    )


def test_old_version_without_merge_parent_is_compatible():
    """
    Versions created before merge support should load normally.
    """
    version = Version.from_dict(
        {
            "version_id": 2,
            "parent_version_id": 1,
            "branch_name": "main",
            "operation": "INSERT INTO users",
            "timestamp": "timestamp",
            "state": {
                "tables": {}
            }
        }
    )

    assert (
        version.merge_parent_version_id
        is None
    )