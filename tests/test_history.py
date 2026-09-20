from pydb.history import HistoryManager


def test_history_initial_version():
    """
    A new history should begin at Version 0.
    """
    history = HistoryManager()

    version_id = history.initialize(
        state={
            "tables": {}
        }
    )

    assert version_id == 0
    assert history.current_version_id == 0

    version = history.get_version(0)

    assert version.operation == "INITIAL"
    assert version.parent_version_id is None
    assert version.branch_name == "main"


def test_history_creates_child_version():
    """
    New versions should point to the previous version.
    """
    history = HistoryManager()

    history.initialize(
        state={
            "tables": {}
        }
    )

    version = history.create_version(
        state={
            "tables": {
                "users": {}
            }
        },
        operation="CREATE TABLE users"
    )

    assert version.version_id == 1
    assert version.parent_version_id == 0
    assert history.current_version_id == 1


def test_history_returns_versions_in_order():
    """
    History should return versions in ascending ID order.
    """
    history = HistoryManager()

    history.initialize(
        state={
            "tables": {}
        }
    )

    history.create_version(
        state={
            "tables": {}
        },
        operation="VERSION 1"
    )

    history.create_version(
        state={
            "tables": {}
        },
        operation="VERSION 2"
    )

    versions = history.get_history()

    assert [
        version.version_id
        for version in versions
    ] == [0, 1, 2]


def test_history_round_trip():
    """
    History metadata should survive serialization.
    """
    history = HistoryManager()

    history.initialize(
        state={
            "tables": {}
        }
    )

    history.create_version(
        state={
            "tables": {
                "users": {}
            }
        },
        operation="CREATE TABLE users"
    )

    data = history.to_dict()

    restored = (
        HistoryManager.from_dict(
            data
        )
    )

    assert restored.current_version_id == 1

    versions = restored.get_history()

    assert len(versions) == 2
    assert versions[1].operation == (
        "CREATE TABLE users"
    )