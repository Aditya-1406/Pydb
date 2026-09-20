from copy import deepcopy


class Version:
    """
    Represents one historical database state.

    A Version is treated as immutable historical information.

    Each normal version contains:

        version_id
        parent_version_id
        branch_name
        operation
        timestamp
        state
        sql

    A merge version can additionally contain:

        merge_parent_version_id

    The normal parent represents the branch being advanced.

    The merge parent represents the source branch version that
    was incorporated into the merge.

    The state is a serialized representation of the database,
    not a live Database object.
    """

    def __init__(
        self,
        version_id,
        parent_version_id,
        branch_name,
        operation,
        timestamp,
        state,
        sql=None,
        merge_parent_version_id=None
    ):
        """
        Create a new Version object.

        sql:
            Original SQL statement responsible for this version,
            when available.

        merge_parent_version_id:
            Second parent used by merge versions.
        """
        self.version_id = version_id
        self.parent_version_id = parent_version_id
        self.branch_name = branch_name
        self.operation = operation
        self.timestamp = timestamp
        self.sql = sql

        # A merge version has two parents.
        #
        # Normal versions leave this as None.
        self.merge_parent_version_id = (
            merge_parent_version_id
        )

        # Deep-copy the state so later database mutations cannot
        # accidentally modify this historical version.
        self.state = deepcopy(state)

    def to_dict(self):
        """
        Convert the Version into a serializable dictionary.

        Optional metadata is only written when it exists so that
        older history files remain compatible.
        """
        data = {
            "version_id": self.version_id,
            "parent_version_id": self.parent_version_id,
            "branch_name": self.branch_name,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "state": deepcopy(self.state)
        }

        if self.sql is not None:
            data["sql"] = self.sql

        if self.merge_parent_version_id is not None:
            data["merge_parent_version_id"] = (
                self.merge_parent_version_id
            )

        return data

    @classmethod
    def from_dict(cls, data):
        """
        Reconstruct a Version from stored dictionary data.

        Older persisted versions may not contain:

            sql
            merge_parent_version_id

        Both therefore default to None.
        """
        return cls(
            version_id=data["version_id"],
            parent_version_id=data.get(
                "parent_version_id"
            ),
            branch_name=data.get(
                "branch_name",
                "main"
            ),
            operation=data.get(
                "operation",
                "UNKNOWN"
            ),
            timestamp=data.get(
                "timestamp"
            ),
            state=data.get(
                "state",
                {}
            ),
            sql=data.get(
                "sql"
            ),
            merge_parent_version_id=data.get(
                "merge_parent_version_id"
            )
        )

    def __repr__(self):
        """
        Return a readable representation for debugging.
        """
        return (
            "Version("
            f"id={self.version_id!r}, "
            f"parent={self.parent_version_id!r}, "
            f"merge_parent={self.merge_parent_version_id!r}, "
            f"branch={self.branch_name!r}, "
            f"operation={self.operation!r}, "
            f"sql={self.sql!r}"
            ")"
        )