from pydb.column import Column
from pydb.index import Index
from pydb.bplus_index import BPlusTreeIndex
from pydb.condition import (
    Condition,
    BetweenCondition
)


class Table:
    """
    Represents a database table.

    A table contains a schema defined by its columns and the
    rows belonging to that schema.

    A table can optionally have:

        - a primary key
        - hash indexes
        - B+Tree indexes

    Every row also receives an internal Record ID.

    Record IDs are separate from SQL columns and are not visible
    in SELECT results.
    """

    def __init__(self, name, columns, primary_key=None):
        """
        Create a table with the given columns and optional
        primary key.

        Column definitions can contain:

            (column_name, data_type)

            (column_name, data_type, nullable)

            (column_name, data_type, nullable, unique)

            (column_name, data_type, nullable, unique, default)
        """
        if not name:
            raise ValueError(
                "Table name cannot be empty"
            )

        if not columns:
            raise ValueError(
                "Table must have at least one column"
            )

        self.name = name
        self.columns = []

        for column_definition in columns:

            if len(column_definition) == 2:
                column_name, data_type = column_definition

                nullable = True
                unique = False
                default = Column.NO_DEFAULT

            elif len(column_definition) == 3:
                (
                    column_name,
                    data_type,
                    nullable
                ) = column_definition

                unique = False
                default = Column.NO_DEFAULT

                if not isinstance(nullable, bool):
                    raise TypeError(
                        "Column nullable property must be a boolean"
                    )

            elif len(column_definition) == 4:
                (
                    column_name,
                    data_type,
                    nullable,
                    unique
                ) = column_definition

                default = Column.NO_DEFAULT

                if not isinstance(nullable, bool):
                    raise TypeError(
                        "Column nullable property must be a boolean"
                    )

                if not isinstance(unique, bool):
                    raise TypeError(
                        "Column unique property must be a boolean"
                    )

            elif len(column_definition) == 5:
                (
                    column_name,
                    data_type,
                    nullable,
                    unique,
                    default
                ) = column_definition

                if not isinstance(nullable, bool):
                    raise TypeError(
                        "Column nullable property must be a boolean"
                    )

                if not isinstance(unique, bool):
                    raise TypeError(
                        "Column unique property must be a boolean"
                    )

            else:
                raise ValueError(
                    "Column definition must contain "
                    "2, 3, 4, or 5 values"
                )

            if any(
                column.name == column_name
                for column in self.columns
            ):
                raise ValueError(
                    f"Duplicate column name: '{column_name}'"
                )

            self.columns.append(
                Column(
                    column_name,
                    data_type,
                    nullable=nullable,
                    unique=unique,
                    default=default
                )
            )

        # ---------------------------------
        # PRIMARY KEY
        # ---------------------------------

        self.primary_key = primary_key

        if self.primary_key is not None:
            if not any(
                column.name == self.primary_key
                for column in self.columns
            ):
                raise ValueError(
                    f"Primary key column "
                    f"'{self.primary_key}' does not exist"
                )

        # ---------------------------------
        # TABLE ROWS
        # ---------------------------------

        self.rows = []

        # ---------------------------------
        # INTERNAL RECORD IDs
        # ---------------------------------

        self.record_ids = []

        self.next_record_id = 1

        # ---------------------------------
        # HASH INDEXES
        # ---------------------------------

        # Existing planner and execution logic uses this mapping:
        #
        #     column_name -> Index
        #
        # Keep this structure unchanged.
        self.indexes = {}

        # ---------------------------------
        # B+TREE INDEXES
        # ---------------------------------

        # Existing planner and execution logic uses this mapping:
        #
        #     column_name -> BPlusTreeIndex
        #
        # Keep this structure unchanged.
        self.bplus_indexes = {}

        # ---------------------------------
        # NAMED INDEX DEFINITIONS
        # ---------------------------------

        # Stores user-visible index metadata.
        #
        # Example:
        #
        # {
        #     "age_hash_idx": {
        #         "type": "HASH",
        #         "column": "age"
        #     },
        #
        #     "age_btree_idx": {
        #         "type": "BTREE",
        #         "column": "age"
        #     }
        # }
        #
        # The actual Index/BPlusTreeIndex objects remain stored
        # in self.indexes and self.bplus_indexes.
        self.index_definitions = {}

    # ------------------------------------------------------------------
    # VALIDATION HELPERS
    # ------------------------------------------------------------------

    def _validate_row(self, row):
        """
        Validate row length and column data types.

        Column validation also handles NULL / NOT NULL
        constraints.
        """
        if len(row) != len(self.columns):
            raise ValueError(
                f"Expected {len(self.columns)} values, got {len(row)}"
            )

        for column, value in zip(
            self.columns,
            row
        ):
            if not column.validate(value):
                raise TypeError(
                    f"Column '{column.name}' expects "
                    f"{column.data_type}"
                )

    def _get_primary_key_index(self):
        """
        Return the index of the primary-key column.
        """
        if self.primary_key is None:
            return None

        for index, column in enumerate(
            self.columns
        ):
            if column.name == self.primary_key:
                return index

        raise ValueError(
            f"Primary key column "
            f"'{self.primary_key}' does not exist"
        )

    def _get_column_index(self, column_name):
        """
        Return the position of a column in the table schema.
        """
        for index, column in enumerate(
            self.columns
        ):
            if column.name == column_name:
                return index

        raise ValueError(
            f"Column '{column_name}' does not exist"
        )

    # ------------------------------------------------------------------
    # HASH INDEX MANAGEMENT
    # ------------------------------------------------------------------

    def create_index(
        self,
        column_name,
        index_name=None
    ):
        """
        Create a hash-style index for an existing column.

        Existing rows are immediately added to the index
        using their internal Record IDs.

        index_name:
            Optional user-visible name for the index.

            When omitted, a generated compatibility name is used.

        Example:

            table.create_index("age")

        or:

            table.create_index(
                "age",
                index_name="age_hash_idx"
            )
        """
        column_index = self._get_column_index(
            column_name
        )

        # Only one hash index is allowed per column
        # in the current Table architecture.
        if column_name in self.indexes:
            raise ValueError(
                f"Index already exists for column "
                f"'{column_name}'"
            )

        # ---------------------------------
        # INDEX NAME
        # ---------------------------------

        if index_name is None:
            index_name = (
                f"hash_{column_name}"
            )

        if index_name in self.index_definitions:
            raise ValueError(
                f"Index '{index_name}' already exists"
            )

        # ---------------------------------
        # BUILD INDEX
        # ---------------------------------

        index = Index(
            column_name
        )

        for row, record_id in zip(
            self.rows,
            self.record_ids
        ):
            index.insert(
                record_id,
                row[column_index]
            )

        self.indexes[column_name] = index

        # Store the user-facing metadata.
        self.index_definitions[
            index_name
        ] = {
            "type": "HASH",
            "column": column_name
        }

    def has_index(self, column_name):
        """
        Return True when a hash index exists for the column.
        """
        return column_name in self.indexes

    def drop_index(self, column_name):
        """
        Remove a hash index by column name.

        This method is retained for backward compatibility
        with the original Table API.

        Dropping a missing index is safe.
        """
        if column_name not in self.indexes:
            return

        self.indexes.pop(
            column_name,
            None
        )

        # Remove the matching named HASH index metadata.
        names_to_remove = [
            name
            for name, definition
            in self.index_definitions.items()
            if (
                definition["type"] == "HASH"
                and definition["column"] == column_name
            )
        ]

        for name in names_to_remove:
            del self.index_definitions[name]

    # ------------------------------------------------------------------
    # B+TREE INDEX MANAGEMENT
    # ------------------------------------------------------------------

    def create_bplus_tree_index(
        self,
        column_name,
        minimum_degree=2,
        index_name=None
    ):
        """
        Create a B+Tree index for an existing column.

        Existing rows are immediately indexed.

        NULL values are skipped because the B+Tree is an
        ordered structure and PyDB does not use B+Tree indexes
        for NULL comparisons.

        index_name:
            Optional user-visible name for the index.
        """
        column_index = self._get_column_index(
            column_name
        )

        # Only one B+Tree index is allowed per column
        # in the current Table architecture.
        if column_name in self.bplus_indexes:
            raise ValueError(
                f"B+Tree index already exists for column "
                f"'{column_name}'"
            )

        # ---------------------------------
        # INDEX NAME
        # ---------------------------------

        if index_name is None:
            index_name = (
                f"btree_{column_name}"
            )

        if index_name in self.index_definitions:
            raise ValueError(
                f"Index '{index_name}' already exists"
            )

        # ---------------------------------
        # BUILD INDEX
        # ---------------------------------

        index = BPlusTreeIndex(
            column_name,
            minimum_degree=minimum_degree
        )

        for row, record_id in zip(
            self.rows,
            self.record_ids
        ):
            value = row[column_index]

            if value is None:
                continue

            index.insert(
                record_id,
                value
            )

        self.bplus_indexes[
            column_name
        ] = index

        # Store the user-facing metadata.
        self.index_definitions[
            index_name
        ] = {
            "type": "BTREE",
            "column": column_name
        }

    def has_bplus_tree_index(self, column_name):
        """
        Return True when a B+Tree index exists for the column.
        """
        return column_name in self.bplus_indexes

    def drop_bplus_tree_index(self, column_name):
        """
        Remove a B+Tree index by column name.

        This method is retained for backward compatibility
        with the original Table API.

        Dropping a missing index is safe.
        """
        if column_name not in self.bplus_indexes:
            return

        self.bplus_indexes.pop(
            column_name,
            None
        )

        # Remove the matching named BTREE index metadata.
        names_to_remove = [
            name
            for name, definition
            in self.index_definitions.items()
            if (
                definition["type"] == "BTREE"
                and definition["column"] == column_name
            )
        ]

        for name in names_to_remove:
            del self.index_definitions[name]

    def has_named_index(self, index_name):
        """
        Return True when an index with the supplied name exists.
        """
        return index_name in self.index_definitions

    def drop_named_index(self, index_name):
        """
        Drop an index using its user-visible name.

        The corresponding underlying hash or B+Tree index
        is removed as well.
        """
        definition = self.index_definitions.get(
            index_name
        )

        if definition is None:
            raise ValueError(
                f"Index '{index_name}' does not exist"
            )

        index_type = definition["type"]
        column_name = definition["column"]

        # ---------------------------------
        # HASH INDEX
        # ---------------------------------

        if index_type == "HASH":
            self.indexes.pop(
                column_name,
                None
            )

        # ---------------------------------
        # B+TREE INDEX
        # ---------------------------------

        elif index_type == "BTREE":
            self.bplus_indexes.pop(
                column_name,
                None
            )

        else:
            raise ValueError(
                f"Unsupported index type: "
                f"{index_type}"
            )

        del self.index_definitions[
            index_name
        ]

    # ------------------------------------------------------------------
    # INDEX SYNCHRONIZATION
    # ------------------------------------------------------------------

    def _update_indexes_after_insert(
        self,
        row,
        record_id
    ):
        """
        Add a newly inserted row to every hash index.
        """
        for column_name, index in self.indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            index.insert(
                record_id,
                row[column_index]
            )

    def _update_bplus_indexes_after_insert(
        self,
        row,
        record_id
    ):
        """
        Add a newly inserted row to every B+Tree index.

        NULL values are skipped.
        """
        for column_name, index in self.bplus_indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            value = row[column_index]

            if value is None:
                continue

            index.insert(
                record_id,
                value
            )

    def _update_indexes_after_update(
        self,
        record_id,
        old_row,
        new_row
    ):
        """
        Synchronize hash indexes after a row update.
        """
        for column_name, index in self.indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            old_value = old_row[column_index]
            new_value = new_row[column_index]

            if old_value != new_value:
                index.update(
                    record_id,
                    old_value,
                    new_value
                )

    def _update_bplus_indexes_after_update(
        self,
        record_id,
        old_row,
        new_row
    ):
        """
        Synchronize B+Tree indexes after a row update.
        """
        for column_name, index in self.bplus_indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            old_value = old_row[column_index]
            new_value = new_row[column_index]

            if old_value != new_value:
                index.update(
                    record_id,
                    old_value,
                    new_value
                )

    def _remove_record_from_indexes(
        self,
        row,
        record_id
    ):
        """
        Remove a deleted row from every hash index.
        """
        for column_name, index in self.indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            index.delete(
                record_id,
                row[column_index]
            )

    def _remove_record_from_bplus_indexes(
        self,
        row,
        record_id
    ):
        """
        Remove a deleted row from every B+Tree index.
        """
        for column_name, index in self.bplus_indexes.items():
            column_index = self._get_column_index(
                column_name
            )

            index.delete(
                record_id,
                row[column_index]
            )

    # ------------------------------------------------------------------
    # HASH INDEX ACCESS PATH
    # ------------------------------------------------------------------

    def _get_indexed_record_ids(self, condition):
        """
        Return Record IDs that can be retrieved directly
        from a hash index.

        Currently supported:

            column = value

        Hash index lookup remains the preferred equality
        access path.

        Returning None means the normal table scan should
        be used or another access path should be attempted.
        """
        if not isinstance(
            condition,
            Condition
        ):
            return None

        if condition.operator != "=":
            return None

        if condition.value is None:
            return None

        if condition.column_name not in self.indexes:
            return None

        index = self.indexes[
            condition.column_name
        ]

        return index.lookup(
            condition.value
        )

    # ------------------------------------------------------------------
    # QUERY PLANNER
    # ------------------------------------------------------------------

    def _choose_access_path(self, condition):
        """
        Decide which access path should be used for a condition.

        Priority:

            1. HASH_INDEX for equality
            2. BTREE_INDEX for equality
            3. BTREE_RANGE for ordered comparisons
            4. FULL_SCAN

        This method only decides the access path.

        It does not execute the query.
        """

        # No WHERE condition means every row must be considered.
        if condition is None:
            return {
                "type": "FULL_SCAN",
                "reason": "No WHERE condition"
            }

        # --------------------------------------------------
        # HASH INDEX
        # --------------------------------------------------

        if (
            isinstance(
                condition,
                Condition
            )
            and condition.operator == "="
            and condition.value is not None
            and condition.column_name in self.indexes
        ):
            return {
                "type": "HASH_INDEX",
                "column": condition.column_name,
                "operator": condition.operator,
                "reason": "Hash index supports equality lookup"
            }

        # --------------------------------------------------
        # B+TREE
        # --------------------------------------------------

        if (
            isinstance(
                condition,
                Condition
            )
            and condition.value is not None
            and condition.column_name in self.bplus_indexes
        ):
            if condition.operator == "=":
                return {
                    "type": "BTREE_INDEX",
                    "column": condition.column_name,
                    "operator": condition.operator,
                    "reason": "B+Tree supports equality lookup"
                }

            if condition.operator in (
                ">",
                ">=",
                "<",
                "<="
            ):
                return {
                    "type": "BTREE_RANGE",
                    "column": condition.column_name,
                    "operator": condition.operator,
                    "reason": "B+Tree supports ordered range lookup"
                }

        # --------------------------------------------------
        # BETWEEN
        # --------------------------------------------------

        if isinstance(
            condition,
            BetweenCondition
        ):
            if (
                condition.lower_value is not None
                and condition.upper_value is not None
                and condition.column_name in self.bplus_indexes
            ):
                return {
                    "type": "BTREE_RANGE",
                    "column": condition.column_name,
                    "operator": "BETWEEN",
                    "reason": "B+Tree supports ordered range lookup"
                }

        # --------------------------------------------------
        # FALLBACK
        # --------------------------------------------------

        return {
            "type": "FULL_SCAN",
            "reason": "No suitable index access path"
        }

    def explain_select(self, condition=None):
        """
        Return a simple EXPLAIN-style description of the
        access path selected for a SELECT condition.

        This is intentionally not a SQL EXPLAIN command yet.

        Example:

            {
                "type": "BTREE_RANGE",
                "column": "age",
                "operator": ">",
                "reason": "B+Tree supports ordered range lookup"
            }
        """
        return self._choose_access_path(
            condition
        )

    # ------------------------------------------------------------------
    # B+TREE ACCESS PATH
    # ------------------------------------------------------------------

    def _get_bplus_indexed_record_ids(
        self,
        condition
    ):
        """
        Return candidate Record IDs retrieved through
        a B+Tree index.

        Supported conditions:

            column = value
            column > value
            column >= value
            column < value
            column <= value
            column BETWEEN lower AND upper

        The B+Tree provides candidate rows.

        Table.select() still evaluates the original condition
        against those candidates to preserve exact SQL
        comparison semantics.

        Returning None means that this B+Tree cannot be used
        for the supplied condition.
        """

        # ---------------------------------
        # SIMPLE COMPARISON
        # ---------------------------------

        if isinstance(
            condition,
            Condition
        ):

            # SQL NULL comparison is not an index access path.
            if condition.value is None:
                return None

            # No B+Tree for this column.
            if condition.column_name not in self.bplus_indexes:
                return None

            index = self.bplus_indexes[
                condition.column_name
            ]

            # Equality can use the B+Tree directly.
            if condition.operator == "=":
                return index.lookup(
                    condition.value
                )

            # The B+Tree range API is inclusive.
            #
            # For > and <, the final condition evaluation
            # removes the boundary value when necessary.
            if condition.operator == ">":
                return index.range_lookup(
                    lower=condition.value
                )

            if condition.operator == ">=":
                return index.range_lookup(
                    lower=condition.value
                )

            if condition.operator == "<":
                return index.range_lookup(
                    upper=condition.value
                )

            if condition.operator == "<=":
                return index.range_lookup(
                    upper=condition.value
                )

            # != does not represent one contiguous B+Tree
            # range, so fall back to the normal scan.
            return None

        # ---------------------------------
        # BETWEEN
        # ---------------------------------

        if isinstance(
            condition,
            BetweenCondition
        ):
            if (
                condition.lower_value is None
                or condition.upper_value is None
            ):
                return None

            if condition.column_name not in self.bplus_indexes:
                return None

            index = self.bplus_indexes[
                condition.column_name
            ]

            return index.range_lookup(
                lower=condition.lower_value,
                upper=condition.upper_value
            )

        return None

    def bplus_tree_range_lookup(
        self,
        column_name,
        lower=None,
        upper=None
    ):
        """
        Perform a direct range lookup through a B+Tree index.

        This remains useful as a learning/debugging API even
        though SELECT can now use the B+Tree automatically.
        """
        if column_name not in self.bplus_indexes:
            raise ValueError(
                f"No B+Tree index exists for column "
                f"'{column_name}'"
            )

        return self.bplus_indexes[
            column_name
        ].range_lookup(
            lower,
            upper
        )

    # ------------------------------------------------------------------
    # PRIMARY KEY / UNIQUE VALIDATION
    # ------------------------------------------------------------------

    def _validate_primary_key(self, row):
        """
        Validate the primary-key value.

        A primary key must:

            - exist
            - never be NULL
            - be unique
        """
        if self.primary_key is None:
            return

        primary_key_index = (
            self._get_primary_key_index()
        )

        primary_key_value = row[
            primary_key_index
        ]

        if primary_key_value is None:
            raise ValueError(
                f"Primary key column "
                f"'{self.primary_key}' cannot be NULL"
            )

        for existing_row in self.rows:
            if (
                existing_row[
                    primary_key_index
                ]
                == primary_key_value
            ):
                raise ValueError(
                    f"Duplicate primary key value: "
                    f"{primary_key_value}"
                )

    def _validate_unique_constraints(self, row):
        """
        Validate UNIQUE constraints for a new row.

        NULL values are ignored because a nullable UNIQUE
        column can contain multiple NULL values.
        """
        for column_index, column in enumerate(
            self.columns
        ):
            if not column.unique:
                continue

            value = row[column_index]

            if value is None:
                continue

            for existing_row in self.rows:
                if (
                    existing_row[column_index]
                    == value
                ):
                    raise ValueError(
                        f"Duplicate value for UNIQUE column "
                        f"'{column.name}': {value}"
                    )

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------

    def insert(self, row):
        """
        Insert a new row after validation.

        A stable Record ID is assigned only after all
        validation succeeds.

        All existing index structures are then synchronized.
        """
        self._validate_row(row)

        self._validate_primary_key(
            row
        )

        self._validate_unique_constraints(
            row
        )

        self.rows.append(
            row
        )

        record_id = self.next_record_id

        self.record_ids.append(
            record_id
        )

        self.next_record_id += 1

        self._update_indexes_after_insert(
            row,
            record_id
        )

        self._update_bplus_indexes_after_insert(
            row,
            record_id
        )

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------

    def to_dict(self):
        """
        Convert the table into a dictionary for persistence.

        Only index definitions are persisted.

        Actual index contents are derived data and are rebuilt
        from rows and Record IDs during loading.

        Both the old index lists and the newer named-index
        definitions are persisted.

        Keeping the old lists preserves compatibility with
        existing PyDB database files.
        """
        return {
            "name": self.name,

            "columns": [
                {
                    "name": column.name,
                    "data_type": column.data_type,
                    "nullable": column.nullable,
                    "unique": column.unique,
                    "default": column.default,
                    "has_default": column.has_default
                }
                for column in self.columns
            ],

            "primary_key": self.primary_key,

            "rows": [
                row.copy()
                for row in self.rows
            ],

            "record_ids": self.record_ids.copy(),

            "next_record_id": self.next_record_id,

            # Backward-compatible index information.
            "indexes": list(
                self.indexes.keys()
            ),

            "bplus_indexes": list(
                self.bplus_indexes.keys()
            ),

            # New named index metadata.
            "index_definitions": {
                name: definition.copy()
                for name, definition
                in self.index_definitions.items()
            }
        }

    @classmethod
    def from_dict(cls, data):
        """
        Reconstruct a Table from persisted data.

        Older database files remain backward-compatible.
        """
        columns = []

        for column in data["columns"]:

            nullable = column.get(
                "nullable",
                True
            )

            unique = column.get(
                "unique",
                False
            )

            has_default = column.get(
                "has_default",
                False
            )

            if has_default:
                default = column.get(
                    "default"
                )
            else:
                default = Column.NO_DEFAULT

            columns.append(
                (
                    column["name"],
                    column["data_type"],
                    nullable,
                    unique,
                    default
                )
            )

        table = cls(
            data["name"],
            columns,
            primary_key=data.get(
                "primary_key"
            )
        )

        # ---------------------------------
        # Restore rows
        # ---------------------------------

        for row in data["rows"]:
            table.insert(
                row
            )

        # ---------------------------------
        # Restore Record IDs
        # ---------------------------------

        if "record_ids" in data:

            if len(
                data["record_ids"]
            ) != len(table.rows):
                raise ValueError(
                    "Record ID count does not match row count"
                )

            table.record_ids = data[
                "record_ids"
            ].copy()

        # ---------------------------------
        # Restore next Record ID
        # ---------------------------------

        if "next_record_id" in data:
            table.next_record_id = data[
                "next_record_id"
            ]

        elif table.record_ids:
            table.next_record_id = (
                max(table.record_ids) + 1
            )

        # ---------------------------------
        # Restore named indexes
        # ---------------------------------

        index_definitions = data.get(
            "index_definitions"
        )

        if index_definitions:
            for index_name, definition in (
                index_definitions.items()
            ):
                index_type = definition[
                    "type"
                ]

                column_name = definition[
                    "column"
                ]

                if index_type == "HASH":

                    table.create_index(
                        column_name,
                        index_name=index_name
                    )

                elif index_type == "BTREE":

                    table.create_bplus_tree_index(
                        column_name,
                        index_name=index_name
                    )

                else:
                    raise ValueError(
                        f"Unsupported persisted index type: "
                        f"{index_type}"
                    )

        else:
            # ---------------------------------
            # Backward compatibility
            # ---------------------------------
            #
            # Older database files only stored:
            #
            #     indexes
            #     bplus_indexes
            #
            # Generate internal/user-visible names for
            # those existing indexes.

            for column_name in data.get(
                "indexes",
                []
            ):
                table.create_index(
                    column_name
                )

            for column_name in data.get(
                "bplus_indexes",
                []
            ):
                table.create_bplus_tree_index(
                    column_name
                )

        return table

    # ------------------------------------------------------------------
    # SELECT - INTERNAL EXECUTION WITH STATISTICS
    # ------------------------------------------------------------------

    def _select_rows_with_stats(
        self,
        condition=None
    ):
        """
        Execute the WHERE-filtering portion of SELECT.

        Returns:

            (matching_rows, execution_stats)

        The statistics are diagnostic and describe how much
        work the current execution path performs.

        Important distinction:

            table_rows_visited
                Number of rows visited while walking the
                table's row list.

            index_candidates
                Number of Record IDs returned by an index.

            condition_evaluations
                Number of times the WHERE condition was
                actually evaluated.

        The current implementation still walks the table row
        list for indexed queries so that SQL result ordering
        remains stable.

        Therefore an index can reduce condition evaluations
        even though table_rows_visited may remain equal to
        the total number of table rows.
        """

        # ---------------------------------
        # INITIAL STATISTICS
        # ---------------------------------

        stats = {
            "access_path": "FULL_SCAN",
            "table_rows": len(
                self.rows
            ),
            "table_rows_visited": 0,
            "index_candidates": None,
            "condition_evaluations": 0,
            "rows_matched": 0
        }

        # ---------------------------------
        # NO WHERE CONDITION
        # ---------------------------------

        if condition is None:

            stats[
                "table_rows_visited"
            ] = len(
                self.rows
            )

            rows = self.rows.copy()

            stats[
                "rows_matched"
            ] = len(
                rows
            )

            return rows, stats

        # ---------------------------------
        # CHOOSE ACCESS PATH
        # ---------------------------------

        access_path = self._choose_access_path(
            condition
        )

        stats[
            "access_path"
        ] = access_path["type"]

        # ---------------------------------
        # HASH INDEX
        # ---------------------------------

        if access_path[
            "type"
        ] == "HASH_INDEX":

            indexed_record_ids = (
                self._get_indexed_record_ids(
                    condition
                )
            )

        # ---------------------------------
        # B+TREE
        # ---------------------------------

        elif access_path[
            "type"
        ] in (
            "BTREE_INDEX",
            "BTREE_RANGE"
        ):

            indexed_record_ids = (
                self._get_bplus_indexed_record_ids(
                    condition
                )
            )

        # ---------------------------------
        # FULL SCAN
        # ---------------------------------

        else:
            indexed_record_ids = None

        # ---------------------------------
        # INDEX ACCESS PATH
        # ---------------------------------

        if indexed_record_ids is not None:

            indexed_record_ids = set(
                indexed_record_ids
            )

            stats[
                "index_candidates"
            ] = len(
                indexed_record_ids
            )

            rows = []

            # Walk the table in original order.
            #
            # This preserves the existing SELECT behavior.
            for row, record_id in zip(
                self.rows,
                self.record_ids
            ):
                stats[
                    "table_rows_visited"
                ] += 1

                # Only candidate records are evaluated
                # against the actual SQL condition.
                if record_id not in indexed_record_ids:
                    continue

                stats[
                    "condition_evaluations"
                ] += 1

                if condition.evaluate(
                    row,
                    self.columns
                ):
                    rows.append(
                        row
                    )

        # ---------------------------------
        # FULL TABLE SCAN
        # ---------------------------------

        else:

            rows = []

            for row in self.rows:

                stats[
                    "table_rows_visited"
                ] += 1

                stats[
                    "condition_evaluations"
                ] += 1

                if condition.evaluate(
                    row,
                    self.columns
                ):
                    rows.append(
                        row
                    )

        # ---------------------------------
        # FINAL MATCH COUNT
        # ---------------------------------

        stats[
            "rows_matched"
        ] = len(
            rows
        )

        return rows, stats

    # ------------------------------------------------------------------
    # SELECT WITH STATISTICS
    # ------------------------------------------------------------------

    def select_with_stats(
        self,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None
    ):
        """
        Execute SELECT and return both:

            (result, execution_stats)

        This is a diagnostic API.

        Normal SELECT callers should continue using select().

        Example:

            rows, stats = table.select_with_stats(
                condition=Condition(
                    "age",
                    ">",
                    30
                )
            )
        """
        rows, stats = (
            self._select_rows_with_stats(
                condition
            )
        )

        # ---------------------------------
        # ORDER BY
        # ---------------------------------

        if order_by is not None:

            column_index = None

            for index, column in enumerate(
                self.columns
            ):
                if column.name == order_by:
                    column_index = index
                    break

            if column_index is None:
                raise ValueError(
                    f"Column '{order_by}' does not exist"
                )

            rows.sort(
                key=lambda row: (
                    row[column_index] is None,
                    row[column_index]
                ),
                reverse=descending
            )

        # ---------------------------------
        # LIMIT
        # ---------------------------------

        if limit is not None:

            if limit < 0:
                raise ValueError(
                    "Limit cannot be negative"
                )

            rows = rows[
                :limit
            ]

        # ---------------------------------
        # SELECT *
        # ---------------------------------

        if columns is None:
            return rows, stats

        # ---------------------------------
        # SELECT COLUMN PROJECTION
        # ---------------------------------

        column_indexes = []

        for column_name in columns:

            for index, column in enumerate(
                self.columns
            ):

                if column.name == column_name:
                    column_indexes.append(
                        index
                    )
                    break

            else:
                raise ValueError(
                    f"Column '{column_name}' does not exist"
                )

        projected_rows = [
            [
                row[index]
                for index in column_indexes
            ]
            for row in rows
        ]

        return projected_rows, stats

    # ------------------------------------------------------------------
    # NORMAL SELECT
    # ------------------------------------------------------------------

    def select(
        self,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None
    ):
        """
        Retrieve rows matching the requested columns,
        condition, ordering, and limit.

        This remains the normal public SELECT API.

        It uses the same execution path as select_with_stats()
        but discards the diagnostic statistics.

        Existing callers therefore continue receiving
        exactly the same SELECT result format.
        """
        rows, _ = self.select_with_stats(
            columns=columns,
            condition=condition,
            order_by=order_by,
            descending=descending,
            limit=limit
        )

        return rows

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        updates,
        condition=None
    ):
        """
        Update rows satisfying the supplied condition.

        Both hash indexes and B+Tree indexes are synchronized
        after every successful row update.
        """
        affected_rows = 0

        primary_key_index = (
            self._get_primary_key_index()
        )

        for row, record_id in zip(
            self.rows,
            self.record_ids
        ):

            if condition is not None:
                if not condition.evaluate(
                    row,
                    self.columns
                ):
                    continue

            # ---------------------------------
            # PRIMARY KEY VALIDATION
            # ---------------------------------

            if self.primary_key in updates:

                new_primary_key = updates[
                    self.primary_key
                ]

                primary_key_column = self.columns[
                    primary_key_index
                ]

                if new_primary_key is None:
                    raise ValueError(
                        f"Primary key column "
                        f"'{self.primary_key}' cannot be NULL"
                    )

                if not primary_key_column.validate(
                    new_primary_key
                ):
                    raise TypeError(
                        f"Column '{self.primary_key}' expects "
                        f"{primary_key_column.data_type}"
                    )

                for existing_row in self.rows:

                    if (
                        existing_row is not row
                        and existing_row[
                            primary_key_index
                        ] == new_primary_key
                    ):
                        raise ValueError(
                            f"Duplicate primary key value: "
                            f"{new_primary_key}"
                        )

            # ---------------------------------
            # UNIQUE / NORMAL COLUMN VALIDATION
            # ---------------------------------

            for column_name, new_value in updates.items():

                for index, column in enumerate(
                    self.columns
                ):

                    if column.name == column_name:

                        if not column.validate(
                            new_value
                        ):
                            raise TypeError(
                                f"Column '{column.name}' expects "
                                f"{column.data_type}"
                            )

                        if (
                            column.unique
                            and new_value is not None
                        ):
                            for existing_row in self.rows:

                                if (
                                    existing_row is not row
                                    and existing_row[index]
                                    == new_value
                                ):
                                    raise ValueError(
                                        f"Duplicate value for UNIQUE "
                                        f"column '{column.name}': "
                                        f"{new_value}"
                                    )

                        break

                else:
                    raise ValueError(
                        f"Column '{column_name}' does not exist"
                    )

            old_row = row.copy()

            for column_name, new_value in updates.items():

                for index, column in enumerate(
                    self.columns
                ):

                    if column.name == column_name:
                        row[index] = new_value
                        break

            self._update_indexes_after_update(
                record_id,
                old_row,
                row
            )

            self._update_bplus_indexes_after_update(
                record_id,
                old_row,
                row
            )

            affected_rows += 1

        return affected_rows

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, condition=None):
        """
        Delete rows satisfying the supplied condition.

        Both hash indexes and B+Tree indexes are synchronized
        before rows are removed.
        """
        if condition is None:

            deleted_count = len(
                self.rows
            )

            for row, record_id in zip(
                self.rows,
                self.record_ids
            ):

                self._remove_record_from_indexes(
                    row,
                    record_id
                )

                self._remove_record_from_bplus_indexes(
                    row,
                    record_id
                )

            self.rows.clear()
            self.record_ids.clear()

            return deleted_count

        remaining_rows = []
        remaining_record_ids = []

        deleted_count = 0

        for row, record_id in zip(
            self.rows,
            self.record_ids
        ):

            if condition.evaluate(
                row,
                self.columns
            ):

                self._remove_record_from_indexes(
                    row,
                    record_id
                )

                self._remove_record_from_bplus_indexes(
                    row,
                    record_id
                )

                deleted_count += 1

            else:

                remaining_rows.append(
                    row
                )

                remaining_record_ids.append(
                    record_id
                )

        self.rows = remaining_rows
        self.record_ids = remaining_record_ids

        return deleted_count