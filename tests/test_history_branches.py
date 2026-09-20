from pydb.history import HistoryManager


def test_initialize_creates_main_branch():
    """
    Initializing history should create main at Version 0.
    """
    history = HistoryManager()

    history.initialize(
        state={
            "tables": {}
        }
    )

    assert history.get_current_branch() == "main"

    assert history.get_branch_head(
        "main"
    ) == 0

    assert history.current_version_id == 0


def test_create_branch_from_current_version():
    """
    A branch should initially point to the current version.
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

    history.create_branch(
        "experiment"
    )

    assert history.get_branch_head(
        "experiment"
    ) == 1

    assert history.get_current_branch() == "main"


def test_switch_branch_moves_to_branch_head():
    """
    Switching branches should move the active historical position
    to the selected branch head.
    """
    history = HistoryManager()

    history.initialize(
        state={}
    )

    history.create_version(
        state={
            "tables": {
                "users": {}
            }
        },
        operation="CREATE TABLE users"
    )

    history.create_branch(
        "experiment"
    )

    history.switch_branch(
        "experiment"
    )

    assert history.get_current_branch() == "experiment"

    assert history.current_version_id == 1


def test_new_version_updates_active_branch_head():
    """
    A new version should become the head of the active branch.
    """
    history = HistoryManager()

    history.initialize(
        state={}
    )

    history.create_version(
        state={
            "tables": {
                "users": {}
            }
        },
        operation="CREATE TABLE users"
    )

    history.create_branch(
        "experiment"
    )

    history.switch_branch(
        "experiment"
    )

    version = history.create_version(
        state={
            "tables": {
                "users": {
                    "rows": 1
                }
            }
        },
        operation="INSERT INTO users"
    )

    assert version.parent_version_id == 1

    assert version.branch_name == "experiment"

    assert history.get_branch_head(
        "experiment"
    ) == version.version_id

    assert history.get_current_branch() == "experiment"


def test_main_branch_head_is_preserved():
    """
    Creating and advancing another branch should not move main's
    branch head.
    """
    history = HistoryManager()

    history.initialize(
        state={}
    )

    history.create_version(
        state={},
        operation="CREATE TABLE users"
    )

    history.create_branch(
        "experiment"
    )

    history.switch_branch(
        "experiment"
    )

    history.create_version(
        state={},
        operation="INSERT INTO users"
    )

    assert history.get_branch_head(
        "main"
    ) == 1

    assert history.get_branch_head(
        "experiment"
    ) == 2


def test_checkout_does_not_move_branch_head():
    """
    Checkout should move only the current historical position.

    The branch head remains where the branch was last advanced.
    """
    history = HistoryManager()

    history.initialize(
        state={}
    )

    history.create_version(
        state={},
        operation="CREATE TABLE users"
    )

    history.create_version(
        state={},
        operation="INSERT INTO users"
    )

    assert history.get_branch_head(
        "main"
    ) == 2

    history.checkout(1)

    assert history.current_version_id == 1

    assert history.get_branch_head(
        "main"
    ) == 2

    assert not history.is_at_branch_head()


def test_branch_metadata_round_trip():
    """
    Branch metadata should survive serialization.
    """
    history = HistoryManager()

    history.initialize(
        state={}
    )

    history.create_version(
        state={},
        operation="CREATE TABLE users"
    )

    history.create_branch(
        "experiment"
    )

    history.switch_branch(
        "experiment"
    )

    history.create_version(
        state={},
        operation="INSERT INTO users"
    )

    data = history.to_dict()

    restored = HistoryManager.from_dict(
        data
    )

    assert restored.get_branches() == {
        "main": 1,
        "experiment": 2
    }

    assert (
        restored.get_current_branch()
        == "experiment"
    )

    assert (
        restored.current_version_id
        == 2
    )


def test_old_history_without_branch_metadata_remains_compatible():
    """
    A history created before branch support should load as a
    single main branch.
    """
    history = HistoryManager.from_dict(
        {
            "current_version_id": 2,
            "versions": [
                {
                    "version_id": 0,
                    "parent_version_id": None,
                    "branch_name": "main",
                    "operation": "INITIAL",
                    "timestamp": "timestamp-0",
                    "state": {}
                },
                {
                    "version_id": 1,
                    "parent_version_id": 0,
                    "branch_name": "main",
                    "operation": "CREATE TABLE users",
                    "timestamp": "timestamp-1",
                    "state": {}
                },
                {
                    "version_id": 2,
                    "parent_version_id": 1,
                    "branch_name": "main",
                    "operation": "INSERT INTO users",
                    "timestamp": "timestamp-2",
                    "state": {}
                }
            ]
        }
    )

    assert history.get_branches() == {
        "main": 2
    }

    assert history.get_current_branch() == "main"

    assert history.current_version_id == 2