from copy import deepcopy
from datetime import datetime, timezone

from pydb.version import Version


class HistoryManager:
    """
    Maintains the committed version history of a database.

    V2 currently supports:

        version history
        checkout
        branches
        merge-parent metadata

    A branch points to a version and represents an independent
    line of database evolution.

    The default branch is:

        main
    """

    def __init__(
        self,
        versions=None,
        current_version_id=None,
        branches=None,
        current_branch="main"
    ):
        """
        Initialize the history manager.

        branches:
            Optional mapping of branch names to their latest
            version IDs.

        current_branch:
            Name of the branch currently being used.

        Older persisted histories may not contain branch metadata.
        In that case, the manager reconstructs a single 'main'
        branch automatically.
        """
        self.versions = {}

        if versions:
            for version in versions:
                if isinstance(
                    version,
                    Version
                ):
                    self.versions[
                        version.version_id
                    ] = version
                else:
                    version_object = Version.from_dict(
                        version
                    )

                    self.versions[
                        version_object.version_id
                    ] = version_object

        self.current_version_id = (
            current_version_id
        )

        # --------------------------------------------------
        # Branch state
        # --------------------------------------------------

        self.branches = {}

        if branches:
            self.branches = {
                branch_name: version_id
                for branch_name, version_id
                in branches.items()
            }

        elif self.versions:
            # --------------------------------------------------
            # Backward compatibility.
            # --------------------------------------------------

            self.branches = {
                "main": max(
                    self.versions.keys()
                )
            }

        else:
            self.branches = {}

        self.current_branch = (
            current_branch
            if current_branch in self.branches
            else "main"
        )

        if (
            self.current_branch not in self.branches
            and "main" in self.branches
        ):
            self.current_branch = "main"

    # ======================================================
    # INITIALIZATION
    # ======================================================

    def initialize(
        self,
        state,
        branch_name="main",
        operation="INITIAL"
    ):
        """
        Create Version 0 when no history exists.

        Version 0 represents the database state from which
        version tracking begins.
        """
        if self.versions:
            return self.current_version_id

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        version = Version(
            version_id=0,
            parent_version_id=None,
            branch_name=branch_name,
            operation=operation,
            timestamp=timestamp,
            state=state
        )

        self.versions[0] = version

        self.branches = {
            branch_name: 0
        }

        self.current_branch = branch_name
        self.current_version_id = 0

        return 0

    # ======================================================
    # VERSION CREATION
    # ======================================================

    def create_version(
        self,
        state,
        operation,
        branch_name=None,
        parent_version_id=None,
        sql=None,
        merge_parent_version_id=None
    ):
        """
        Create a new committed database version.

        When branch_name is omitted, the current branch is used.

        When parent_version_id is omitted, the current historical
        version becomes the primary parent.

        sql:
            Original SQL responsible for this version.

        merge_parent_version_id:
            Optional second parent for a merge version.

        The new version becomes the head of the selected branch.
        """
        # --------------------------------------------------
        # Resolve branch.
        # --------------------------------------------------

        if branch_name is None:
            branch_name = self.current_branch

        # --------------------------------------------------
        # Resolve parent.
        # --------------------------------------------------

        if parent_version_id is None:
            parent_version_id = (
                self.current_version_id
            )

        # --------------------------------------------------
        # Validate branch.
        # --------------------------------------------------

        if branch_name not in self.branches:
            raise ValueError(
                f"Branch '{branch_name}' does not exist"
            )

        # --------------------------------------------------
        # Validate merge parent.
        # --------------------------------------------------

        if merge_parent_version_id is not None:

            if merge_parent_version_id not in self.versions:
                raise ValueError(
                    f"Version '{merge_parent_version_id}' "
                    f"does not exist"
                )

            if (
                merge_parent_version_id
                == parent_version_id
            ):
                raise ValueError(
                    "Merge parent cannot be the same "
                    "as the primary parent"
                )

        # --------------------------------------------------
        # Generate the next globally unique version ID.
        # --------------------------------------------------

        if not self.versions:
            version_id = 0
        else:
            version_id = max(
                self.versions.keys()
            ) + 1

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        version = Version(
            version_id=version_id,
            parent_version_id=parent_version_id,
            branch_name=branch_name,
            operation=operation,
            timestamp=timestamp,
            state=state,
            sql=sql,
            merge_parent_version_id=(
                merge_parent_version_id
            )
        )

        self.versions[version_id] = version

        # New version becomes the branch head.
        self.branches[branch_name] = version_id

        self.current_branch = branch_name
        self.current_version_id = version_id

        return version

    # ======================================================
    # BRANCH OPERATIONS
    # ======================================================

    def create_branch(
        self,
        branch_name,
        from_version_id=None
    ):
        """
        Create a new branch starting from an existing version.

        The new branch initially points to the selected version.

        Creating a branch does not switch the active branch.
        """
        if not isinstance(
            branch_name,
            str
        ):
            raise ValueError(
                "Branch name must be a string"
            )

        branch_name = branch_name.strip()

        if not branch_name:
            raise ValueError(
                "Branch name cannot be empty"
            )

        if branch_name in self.branches:
            raise ValueError(
                f"Branch '{branch_name}' already exists"
            )

        if from_version_id is None:
            from_version_id = (
                self.current_version_id
            )

        if from_version_id not in self.versions:
            raise ValueError(
                f"Version '{from_version_id}' does not exist"
            )

        self.branches[branch_name] = (
            from_version_id
        )

        return branch_name

    def switch_branch(self, branch_name):
        """
        Switch to an existing branch.

        Switching a branch moves the active historical position
        to that branch's current head version.

        The actual table state is restored by Database.
        """
        if branch_name not in self.branches:
            raise ValueError(
                f"Branch '{branch_name}' does not exist"
            )

        self.current_branch = branch_name

        self.current_version_id = (
            self.branches[branch_name]
        )

        return self.current_version_id

    def get_branches(self):
        """
        Return branch names and their current head versions.

        A new dictionary is returned so callers cannot accidentally
        modify internal branch metadata.
        """
        return dict(
            self.branches
        )

    def get_current_branch(self):
        """
        Return the name of the active branch.
        """
        return self.current_branch

    def get_branch_head(self, branch_name=None):
        """
        Return the version at the head of a branch.

        When branch_name is omitted, the active branch is used.
        """
        if branch_name is None:
            branch_name = self.current_branch

        if branch_name not in self.branches:
            raise ValueError(
                f"Branch '{branch_name}' does not exist"
            )

        return self.branches[branch_name]

    def is_at_branch_head(self):
        """
        Return True when the active historical position is equal
        to the active branch's head.
        """
        if self.current_branch not in self.branches:
            return False

        return (
            self.current_version_id
            == self.branches[
                self.current_branch
            ]
        )

    # ======================================================
    # CHECKOUT
    # ======================================================

    def checkout(self, version_id):
        """
        Move the active historical position to a specific version.

        Checkout does not change branch metadata.
        """
        if version_id not in self.versions:
            raise ValueError(
                f"Version '{version_id}' does not exist"
            )

        self.current_version_id = version_id

        return self.versions[version_id]

    # ======================================================
    # VERSION LOOKUP
    # ======================================================

    def get_version(self, version_id):
        """
        Return a specific Version.

        Raises:
            ValueError:
                If the version does not exist.
        """
        if version_id not in self.versions:
            raise ValueError(
                f"Version '{version_id}' does not exist"
            )

        return self.versions[version_id]

    def get_current_version(self):
        """
        Return the current version.
        """
        if self.current_version_id is None:
            return None

        return self.get_version(
            self.current_version_id
        )

    def get_history(self):
        """
        Return versions in ascending version order.
        """
        return [
            self.versions[version_id]
            for version_id in sorted(
                self.versions.keys()
            )
        ]

    # ======================================================
    # PERSISTENCE
    # ======================================================

    def to_dict(self):
        """
        Convert history into a serializable dictionary.

        Branch metadata is persisted once branching is being used.
        Merge-parent metadata is stored inside each Version.
        """
        data = {
            "current_version_id": (
                self.current_version_id
            ),
            "versions": [
                version.to_dict()
                for version in self.get_history()
            ]
        }

        if (
            len(self.branches) > 1
            or self.current_branch != "main"
        ):
            data["branches"] = dict(
                self.branches
            )

            data["current_branch"] = (
                self.current_branch
            )

        return data

    @classmethod
    def from_dict(cls, data):
        """
        Reconstruct a HistoryManager from persisted data.

        Older V2 history files without branch or merge-parent
        metadata remain compatible.
        """
        if not data:
            return cls()

        versions = [
            Version.from_dict(version_data)
            for version_data in data.get(
                "versions",
                []
            )
        ]

        return cls(
            versions=versions,
            current_version_id=data.get(
                "current_version_id"
            ),
            branches=data.get(
                "branches"
            ),
            current_branch=data.get(
                "current_branch",
                "main"
            )
        )