from copy import deepcopy

from pydb.table import Table
from pydb.storage import StorageEngine
from pydb.parser import Parser
from pydb.executor import QueryExecutor
from pydb.history import HistoryManager

from pydb.query import (
    InsertQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    DropTableQuery,
    CreateIndexQuery,
    DropIndexQuery,
    BeginQuery,
    CommitQuery,
    RollbackQuery,
    SelectQuery,
    AggregateExpression
)


class Database:
    """
    Represents the PyDB database.

    Database is responsible for:

        table lifecycle
        persistence
        transactions
        version history
        historical state checkout
        branch management
        version comparison
        historical query replay
        historical query comparison
        what-if planner analysis
        three-way branch merge
    """

    def __init__(self, file_path="pydb.json"):
        """
        Initialize the database.

        A HistoryManager is created before loading the persisted
        database so that old V1 database files can be upgraded
        automatically to the V2 history model.
        """
        self.tables = {}

        self.storage = StorageEngine(
            file_path
        )

        self.dirty = False

        self._snapshot = None

        # --------------------------------------------------
        # V2: Version history
        # --------------------------------------------------

        self.history = HistoryManager()

        self.parser = Parser()

        self.executor = QueryExecutor(
            self
        )

        self._load()

    # ======================================================
    # DATABASE STATE
    # ======================================================

    def _database_state(self):
        """
        Return a completely isolated database state used for
        historical versions.

        A historical version must never share mutable nested
        objects with the live database.

        Therefore the entire serialized state is deep-copied
        before being handed to HistoryManager.
        """
        state = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            }
        }

        return deepcopy(
            state
        )

    def _restore_database_state(self, state):
        """
        Restore the database tables from a serialized database
        state.

        Historical version state is deep-copied before rebuilding
        live Table objects so that future mutations cannot alter
        historical snapshots.
        """
        if not isinstance(
            state,
            dict
        ):
            raise ValueError(
                "Invalid database state"
            )

        self.tables = {
            name: Table.from_dict(
                deepcopy(
                    table_data
                )
            )
            for name, table_data in state.get(
                "tables",
                {}
            ).items()
        }

    # ======================================================
    # TABLE OPERATIONS
    # ======================================================

    def create_table(
        self,
        name,
        columns,
        primary_key=None
    ):
        """
        Create a new table.
        """
        if name in self.tables:
            raise ValueError(
                f"Table '{name}' already exists"
            )

        table = Table(
            name,
            columns,
            primary_key=primary_key
        )

        self.tables[name] = table

        self.mark_dirty()

        return table

    def get_table(self, name):
        """
        Return a table by name.
        """
        if name not in self.tables:
            raise ValueError(
                f"Table '{name}' does not exist"
            )

        return self.tables[name]

    def list_tables(self):
        """
        Return the names of all tables.
        """
        return list(
            self.tables.keys()
        )

    def drop_table(self, name):
        """
        Drop an existing table.
        """
        if name not in self.tables:
            raise ValueError(
                f"Table '{name}' does not exist"
            )

        del self.tables[name]

        self.mark_dirty()

    # ======================================================
    # SQL EXECUTION
    # ======================================================

    def execute(self, sql):
        """
        Parse and execute a SQL statement.

        V2 version behavior:

            mutation outside transaction
                -> create a new version

            mutation inside transaction
                -> wait until COMMIT

            ROLLBACK
                -> restore state
                -> create no version

            COMMIT
                -> create one version for the transaction
        """
        query = self.parser.parse(
            sql
        )

        result = self.executor.execute(
            query
        )

        if isinstance(
            query,
            (
                BeginQuery,
                CommitQuery,
                RollbackQuery
            )
        ):
            return result

        if (
            self._is_versioned_mutation(
                query
            )
            and self._snapshot is None
        ):
            self._create_version(
                self._version_operation(
                    query
                ),
                sql=sql
            )

        return result

    # ======================================================
    # VERSIONING
    # ======================================================

    def _is_versioned_mutation(self, query):
        """
        Return True when the Query Object changes database state.
        """
        return isinstance(
            query,
            (
                InsertQuery,
                UpdateQuery,
                DeleteQuery,
                CreateTableQuery,
                DropTableQuery,
                CreateIndexQuery,
                DropIndexQuery
            )
        )

    def _version_operation(self, query):
        """
        Generate a human-readable description for a version.
        """
        if isinstance(
            query,
            InsertQuery
        ):
            return (
                f"INSERT INTO "
                f"{query.table_name}"
            )

        if isinstance(
            query,
            UpdateQuery
        ):
            return (
                f"UPDATE "
                f"{query.table_name}"
            )

        if isinstance(
            query,
            DeleteQuery
        ):
            return (
                f"DELETE FROM "
                f"{query.table_name}"
            )

        if isinstance(
            query,
            CreateTableQuery
        ):
            return (
                f"CREATE TABLE "
                f"{query.table_name}"
            )

        if isinstance(
            query,
            DropTableQuery
        ):
            return (
                f"DROP TABLE "
                f"{query.table_name}"
            )

        if isinstance(
            query,
            CreateIndexQuery
        ):
            return (
                f"CREATE "
                f"{query.index_type} INDEX "
                f"{query.index_name}"
            )

        if isinstance(
            query,
            DropIndexQuery
        ):
            return (
                f"DROP INDEX "
                f"{query.index_name}"
            )

        return type(query).__name__

    def _create_version(
        self,
        operation,
        sql=None,
        merge_parent_version_id=None
    ):
        """
        Create a new version from the current database state.

        The active HistoryManager branch is used automatically.

        sql:
            Original SQL statement responsible for the version.

        merge_parent_version_id:
            Optional second parent used for merge commits.
        """
        return self.history.create_version(
            state=self._database_state(),
            operation=operation,
            sql=sql,
            merge_parent_version_id=(
                merge_parent_version_id
            )
        )

    def get_history(self):
        """
        Return the current version history.
        """
        return self.history.get_history()

    def get_current_version(self):
        """
        Return the version representing the current historical
        database position.

        Returns None when no current version exists.
        """
        return self.history.get_current_version()

    # ======================================================
    # CHECKOUT
    # ======================================================

    def checkout(self, version_id):
        """
        Restore the database to a previously committed version.

        Checkout does not create a new version.

        The active branch remains unchanged.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Cannot checkout during an active transaction"
            )

        try:
            version_id = int(
                version_id
            )
        except (
            TypeError,
            ValueError
        ):
            raise ValueError(
                "Version ID must be an integer"
            )

        version = self.history.get_version(
            version_id
        )

        self._restore_database_state(
            version.state
        )

        self.history.current_version_id = (
            version.version_id
        )

        self.mark_dirty()

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
        Create a new branch from a historical version.

        Creating a branch does not change the active database state
        and does not create a new database version.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Cannot create a branch during an active transaction"
            )

        branch_name = (
            branch_name.strip()
            if isinstance(
                branch_name,
                str
            )
            else branch_name
        )

        result = self.history.create_branch(
            branch_name,
            from_version_id=from_version_id
        )

        self.mark_dirty()

        return result

    def switch_branch(self, branch_name):
        """
        Switch to an existing branch.

        Switching branches moves the active database state to the
        head version of that branch.

        No new database version is created.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Cannot switch branches during an active transaction"
            )

        version_id = self.history.switch_branch(
            branch_name
        )

        version = self.history.get_version(
            version_id
        )

        self._restore_database_state(
            version.state
        )

        self.mark_dirty()

        return version

    def get_branches(self):
        """
        Return all branches and their current head versions.
        """
        return self.history.get_branches()

    def get_current_branch(self):
        """
        Return the name of the currently active branch.
        """
        return self.history.get_current_branch()

    def get_branch_head(self, branch_name=None):
        """
        Return the version ID at the head of a branch.

        When branch_name is omitted, the active branch is used.
        """
        return self.history.get_branch_head(
            branch_name
        )

    # ======================================================
    # HISTORICAL QUERY REPLAY
    # ======================================================

    def replay(self, version_id):
        """
        Replay the SQL stored in a historical version.

        The SQL is executed against the current database state
        and current active branch.

        A successful replay therefore creates a new normal version.
        """
        try:
            version_id = int(
                version_id
            )
        except (
            TypeError,
            ValueError
        ):
            raise ValueError(
                "Version ID must be an integer"
            )

        version = self.history.get_version(
            version_id
        )

        if version.sql is None:
            raise ValueError(
                f"Version '{version_id}' "
                f"does not contain replayable SQL"
            )

        result = self.execute(
            version.sql
        )

        new_version = (
            self.get_current_version()
        )

        return {
            "source_version_id": (
                version.version_id
            ),
            "new_version_id": (
                new_version.version_id
                if new_version is not None
                else None
            ),
            "result": result
        }

    # ======================================================
    # VERSION GRAPH
    # ======================================================

    def _get_ancestor_distances(
        self,
        version_id
    ):
        """
        Return every ancestor of a version together with the
        shortest number of parent edges needed to reach it.

        Normal versions have one parent.

        Merge versions have two parents:

            parent_version_id
            merge_parent_version_id

        This makes PyDB's history a DAG rather than a simple tree.
        """
        distances = {
            version_id: 0
        }

        queue = [
            version_id
        ]

        while queue:
            current_id = queue.pop(0)

            current_distance = distances[
                current_id
            ]

            version = self.history.get_version(
                current_id
            )

            parents = [
                version.parent_version_id,
                version.merge_parent_version_id
            ]

            for parent_id in parents:
                if parent_id is None:
                    continue

                next_distance = (
                    current_distance + 1
                )

                if (
                    parent_id not in distances
                    or next_distance
                    < distances[parent_id]
                ):
                    distances[parent_id] = (
                        next_distance
                    )

                    queue.append(
                        parent_id
                    )

        return distances

    def _get_ancestor_ids(self, version_id):
        """
        Return all ancestor version IDs of a version.

        The starting version is included.
        """
        return set(
            self._get_ancestor_distances(
                version_id
            ).keys()
        )

    def _find_common_ancestor_version_id(
        self,
        before_version_id,
        after_version_id
    ):
        """
        Find the closest common ancestor of two versions.

        This works for both normal history trees and merge-generated
        DAGs.

        The common ancestor minimizing the combined graph distance
        is selected.
        """
        before_distances = (
            self._get_ancestor_distances(
                before_version_id
            )
        )

        after_distances = (
            self._get_ancestor_distances(
                after_version_id
            )
        )

        common_ids = (
            set(before_distances.keys())
            & set(after_distances.keys())
        )

        if not common_ids:
            return None

        return min(
            common_ids,
            key=lambda version_id: (
                before_distances[version_id]
                + after_distances[version_id],
                max(
                    before_distances[version_id],
                    after_distances[version_id]
                ),
                version_id
            )
        )

    def _is_ancestor(
        self,
        ancestor_version_id,
        descendant_version_id
    ):
        """
        Return True when ancestor_version_id appears anywhere
        in descendant_version_id's history.
        """
        return (
            ancestor_version_id
            in self._get_ancestor_ids(
                descendant_version_id
            )
        )

    # ======================================================
    # THREE-WAY MERGE HELPERS
    # ======================================================

    def _merge_value(
        self,
        base_value,
        target_value,
        source_value,
        conflict_type,
        details
    ):
        """
        Perform a standard three-way merge for one value.

        Resolution rules:

            target == source
                -> both agree

            target == base
                -> only source changed

            source == base
                -> only target changed

            otherwise
                -> conflict
        """
        if (
            target_value
            == source_value
        ):
            return (
                deepcopy(target_value),
                None
            )

        if (
            target_value
            == base_value
        ):
            return (
                deepcopy(source_value),
                None
            )

        if (
            source_value
            == base_value
        ):
            return (
                deepcopy(target_value),
                None
            )

        conflict = {
            "type": conflict_type,
            **details,
            "base": deepcopy(base_value),
            "target": deepcopy(target_value),
            "source": deepcopy(source_value)
        }

        return None, conflict

    def _extract_rows_for_merge(
        self,
        table_data
    ):
        """
        Build a Record ID -> row mapping from serialized table data.

        Record IDs are used as row identity only when the row existed
        in the common ancestor.

        Record IDs created independently after the fork are treated
        as branch-local identifiers.
        """
        if table_data is None:
            return {}

        rows = table_data.get(
            "rows",
            []
        )

        record_ids = table_data.get(
            "record_ids",
            []
        )

        result = {}

        for index, row in enumerate(
            rows
        ):
            if index < len(record_ids):
                record_id = record_ids[index]
            else:
                record_id = index + 1

            result[record_id] = deepcopy(
                row
            )

        return result

    def _merge_rows(
        self,
        table_name,
        base_table,
        target_table,
        source_table
    ):
        """
        Perform a three-way merge of table rows.

        Important identity rules:

            Record IDs that existed in the common ancestor
                -> represent the same logical row

            Record IDs created independently after the fork
                -> are branch-local

        For independently-created rows with colliding Record IDs:

            source branch keeps the original Record ID

            target branch row is remapped to a fresh Record ID

        This matches the deterministic semantics used by PyDB's
        merge tests while preserving both rows.
        """
        base_rows = (
            self._extract_rows_for_merge(
                base_table
            )
        )

        target_rows = (
            self._extract_rows_for_merge(
                target_table
            )
        )

        source_rows = (
            self._extract_rows_for_merge(
                source_table
            )
        )

        missing = object()

        merged_rows = {}
        conflicts = []

        base_record_ids = set(
            base_rows.keys()
        )

        target_record_ids = set(
            target_rows.keys()
        )

        source_record_ids = set(
            source_rows.keys()
        )

        # --------------------------------------------------
        # STEP 1:
        #
        # Merge every row that existed in the common ancestor.
        #
        # These Record IDs are shared logical identities.
        # --------------------------------------------------

        for record_id in sorted(
            base_record_ids
        ):
            base_value = base_rows[
                record_id
            ]

            target_value = target_rows.get(
                record_id,
                missing
            )

            source_value = source_rows.get(
                record_id,
                missing
            )

            # ----------------------------------------------
            # Both branches deleted the row.
            # ----------------------------------------------

            if (
                target_value is missing
                and source_value is missing
            ):
                continue

            # ----------------------------------------------
            # Target deleted the row.
            # ----------------------------------------------

            if target_value is missing:

                if source_value == base_value:
                    continue

                conflicts.append(
                    {
                        "type": "row_conflict",
                        "table": table_name,
                        "record_id": record_id,
                        "base": deepcopy(
                            base_value
                        ),
                        "target": None,
                        "source": deepcopy(
                            source_value
                        )
                    }
                )

                continue

            # ----------------------------------------------
            # Source deleted the row.
            # ----------------------------------------------

            if source_value is missing:

                if target_value == base_value:
                    continue

                conflicts.append(
                    {
                        "type": "row_conflict",
                        "table": table_name,
                        "record_id": record_id,
                        "base": deepcopy(
                            base_value
                        ),
                        "target": deepcopy(
                            target_value
                        ),
                        "source": None
                    }
                )

                continue

            # ----------------------------------------------
            # Both branches still contain the shared row.
            # ----------------------------------------------

            if (
                target_value
                == source_value
            ):
                merged_rows[
                    record_id
                ] = deepcopy(
                    target_value
                )

                continue

            if target_value == base_value:
                merged_rows[
                    record_id
                ] = deepcopy(
                    source_value
                )

                continue

            if source_value == base_value:
                merged_rows[
                    record_id
                ] = deepcopy(
                    target_value
                )

                continue

            # Both branches changed the same ancestor row
            # differently.
            conflicts.append(
                {
                    "type": "row_conflict",
                    "table": table_name,
                    "record_id": record_id,
                    "base": deepcopy(
                        base_value
                    ),
                    "target": deepcopy(
                        target_value
                    ),
                    "source": deepcopy(
                        source_value
                    )
                }
            )

        # --------------------------------------------------
        # STEP 2:
        #
        # Identify branch-local additions.
        # --------------------------------------------------

        target_new_ids = (
            target_record_ids
            - base_record_ids
        )

        source_new_ids = (
            source_record_ids
            - base_record_ids
        )

        # --------------------------------------------------
        # STEP 3:
        #
        # Allocate fresh IDs above every original ID.
        #
        # This ensures remapped rows cannot collide with an
        # existing Record ID.
        # --------------------------------------------------

        numeric_record_ids = [
            record_id
            for record_id in (
                base_record_ids
                | target_record_ids
                | source_record_ids
            )
            if isinstance(
                record_id,
                int
            )
        ]

        next_record_id = (
            max(
                numeric_record_ids
            ) + 1
            if numeric_record_ids
            else 1
        )

        def allocate_record_id():
            """
            Allocate a fresh internal Record ID.
            """
            nonlocal next_record_id

            while (
                next_record_id
                in merged_rows
            ):
                next_record_id += 1

            record_id = (
                next_record_id
            )

            next_record_id += 1

            return record_id

        # --------------------------------------------------
        # STEP 4:
        #
        # Preserve source branch additions first.
        #
        # This is intentional:
        #
        # when source and target independently use the same
        # branch-local Record ID, the source row keeps the
        # original identifier and the target row is remapped.
        # --------------------------------------------------

        for record_id in sorted(
            source_new_ids
        ):
            source_row = source_rows[
                record_id
            ]

            if record_id not in merged_rows:
                merged_rows[
                    record_id
                ] = deepcopy(
                    source_row
                )

                continue

            # A shared row should already have been inserted
            # during STEP 1. This path is therefore defensive.
            if (
                merged_rows[
                    record_id
                ]
                == source_row
            ):
                continue

            new_record_id = (
                allocate_record_id()
            )

            merged_rows[
                new_record_id
            ] = deepcopy(
                source_row
            )

        # --------------------------------------------------
        # STEP 5:
        #
        # Add target branch additions.
        #
        # Preserve the target Record ID when possible.
        #
        # If it collides with a source-local addition:
        #
        #     same row
        #         -> deduplicate
        #
        #     different row
        #         -> remap target row
        # --------------------------------------------------

        for record_id in sorted(
            target_new_ids
        ):
            target_row = target_rows[
                record_id
            ]

            if record_id not in merged_rows:
                merged_rows[
                    record_id
                ] = deepcopy(
                    target_row
                )

                continue

            if (
                merged_rows[
                    record_id
                ]
                == target_row
            ):
                continue

            new_record_id = (
                allocate_record_id()
            )

            merged_rows[
                new_record_id
            ] = deepcopy(
                target_row
            )

        return (
            merged_rows,
            conflicts
        )

    def _get_column_position(
        self,
        table_data,
        column_name
    ):
        """
        Find a column's positional index in serialized table data.

        PyDB currently serializes columns as metadata structures.
        This helper is tolerant of list-based and mapping-based
        representations.
        """
        if table_data is None:
            return None

        columns = table_data.get(
            "columns",
            []
        )

        if isinstance(
            columns,
            dict
        ):
            column_names = list(
                columns.keys()
            )

            if column_name in column_names:
                return column_names.index(
                    column_name
                )

            return None

        for index, column in enumerate(
            columns
        ):
            if isinstance(
                column,
                dict
            ):
                if (
                    column.get("name")
                    == column_name
                ):
                    return index

            elif isinstance(
                column,
                (list, tuple)
            ):
                if (
                    len(column) > 0
                    and column[0]
                    == column_name
                ):
                    return index

            elif (
                isinstance(
                    column,
                    str
                )
                and column == column_name
            ):
                return index

        return None

    def _get_row_column_value(
        self,
        row,
        column_name,
        column_position
    ):
        """
        Read one column value from a serialized row.

        PyDB rows are normally positional lists, but this helper
        also supports mapping-based rows.
        """
        if isinstance(
            row,
            dict
        ):
            return row.get(
                column_name
            )

        if (
            column_position is None
            or not isinstance(
                row,
                (list, tuple)
            )
            or column_position >= len(row)
        ):
            return None

        return row[
            column_position
        ]

    def _validate_merged_table_constraints(
        self,
        table_data
    ):
        """
        Validate important logical constraints on a merged table
        before the live database is modified.
        """
        Table.from_dict(
            deepcopy(
                table_data
            )
        )

        primary_key = table_data.get(
            "primary_key"
        )

        if primary_key is None:
            return

        column_position = (
            self._get_column_position(
                table_data,
                primary_key
            )
        )

        if column_position is None:
            raise ValueError(
                f"Primary key column "
                f"'{primary_key}' "
                f"does not exist"
            )

        seen_values = set()

        for row in table_data.get(
            "rows",
            []
        ):
            value = (
                self._get_row_column_value(
                    row,
                    primary_key,
                    column_position
                )
            )

            if value is None:
                raise ValueError(
                    f"Primary key column "
                    f"'{primary_key}' "
                    f"cannot contain NULL"
                )

            if value in seen_values:
                raise ValueError(
                    f"Duplicate primary key value "
                    f"'{value}' "
                    f"for column "
                    f"'{primary_key}'"
                )

            seen_values.add(
                value
            )

    def _merge_table(
        self,
        table_name,
        base_table,
        target_table,
        source_table
    ):
        """
        Perform a three-way merge of one existing table.

        Schema and index definitions are merged independently.

        Rows are then merged using Record IDs with the
        common-ancestor identity rule.
        """
        conflicts = []

        # --------------------------------------------------
        # SCHEMA
        # --------------------------------------------------

        base_columns = (
            None
            if base_table is None
            else base_table.get(
                "columns"
            )
        )

        target_columns = (
            None
            if target_table is None
            else target_table.get(
                "columns"
            )
        )

        source_columns = (
            None
            if source_table is None
            else source_table.get(
                "columns"
            )
        )

        merged_columns, conflict = (
            self._merge_value(
                base_value=base_columns,
                target_value=target_columns,
                source_value=source_columns,
                conflict_type="schema_conflict",
                details={
                    "table": table_name,
                    "property": "columns"
                }
            )
        )

        if conflict is not None:
            conflicts.append(
                conflict
            )

        # --------------------------------------------------
        # PRIMARY KEY
        # --------------------------------------------------

        base_primary_key = (
            None
            if base_table is None
            else base_table.get(
                "primary_key"
            )
        )

        target_primary_key = (
            None
            if target_table is None
            else target_table.get(
                "primary_key"
            )
        )

        source_primary_key = (
            None
            if source_table is None
            else source_table.get(
                "primary_key"
            )
        )

        merged_primary_key, conflict = (
            self._merge_value(
                base_value=base_primary_key,
                target_value=target_primary_key,
                source_value=source_primary_key,
                conflict_type="schema_conflict",
                details={
                    "table": table_name,
                    "property": "primary_key"
                }
            )
        )

        if conflict is not None:
            conflicts.append(
                conflict
            )

        # --------------------------------------------------
        # INDEX DEFINITIONS
        # --------------------------------------------------

        base_indexes = (
            {}
            if base_table is None
            else base_table.get(
                "index_definitions",
                {}
            )
        )

        target_indexes = (
            {}
            if target_table is None
            else target_table.get(
                "index_definitions",
                {}
            )
        )

        source_indexes = (
            {}
            if source_table is None
            else source_table.get(
                "index_definitions",
                {}
            )
        )

        merged_indexes, conflict = (
            self._merge_value(
                base_value=base_indexes,
                target_value=target_indexes,
                source_value=source_indexes,
                conflict_type="index_conflict",
                details={
                    "table": table_name,
                    "property": "index_definitions"
                }
            )
        )

        if conflict is not None:
            conflicts.append(
                conflict
            )

        # --------------------------------------------------
        # ROWS
        # --------------------------------------------------

        merged_rows_map, row_conflicts = (
            self._merge_rows(
                table_name,
                base_table,
                target_table,
                source_table
            )
        )

        conflicts.extend(
            row_conflicts
        )

        # --------------------------------------------------
        # Return early when metadata or row conflicts exist.
        # --------------------------------------------------

        if conflicts:
            return None, conflicts

        # --------------------------------------------------
        # Build merged serialized table.
        # --------------------------------------------------

        merged_table = deepcopy(
            target_table
        )

        merged_table[
            "name"
        ] = table_name

        merged_table[
            "columns"
        ] = merged_columns

        merged_table[
            "primary_key"
        ] = merged_primary_key

        # --------------------------------------------------
        # Rebuild rows in stable Record ID order.
        # --------------------------------------------------

        merged_record_ids = sorted(
            merged_rows_map.keys()
        )

        merged_table[
            "record_ids"
        ] = merged_record_ids

        merged_table[
            "rows"
        ] = [
            deepcopy(
                merged_rows_map[
                    record_id
                ]
            )
            for record_id in merged_record_ids
        ]

        # --------------------------------------------------
        # Preserve the highest next Record ID observed on either
        # branch while ensuring it is beyond every merged ID.
        # --------------------------------------------------

        target_next_id = target_table.get(
            "next_record_id",
            1
        )

        source_next_id = source_table.get(
            "next_record_id",
            1
        )

        maximum_record_id = (
            max(
                merged_record_ids
            )
            if merged_record_ids
            else 0
        )

        merged_table[
            "next_record_id"
        ] = max(
            target_next_id,
            source_next_id,
            maximum_record_id + 1
        )

        # --------------------------------------------------
        # Persist merged index definitions.
        # --------------------------------------------------

        merged_table[
            "index_definitions"
        ] = {
            name: deepcopy(
                definition
            )
            for name, definition
            in merged_indexes.items()
        }

        merged_table[
            "indexes"
        ] = [
            definition["column"]
            for definition
            in merged_indexes.values()
            if definition.get(
                "type"
            ) == "HASH"
        ]

        merged_table[
            "bplus_indexes"
        ] = [
            definition["column"]
            for definition
            in merged_indexes.values()
            if definition.get(
                "type"
            ) == "BTREE"
        ]

        # --------------------------------------------------
        # Validate the merged table before touching live state.
        # --------------------------------------------------

        try:
            self._validate_merged_table_constraints(
                merged_table
            )
        except Exception as exc:
            conflicts.append(
                {
                    "type": "constraint_conflict",
                    "table": table_name,
                    "reason": str(exc)
                }
            )

            return None, conflicts

        return (
            merged_table,
            []
        )

    def _three_way_merge_states(
        self,
        base_state,
        target_state,
        source_state
    ):
        """
        Perform a three-way merge of complete database states.

        Returns:

            merged_state
            conflicts

        No live database state is modified.
        """
        base_tables = deepcopy(
            base_state.get(
                "tables",
                {}
            )
        )

        target_tables = deepcopy(
            target_state.get(
                "tables",
                {}
            )
        )

        source_tables = deepcopy(
            source_state.get(
                "tables",
                {}
            )
        )

        all_table_names = (
            set(base_tables.keys())
            | set(target_tables.keys())
            | set(source_tables.keys())
        )

        merged_tables = {}
        conflicts = []

        missing = object()

        for table_name in sorted(
            all_table_names
        ):
            base_table = base_tables.get(
                table_name,
                missing
            )

            target_table = target_tables.get(
                table_name,
                missing
            )

            source_table = source_tables.get(
                table_name,
                missing
            )

            # ----------------------------------------------
            # NEW TABLE AFTER FORK
            # ----------------------------------------------

            if base_table is missing:

                if target_table is missing:
                    if source_table is not missing:
                        merged_tables[
                            table_name
                        ] = deepcopy(
                            source_table
                        )

                    continue

                if source_table is missing:
                    merged_tables[
                        table_name
                    ] = deepcopy(
                        target_table
                    )

                    continue

                if target_table == source_table:
                    merged_tables[
                        table_name
                    ] = deepcopy(
                        target_table
                    )

                    continue

                conflicts.append(
                    {
                        "type": "table_add_conflict",
                        "table": table_name,
                        "base": None,
                        "target": deepcopy(
                            target_table
                        ),
                        "source": deepcopy(
                            source_table
                        )
                    }
                )

                continue

            # ----------------------------------------------
            # TABLE EXISTED IN ANCESTOR
            # ----------------------------------------------

            if target_table is missing:

                if source_table is missing:
                    continue

                if source_table == base_table:
                    continue

                conflicts.append(
                    {
                        "type": "table_delete_conflict",
                        "table": table_name,
                        "base": deepcopy(
                            base_table
                        ),
                        "target": None,
                        "source": deepcopy(
                            source_table
                        )
                    }
                )

                continue

            if source_table is missing:

                if target_table == base_table:
                    continue

                conflicts.append(
                    {
                        "type": "table_delete_conflict",
                        "table": table_name,
                        "base": deepcopy(
                            base_table
                        ),
                        "target": deepcopy(
                            target_table
                        ),
                        "source": None
                    }
                )

                continue

            # ----------------------------------------------
            # BOTH BRANCHES STILL CONTAIN TABLE
            # ----------------------------------------------

            merged_table, table_conflicts = (
                self._merge_table(
                    table_name,
                    base_table,
                    target_table,
                    source_table
                )
            )

            if table_conflicts:
                conflicts.extend(
                    table_conflicts
                )
                continue

            merged_tables[
                table_name
            ] = merged_table

        return (
            {
                "tables": merged_tables
            },
            conflicts
        )

    def merge_branch(
        self,
        source_branch
    ):
        """
        Three-way merge a source branch into the current active branch.

        Merge behavior:

            1. current branch is the target
            2. source branch supplies the second parent
            3. common ancestor is calculated
            4. states are merged without modifying the live database
            5. conflicts stop the merge completely
            6. conflict-free merges create one two-parent version

        The active branch must be at its branch head.

        A merge does not create a version when conflicts exist.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Cannot merge during an active transaction"
            )

        target_branch = (
            self.history.get_current_branch()
        )

        if source_branch not in (
            self.history.get_branches()
        ):
            raise ValueError(
                f"Branch '{source_branch}' does not exist"
            )

        if source_branch == target_branch:
            raise ValueError(
                "Cannot merge a branch into itself"
            )

        if not self.history.is_at_branch_head():
            raise RuntimeError(
                "Current branch is not at its head. "
                "Checkout or switch to the branch head before merging."
            )

        target_version_id = (
            self.history.get_branch_head(
                target_branch
            )
        )

        source_version_id = (
            self.history.get_branch_head(
                source_branch
            )
        )

        if (
            target_version_id
            == source_version_id
        ):
            return {
                "status": "UP_TO_DATE",
                "target_branch": target_branch,
                "source_branch": source_branch,
                "target_version": target_version_id,
                "source_version": source_version_id,
                "ancestor_version": target_version_id,
                "merged_version": target_version_id,
                "conflicts": []
            }

        if self._is_ancestor(
            source_version_id,
            target_version_id
        ):
            return {
                "status": "UP_TO_DATE",
                "target_branch": target_branch,
                "source_branch": source_branch,
                "target_version": target_version_id,
                "source_version": source_version_id,
                "ancestor_version": source_version_id,
                "merged_version": target_version_id,
                "conflicts": []
            }

        ancestor_version_id = (
            self._find_common_ancestor_version_id(
                target_version_id,
                source_version_id
            )
        )

        if ancestor_version_id is None:
            raise RuntimeError(
                "Branches do not have a common ancestor"
            )

        ancestor_version = (
            self.history.get_version(
                ancestor_version_id
            )
        )

        target_version = (
            self.history.get_version(
                target_version_id
            )
        )

        source_version = (
            self.history.get_version(
                source_version_id
            )
        )

        merged_state, conflicts = (
            self._three_way_merge_states(
                base_state=ancestor_version.state,
                target_state=target_version.state,
                source_state=source_version.state
            )
        )

        # --------------------------------------------------
        # Conflicted merge:
        #
        # No live database or history state is changed.
        # --------------------------------------------------

        if conflicts:
            return {
                "status": "CONFLICT",
                "target_branch": target_branch,
                "source_branch": source_branch,
                "target_version": target_version_id,
                "source_version": source_version_id,
                "ancestor_version": ancestor_version_id,
                "merged_version": None,
                "conflicts": conflicts
            }

        # --------------------------------------------------
        # Validate complete merged state.
        # --------------------------------------------------

        try:
            for table_data in merged_state.get(
                "tables",
                {}
            ).values():
                self._validate_merged_table_constraints(
                    table_data
                )

        except Exception as exc:
            return {
                "status": "CONFLICT",
                "target_branch": target_branch,
                "source_branch": source_branch,
                "target_version": target_version_id,
                "source_version": source_version_id,
                "ancestor_version": ancestor_version_id,
                "merged_version": None,
                "conflicts": [
                    {
                        "type": "constraint_conflict",
                        "reason": str(exc)
                    }
                ]
            }

        # --------------------------------------------------
        # Apply merged state.
        # --------------------------------------------------

        self._restore_database_state(
            merged_state
        )

        self.mark_dirty()

        # --------------------------------------------------
        # Create two-parent merge version.
        # --------------------------------------------------

        merge_version = (
            self.history.create_version(
                state=self._database_state(),
                operation=(
                    f"MERGE "
                    f"{source_branch} "
                    f"INTO "
                    f"{target_branch}"
                ),
                branch_name=target_branch,
                parent_version_id=target_version_id,
                merge_parent_version_id=source_version_id
            )
        )

        return {
            "status": "MERGED",
            "target_branch": target_branch,
            "source_branch": source_branch,
            "target_version": target_version_id,
            "source_version": source_version_id,
            "ancestor_version": ancestor_version_id,
            "merged_version": merge_version.version_id,
            "conflicts": []
        }

    # ======================================================
    # VERSION DIFF
    # ======================================================

    def _parse_version_id(self, version_id):
        """
        Convert a version identifier to an integer.

        This keeps version validation consistent for diff and
        comparison operations.
        """
        try:
            return int(
                version_id
            )
        except (
            TypeError,
            ValueError
        ):
            raise ValueError(
                "Version ID must be an integer"
            )

    def _extract_rows_by_id(self, table_data):
        """
        Build a mapping of Record ID to row for a serialized table.
        """
        rows = table_data.get(
            "rows",
            []
        )

        record_ids = table_data.get(
            "record_ids",
            []
        )

        result = {}

        for index, row in enumerate(
            rows
        ):
            if index < len(record_ids):
                record_id = record_ids[index]
            else:
                record_id = index + 1

            result[record_id] = row

        return result

    def _table_schema_changed(
        self,
        before,
        after
    ):
        """
        Determine whether the logical table schema changed.
        """
        return (
            before.get("columns")
            != after.get("columns")
            or
            before.get("primary_key")
            != after.get("primary_key")
        )

    def _table_indexes_changed(
        self,
        before,
        after
    ):
        """
        Determine whether the table's index definitions changed.
        """
        before_definitions = before.get(
            "index_definitions"
        )

        after_definitions = after.get(
            "index_definitions"
        )

        if (
            before_definitions is not None
            or after_definitions is not None
        ):
            return (
                before_definitions
                != after_definitions
            )

        return (
            before.get("indexes", [])
            != after.get("indexes", [])
            or
            before.get("bplus_indexes", [])
            != after.get("bplus_indexes", [])
        )

    def _diff_table(
        self,
        before,
        after,
        common_ancestor=None
    ):
        """
        Compare two serialized versions of one table.

        A common ancestor is used so branch-local Record ID
        collisions are not mistaken for row updates.
        """
        before_rows = (
            self._extract_rows_by_id(
                before
            )
        )

        after_rows = (
            self._extract_rows_by_id(
                after
            )
        )

        ancestor_rows = {}

        if common_ancestor is not None:
            ancestor_rows = (
                self._extract_rows_by_id(
                    common_ancestor
                )
            )

        ancestor_record_ids = set(
            ancestor_rows.keys()
        )

        before_ids = set(
            before_rows.keys()
        )

        after_ids = set(
            after_rows.keys()
        )

        comparable_ids = (
            before_ids
            & after_ids
            & ancestor_record_ids
        )

        removed_ids = (
            before_ids
            - comparable_ids
        )

        added_ids = (
            after_ids
            - comparable_ids
        )

        updated = []

        for record_id in sorted(
            comparable_ids
        ):
            before_row = before_rows[
                record_id
            ]

            after_row = after_rows[
                record_id
            ]

            if before_row != after_row:
                updated.append(
                    {
                        "record_id": record_id,
                        "before": before_row,
                        "after": after_row
                    }
                )

        return {
            "schema_changed": (
                self._table_schema_changed(
                    before,
                    after
                )
            ),
            "indexes_changed": (
                self._table_indexes_changed(
                    before,
                    after
                )
            ),
            "rows_added": [
                {
                    "record_id": record_id,
                    "row": after_rows[
                        record_id
                    ]
                }
                for record_id in sorted(
                    added_ids
                )
            ],
            "rows_removed": [
                {
                    "record_id": record_id,
                    "row": before_rows[
                        record_id
                    ]
                }
                for record_id in sorted(
                    removed_ids
                )
            ],
            "rows_updated": updated
        }

    def diff_versions(
        self,
        before_version_id,
        after_version_id
    ):
        """
        Compare two historical database versions.

        The comparison is logical rather than a raw JSON diff.

        When comparing versions from different branches, the
        common ancestor is used to distinguish shared rows from
        independently created branch-local rows.

        The ancestry algorithm also understands two-parent merge
        versions.
        """
        before_version_id = (
            self._parse_version_id(
                before_version_id
            )
        )

        after_version_id = (
            self._parse_version_id(
                after_version_id
            )
        )

        before_version = (
            self.history.get_version(
                before_version_id
            )
        )

        after_version = (
            self.history.get_version(
                after_version_id
            )
        )

        common_ancestor_version_id = (
            self._find_common_ancestor_version_id(
                before_version_id,
                after_version_id
            )
        )

        common_ancestor_version = None

        if common_ancestor_version_id is not None:
            common_ancestor_version = (
                self.history.get_version(
                    common_ancestor_version_id
                )
            )

        before_tables = (
            before_version.state.get(
                "tables",
                {}
            )
        )

        after_tables = (
            after_version.state.get(
                "tables",
                {}
            )
        )

        ancestor_tables = {}

        if common_ancestor_version is not None:
            ancestor_tables = (
                common_ancestor_version.state.get(
                    "tables",
                    {}
                )
            )

        before_table_names = set(
            before_tables.keys()
        )

        after_table_names = set(
            after_tables.keys()
        )

        tables_added = sorted(
            after_table_names
            - before_table_names
        )

        tables_removed = sorted(
            before_table_names
            - after_table_names
        )

        tables_changed = {}

        common_tables = sorted(
            before_table_names
            & after_table_names
        )

        for table_name in common_tables:
            table_diff = self._diff_table(
                before_tables[table_name],
                after_tables[table_name],
                common_ancestor=ancestor_tables.get(
                    table_name
                )
            )

            if (
                table_diff["schema_changed"]
                or table_diff["indexes_changed"]
                or table_diff["rows_added"]
                or table_diff["rows_removed"]
                or table_diff["rows_updated"]
            ):
                tables_changed[
                    table_name
                ] = table_diff

        return {
            "before_version": before_version_id,
            "after_version": after_version_id,
            "tables_added": tables_added,
            "tables_removed": tables_removed,
            "tables_changed": tables_changed
        }

    # ======================================================
    # HISTORICAL QUERY COMPARISON
    # ======================================================

    def _get_historical_table(
        self,
        version,
        table_name
    ):
        """
        Reconstruct a temporary Table from a historical version.
        """
        tables = version.state.get(
            "tables",
            {}
        )

        if table_name not in tables:
            raise ValueError(
                f"Table '{table_name}' does not exist "
                f"in version '{version.version_id}'"
            )

        return Table.from_dict(
            deepcopy(
                tables[table_name]
            )
        )

    def _compare_select_at_version(
        self,
        query,
        version
    ):
        """
        Execute one normal SELECT against a historical version.
        """
        table = self._get_historical_table(
            version,
            query.table_name
        )

        resolved_order_by = (
            self.executor._resolve_normal_order_by(
                table,
                query.columns,
                query.aliases,
                query.order_by
            )
        )

        result, stats = (
            table.select_with_stats(
                columns=query.columns,
                condition=query.condition,
                order_by=resolved_order_by,
                descending=query.descending,
                limit=query.limit
            )
        )

        plan = table.explain_select(
            query.condition
        )

        return {
            "result": result,
            "stats": stats,
            "plan": plan
        }

    def compare_versions(
        self,
        before_version_id,
        after_version_id,
        sql
    ):
        """
        Execute the same SELECT query against two historical
        database versions and compare their behavior.
        """
        before_version_id = (
            self._parse_version_id(
                before_version_id
            )
        )

        after_version_id = (
            self._parse_version_id(
                after_version_id
            )
        )

        if not isinstance(
            sql,
            str
        ) or not sql.strip():
            raise ValueError(
                "SELECT query cannot be empty"
            )

        query = self.parser.parse(
            sql
        )

        if not isinstance(
            query,
            SelectQuery
        ):
            raise ValueError(
                ".compare only supports SELECT statements"
            )

        if query.group_by:
            raise ValueError(
                ".compare does not yet support GROUP BY queries"
            )

        if (
            query.columns is not None
            and any(
                isinstance(
                    column,
                    AggregateExpression
                )
                for column in query.columns
            )
        ):
            raise ValueError(
                ".compare does not yet support aggregate queries"
            )

        before_version = (
            self.history.get_version(
                before_version_id
            )
        )

        after_version = (
            self.history.get_version(
                after_version_id
            )
        )

        before_execution = (
            self._compare_select_at_version(
                query,
                before_version
            )
        )

        after_execution = (
            self._compare_select_at_version(
                query,
                after_version
            )
        )

        before_result = (
            before_execution["result"]
        )

        after_result = (
            after_execution["result"]
        )

        before_stats = (
            before_execution["stats"]
        )

        after_stats = (
            after_execution["stats"]
        )

        return {
            "query": sql.strip(),
            "before_version": before_version_id,
            "after_version": after_version_id,
            "before": {
                "result": before_result,
                "stats": before_stats,
                "plan": before_execution["plan"]
            },
            "after": {
                "result": after_result,
                "stats": after_stats,
                "plan": after_execution["plan"]
            },
            "result_changed": (
                before_result
                != after_result
            ),
            "access_path_changed": (
                before_stats["access_path"]
                != after_stats["access_path"]
            )
        }

    # ======================================================
    # WHAT-IF PLANNER ANALYSIS
    # ======================================================

    def _whatif_select_on_table(
        self,
        table,
        query
    ):
        """
        Execute a normal SELECT against a supplied temporary Table.
        """
        resolved_order_by = (
            self.executor._resolve_normal_order_by(
                table,
                query.columns,
                query.aliases,
                query.order_by
            )
        )

        result, stats = (
            table.select_with_stats(
                columns=query.columns,
                condition=query.condition,
                order_by=resolved_order_by,
                descending=query.descending,
                limit=query.limit
            )
        )

        plan = table.explain_select(
            query.condition
        )

        return {
            "result": result,
            "stats": stats,
            "plan": plan
        }

    def what_if_index(
        self,
        create_index_sql,
        select_sql
    ):
        """
        Simulate creation of an index and evaluate its effect on
        a SELECT query without modifying the real database.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Cannot run what-if analysis during an active transaction"
            )

        if (
            not isinstance(
                create_index_sql,
                str
            )
            or not create_index_sql.strip()
        ):
            raise ValueError(
                "CREATE INDEX query cannot be empty"
            )

        if (
            not isinstance(
                select_sql,
                str
            )
            or not select_sql.strip()
        ):
            raise ValueError(
                "SELECT query cannot be empty"
            )

        create_query = self.parser.parse(
            create_index_sql.strip()
        )

        if not isinstance(
            create_query,
            CreateIndexQuery
        ):
            raise ValueError(
                ".whatif requires a CREATE INDEX statement"
            )

        select_query = self.parser.parse(
            select_sql.strip()
        )

        if not isinstance(
            select_query,
            SelectQuery
        ):
            raise ValueError(
                ".whatif only supports SELECT workloads"
            )

        if select_query.group_by:
            raise ValueError(
                ".whatif does not yet support GROUP BY queries"
            )

        if (
            select_query.columns is not None
            and any(
                isinstance(
                    column,
                    AggregateExpression
                )
                for column in select_query.columns
            )
        ):
            raise ValueError(
                ".whatif does not yet support aggregate queries"
            )

        real_table = self.get_table(
            create_query.table_name
        )

        if (
            select_query.table_name
            != create_query.table_name
        ):
            raise ValueError(
                "CREATE INDEX and SELECT must target the same table"
            )

        current_table = Table.from_dict(
            deepcopy(
                real_table.to_dict()
            )
        )

        hypothetical_table = Table.from_dict(
            deepcopy(
                real_table.to_dict()
            )
        )

        if hypothetical_table.has_named_index(
            create_query.index_name
        ):
            raise ValueError(
                f"Index '{create_query.index_name}' "
                f"already exists"
            )

        index_type = (
            create_query.index_type.upper()
        )

        if index_type == "HASH":
            hypothetical_table.create_index(
                create_query.column_name,
                index_name=create_query.index_name
            )

        elif index_type == "BTREE":
            hypothetical_table.create_bplus_tree_index(
                create_query.column_name,
                index_name=create_query.index_name
            )

        else:
            raise ValueError(
                f"Unsupported index type: {index_type}"
            )

        without_index = (
            self._whatif_select_on_table(
                current_table,
                select_query
            )
        )

        with_index = (
            self._whatif_select_on_table(
                hypothetical_table,
                select_query
            )
        )

        return {
            "create_index_sql": (
                create_index_sql.strip()
            ),
            "select_sql": (
                select_sql.strip()
            ),
            "index": {
                "name": create_query.index_name,
                "type": index_type,
                "table": create_query.table_name,
                "column": create_query.column_name
            },
            "without_index": without_index,
            "with_index": with_index,
            "result_changed": (
                without_index["result"]
                != with_index["result"]
            ),
            "access_path_changed": (
                without_index["stats"]["access_path"]
                != with_index["stats"]["access_path"]
            ),
            "condition_evaluations_changed": (
                without_index[
                    "stats"
                ]["condition_evaluations"]
                !=
                with_index[
                    "stats"
                ]["condition_evaluations"]
            )
        }

    # ======================================================
    # PERSISTENCE
    # ======================================================

    def save(self):
        """
        Persist the database and version history.
        """
        data = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            },
            "history": self.history.to_dict()
        }

        self.storage.save(
            data
        )

        self.dirty = False

    def _load(self):
        """
        Load the database from persistent storage.

        Existing V1 databases without history are upgraded into
        a single initial Version 0.
        """
        data = self.storage.load()

        for name, table_data in data.get(
            "tables",
            {}
        ).items():
            self.tables[name] = (
                Table.from_dict(
                    deepcopy(
                        table_data
                    )
                )
            )

        history_data = data.get(
            "history"
        )

        if history_data:
            self.history = (
                HistoryManager.from_dict(
                    history_data
                )
            )

        else:
            self.history.initialize(
                state=self._database_state(),
                branch_name="main",
                operation="INITIAL"
            )

    # ======================================================
    # DIRTY STATE
    # ======================================================

    def mark_dirty(self):
        """
        Mark the database as having unsaved changes.
        """
        self.dirty = True

    # ======================================================
    # TRANSACTIONS
    # ======================================================

    def begin(self):
        """
        Start a new database transaction.

        The transaction stores the current table state and
        dirty state.

        Version history is not modified by BEGIN.
        """
        if self._snapshot is not None:
            raise RuntimeError(
                "Transaction already active"
            )

        self._snapshot = {
            "tables": {
                name: deepcopy(
                    table.to_dict()
                )
                for name, table in self.tables.items()
            },
            "dirty": self.dirty
        }

    def _transaction_state_changed(self):
        """
        Determine whether a transaction actually changed
        database state.
        """
        if self._snapshot is None:
            return False

        current_tables = {
            name: table.to_dict()
            for name, table in self.tables.items()
        }

        return (
            current_tables
            != self._snapshot["tables"]
        )

    def rollback(self):
        """
        Roll back the current transaction.

        No new version is created because the changes were
        discarded.
        """
        if self._snapshot is None:
            raise RuntimeError(
                "No active transaction"
            )

        self.tables = {
            name: Table.from_dict(
                deepcopy(
                    table_data
                )
            )
            for name, table_data
            in self._snapshot["tables"].items()
        }

        self.dirty = (
            self._snapshot["dirty"]
        )

        self._snapshot = None

    def commit(self):
        """
        Commit the current transaction.

        Multiple mutations inside the transaction produce
        exactly one new historical version.
        """
        if self._snapshot is None:
            raise RuntimeError(
                "No active transaction"
            )

        changed = (
            self._transaction_state_changed()
        )

        if changed:
            self._create_version(
                "TRANSACTION COMMIT"
            )

        self.save()

        self._snapshot = None