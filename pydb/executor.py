from pydb.query import (
    InsertQuery,
    SelectQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    CreateIndexQuery,
    DropIndexQuery,
    DropTableQuery,
    ShowTablesQuery,
    DescribeTableQuery,
    AggregateExpression,
    HavingCondition,
    HavingAndCondition,
    HavingOrCondition,
    BeginQuery,
    CommitQuery,
    RollbackQuery
)


class QueryExecutor:
    """
    Executes database operations against a Database instance.
    """

    def __init__(self, database):
        """
        Store the database that this executor will operate on.
        """
        self.database = database

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------

    def insert(
        self,
        table_name,
        row,
        column_names=None
    ):
        """
        Insert a new row into the specified table.

        Supports both:

            INSERT INTO users VALUES (...)

        and:

            INSERT INTO users (name, age)
            VALUES ('Aditya', 22)

        For column-list INSERTs:

            - supplied values are mapped by column name
            - omitted columns use DEFAULT when available
            - omitted nullable columns become NULL
            - omitted NOT NULL columns without DEFAULT fail
            - explicit DEFAULT is resolved here
            - explicit NULL remains None

        Table.insert() remains responsible for final
        schema/type/constraint validation.
        """
        table = self.database.get_table(table_name)

        # --------------------------------------------------
        # Full-row INSERT
        # --------------------------------------------------

        if column_names is None:
            if len(row) != len(table.columns):
                raise ValueError(
                    f"Expected {len(table.columns)} values "
                    f"but received {len(row)}"
                )

            resolved_row = []

            for column, value in zip(
                table.columns,
                row
            ):
                if value is InsertQuery.DEFAULT:
                    if not column.has_default:
                        raise ValueError(
                            f"Column '{column.name}' "
                            f"has no default value"
                        )

                    resolved_row.append(
                        column.default
                    )

                else:
                    resolved_row.append(value)

            table.insert(resolved_row)

            self.database.mark_dirty()

            return

        # --------------------------------------------------
        # Column-list INSERT validation
        # --------------------------------------------------

        if len(column_names) != len(row):
            raise ValueError(
                f"Expected {len(column_names)} values "
                f"for {len(column_names)} columns "
                f"but received {len(row)}"
            )

        if len(column_names) != len(set(column_names)):
            raise ValueError(
                "Duplicate column names are not allowed"
            )

        table_column_names = {
            column.name
            for column in table.columns
        }

        for column_name in column_names:
            if column_name not in table_column_names:
                raise ValueError(
                    f"Column '{column_name}' does not exist"
                )

        # --------------------------------------------------
        # Build a complete table row
        # --------------------------------------------------

        supplied_values = dict(
            zip(column_names, row)
        )

        resolved_row = []

        for column in table.columns:

            # ----------------------------------------------
            # Supplied column
            # ----------------------------------------------

            if column.name in supplied_values:
                value = supplied_values[column.name]

                if value is InsertQuery.DEFAULT:

                    if not column.has_default:
                        raise ValueError(
                            f"Column '{column.name}' "
                            f"has no default value"
                        )

                    resolved_row.append(
                        column.default
                    )

                else:
                    resolved_row.append(value)

                continue

            # ----------------------------------------------
            # Omitted column with DEFAULT
            # ----------------------------------------------

            if column.has_default:
                resolved_row.append(
                    column.default
                )
                continue

            # ----------------------------------------------
            # Omitted nullable column
            # ----------------------------------------------

            if column.nullable:
                resolved_row.append(None)
                continue

            # ----------------------------------------------
            # Omitted NOT NULL column without DEFAULT
            # ----------------------------------------------

            raise ValueError(
                f"Column '{column.name}' is NOT NULL "
                f"and has no default value"
            )

        table.insert(resolved_row)

        self.database.mark_dirty()

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------

    def select(
        self,
        table_name,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None,
        group_by=None,
        having=None,
        aliases=None
    ):
        """
        Execute a SELECT query.

        The execution order is:

            1. WHERE
            2. GROUP BY
            3. HAVING
            4. SELECT
            5. ORDER BY
            6. LIMIT

        Aliases are metadata attached to SELECT expressions.

        Aliases can also be used by ORDER BY.

        The returned rows remain normal Python lists so that the
        existing PyDB result format remains backward compatible.
        """
        table = self.database.get_table(table_name)

        # Keep backwards compatibility for callers that directly
        # invoke executor.select() without supplying aliases.
        if aliases is None:
            aliases = []

        has_aggregate = self._contains_aggregate(columns)
        has_grouping = bool(group_by)

        # ---------------------------------
        # Validate GROUP BY / HAVING usage
        # ---------------------------------

        if having is not None and not (
            has_aggregate or has_grouping
        ):
            raise ValueError(
                "HAVING requires GROUP BY or an aggregate query"
            )

        if has_grouping:
            self._validate_group_by(
                table,
                columns,
                group_by
            )

        # ---------------------------------
        # Normal SELECT
        # ---------------------------------

        if not has_aggregate and not has_grouping:
            if having is not None:
                raise ValueError(
                    "HAVING requires GROUP BY or an aggregate query"
                )

            # Resolve ORDER BY aliases before passing the
            # operation to Table.select().
            resolved_order_by = self._resolve_normal_order_by(
                table,
                columns,
                aliases,
                order_by
            )

            return table.select(
                columns=columns,
                condition=condition,
                order_by=resolved_order_by,
                descending=descending,
                limit=limit
            )

        # ---------------------------------
        # Aggregate / grouped SELECT
        # ---------------------------------

        rows = table.select(
            condition=condition
        )

        groups = self._build_groups(
            rows,
            table,
            group_by
        )

        result_rows = []

        for group_rows in groups:

            # HAVING is evaluated against the completed group.
            if having is not None:
                if not self._evaluate_having(
                    table,
                    group_rows,
                    having
                ):
                    continue

            result_row = []

            if columns is None:
                raise ValueError(
                    "SELECT * cannot be used with GROUP BY "
                    "or aggregate queries"
                )

            for expression in columns:

                if isinstance(
                    expression,
                    AggregateExpression
                ):
                    value = self._calculate_aggregate(
                        table,
                        group_rows,
                        expression
                    )

                else:
                    column_index = self._get_column_index(
                        table,
                        expression
                    )

                    value = group_rows[0][column_index]

                result_row.append(value)

            result_rows.append(result_row)

        # ---------------------------------
        # ORDER BY grouped results
        # ---------------------------------

        if order_by is not None:
            result_rows = self._order_grouped_results(
                table,
                result_rows,
                columns,
                aliases,
                order_by,
                descending
            )

        # ---------------------------------
        # LIMIT grouped results
        # ---------------------------------

        if limit is not None:
            if limit < 0:
                raise ValueError(
                    "LIMIT cannot be negative"
                )

            result_rows = result_rows[:limit]

        return result_rows

    # ------------------------------------------------------------------
    # INDEX CREATION
    # ------------------------------------------------------------------

    def create_index(
        self,
        index_name,
        table_name,
        column_name,
        index_type="HASH"
    ):
        """
        Create a named index on a table.

        Supported index types:

            HASH
            BTREE

        HASH is the default when no explicit type is supplied.

        Example:

            CREATE INDEX age_idx
            ON users(age);

        or:

            CREATE INDEX age_idx
            ON users(age)
            USING BTREE;
        """
        table = self.database.get_table(
            table_name
        )

        index_type = index_type.upper()

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
                f"Unsupported index type: {index_type}"
            )

        # Creating an index changes the database metadata.
        self.database.mark_dirty()

        return None

    # ------------------------------------------------------------------
    # INDEX DROP
    # ------------------------------------------------------------------

    def drop_index(
        self,
        index_name
    ):
        """
        Drop a named index.

        Index names are globally searched across the current
        database tables.

        Example:

            DROP INDEX age_idx;
        """
        for table in self.database.tables.values():

            if not table.has_named_index(
                index_name
            ):
                continue

            table.drop_named_index(
                index_name
            )

            # Dropping an index changes database metadata.
            self.database.mark_dirty()

            return None

        raise ValueError(
            f"Index '{index_name}' does not exist"
        )

    # ------------------------------------------------------------------
    # AGGREGATE HELPERS
    # ------------------------------------------------------------------

    def _contains_aggregate(self, columns):
        """
        Return True when the SELECT column list contains
        aggregate expressions.
        """
        if columns is None:
            return False

        return any(
            isinstance(
                column,
                AggregateExpression
            )
            for column in columns
        )

    def _validate_group_by(
        self,
        table,
        columns,
        group_by
    ):
        """
        Validate GROUP BY columns and SELECT expressions.

        Every GROUP BY column must exist.

        When GROUP BY is used, every normal selected column must
        appear in the GROUP BY list.

        Aggregate expressions are allowed without appearing in
        GROUP BY.
        """
        if not group_by:
            return

        for column_name in group_by:
            self._get_column_index(
                table,
                column_name
            )

        if columns is None:
            raise ValueError(
                "SELECT * cannot be used with GROUP BY"
            )

        for expression in columns:

            if isinstance(
                expression,
                AggregateExpression
            ):
                continue

            if expression not in group_by:
                raise ValueError(
                    f"Column '{expression}' must appear "
                    f"in GROUP BY or be used in an aggregate"
                )

    def _build_groups(
        self,
        rows,
        table,
        group_by
    ):
        """
        Divide filtered rows into groups.

        A group is represented by a list of rows.

        When group_by is None, all filtered rows form one group.
        This is how normal aggregate queries such as:

            SELECT COUNT(*)

        are represented internally.
        """
        if group_by is None:
            return [rows]

        if not rows:
            return []

        indexes = [
            self._get_column_index(
                table,
                column_name
            )
            for column_name in group_by
        ]

        groups = {}
        group_order = []

        for row in rows:

            key = tuple(
                row[index]
                for index in indexes
            )

            if key not in groups:
                groups[key] = []
                group_order.append(key)

            groups[key].append(row)

        return [
            groups[key]
            for key in group_order
        ]

    def _evaluate_having(
        self,
        table,
        rows,
        condition
    ):
        """
        Evaluate a HAVING condition against one group.

        HAVING conditions can reference:

            - aggregate expressions
            - GROUP BY columns
            - AND
            - OR
        """
        if isinstance(
            condition,
            HavingCondition
        ):
            return self._evaluate_single_having(
                table,
                rows,
                condition
            )

        if isinstance(
            condition,
            HavingAndCondition
        ):
            return (
                self._evaluate_having(
                    table,
                    rows,
                    condition.left
                )
                and
                self._evaluate_having(
                    table,
                    rows,
                    condition.right
                )
            )

        if isinstance(
            condition,
            HavingOrCondition
        ):
            return (
                self._evaluate_having(
                    table,
                    rows,
                    condition.left
                )
                or
                self._evaluate_having(
                    table,
                    rows,
                    condition.right
                )
            )

        raise ValueError(
            "Unsupported HAVING condition"
        )

    def _evaluate_single_having(
        self,
        table,
        rows,
        condition
    ):
        """
        Evaluate one comparison inside HAVING.
        """
        expression = condition.expression

        if isinstance(
            expression,
            AggregateExpression
        ):
            left_value = self._calculate_aggregate(
                table,
                rows,
                expression
            )

        else:
            column_index = self._get_column_index(
                table,
                expression
            )

            if not rows:
                return False

            left_value = rows[0][column_index]

        return self._compare_values(
            left_value,
            condition.operator,
            condition.value
        )

    def _compare_values(
        self,
        left,
        operator,
        right
    ):
        """
        Compare two values using a SQL comparison operator.

        NULL comparisons return False.
        """
        if left is None or right is None:
            return False

        if operator == "=":
            return left == right

        if operator == "!=":
            return left != right

        if operator == ">":
            return left > right

        if operator == "<":
            return left < right

        if operator == ">=":
            return left >= right

        if operator == "<=":
            return left <= right

        raise ValueError(
            f"Unsupported comparison operator: {operator}"
        )

    # ------------------------------------------------------------------
    # ORDER BY HELPERS
    # ------------------------------------------------------------------

    def _resolve_normal_order_by(
        self,
        table,
        columns,
        aliases,
        order_by
    ):
        """
        Resolve ORDER BY for a normal SELECT.

        ORDER BY may reference:

            - an actual selected column
            - a SELECT alias
        """
        if order_by is None:
            return None

        # ---------------------------------
        # Alias lookup
        # ---------------------------------

        if aliases and columns is not None:
            for index, alias in enumerate(aliases):

                if alias != order_by:
                    continue

                expression = columns[index]

                if isinstance(
                    expression,
                    AggregateExpression
                ):
                    raise ValueError(
                        f"Aggregate alias '{order_by}' "
                        f"cannot be used in a normal SELECT"
                    )

                return expression

        # ---------------------------------
        # Direct selected column
        # ---------------------------------

        if columns is not None:
            for expression in columns:
                if (
                    isinstance(
                        expression,
                        str
                    )
                    and expression == order_by
                ):
                    return order_by

        return order_by

    def _order_grouped_results(
        self,
        table,
        rows,
        expressions,
        aliases,
        order_by,
        descending
    ):
        """
        Sort grouped query results.

        ORDER BY may reference:

            - a selected normal column
            - a selected expression alias
        """
        if expressions is None:
            raise ValueError(
                "ORDER BY cannot be resolved without SELECT expressions"
            )

        if aliases is None:
            aliases = []

        order_index = None

        # ---------------------------------
        # SELECT aliases
        # ---------------------------------

        for index, alias in enumerate(aliases):
            if alias == order_by:
                order_index = index
                break

        # ---------------------------------
        # Selected normal columns
        # ---------------------------------

        if order_index is None:
            for index, expression in enumerate(expressions):
                if (
                    isinstance(expression, str)
                    and expression == order_by
                ):
                    order_index = index
                    break

        if order_index is None:
            raise ValueError(
                f"ORDER BY column or alias '{order_by}' "
                f"must be selected"
            )

        return sorted(
            rows,
            key=lambda row: (
                row[order_index] is None,
                row[order_index]
            ),
            reverse=descending
        )

    # ------------------------------------------------------------------
    # AGGREGATES
    # ------------------------------------------------------------------

    def _execute_aggregates(
        self,
        table,
        rows,
        expressions
    ):
        """
        Calculate all aggregate expressions over the filtered rows.

        This method is retained for compatibility with the existing
        aggregate implementation.
        """
        result = []

        for expression in expressions:
            result.append(
                self._calculate_aggregate(
                    table,
                    rows,
                    expression
                )
            )

        return [result]

    def _calculate_aggregate(
        self,
        table,
        rows,
        expression
    ):
        """
        Calculate one aggregate expression.

        NULL values are ignored by every aggregate except
        COUNT(*), which counts every row.

        Empty input produces:

            COUNT -> 0

            SUM / AVG / MIN / MAX -> None
        """
        function_name = expression.function_name

        if expression.is_count_all:
            return len(rows)

        column_index = self._get_column_index(
            table,
            expression.column_name
        )

        values = [
            row[column_index]
            for row in rows
            if row[column_index] is not None
        ]

        if function_name == "COUNT":
            return len(values)

        if not values:
            return None

        if function_name in (
            "SUM",
            "AVG"
        ):
            self._validate_numeric_column(
                table,
                column_index
            )

            if function_name == "SUM":
                return sum(values)

            return sum(values) / len(values)

        if function_name == "MIN":
            return min(values)

        if function_name == "MAX":
            return max(values)

        raise ValueError(
            f"Unsupported aggregate function: {function_name}"
        )

    # ------------------------------------------------------------------
    # COLUMN HELPERS
    # ------------------------------------------------------------------

    def _get_column_index(
        self,
        table,
        column_name
    ):
        """
        Find the index of a column in the table schema.
        """
        for index, column in enumerate(table.columns):
            if column.name == column_name:
                return index

        raise ValueError(
            f"Column '{column_name}' does not exist"
        )

    def _validate_numeric_column(
        self,
        table,
        column_index
    ):
        """
        Ensure that a SUM or AVG operation is performed on
        an INT or FLOAT column.
        """
        column = table.columns[column_index]

        if column.data_type not in (
            "INT",
            "FLOAT"
        ):
            raise TypeError(
                f"{column.data_type} column "
                f"'{column.name}' cannot be used with "
                f"SUM or AVG"
            )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        table_name,
        updates,
        condition=None
    ):
        """
        Update rows in a table that satisfy the given condition.
        """
        table = self.database.get_table(table_name)

        affected_rows = table.update(
            updates,
            condition
        )

        self.database.mark_dirty()

        return affected_rows

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(
        self,
        table_name,
        condition=None
    ):
        """
        Delete rows from a table that satisfy the given condition.
        """
        table = self.database.get_table(table_name)

        affected_rows = table.delete(
            condition
        )

        self.database.mark_dirty()

        return affected_rows

    # ------------------------------------------------------------------
    # CREATE TABLE
    # ------------------------------------------------------------------

    def create_table(
        self,
        table_name,
        columns,
        primary_key=None
    ):
        """
        Create a new table in the database.

        The actual table creation and schema validation are
        delegated to Database.create_table().
        """
        return self.database.create_table(
            table_name,
            columns,
            primary_key=primary_key
        )

    # ------------------------------------------------------------------
    # TRANSACTIONS
    # ------------------------------------------------------------------

    def begin(self):
        """
        Start a new database transaction.
        """
        self.database.begin()

    def commit(self):
        """
        Commit the current transaction.
        """
        self.database.commit()

    def rollback(self):
        """
        Roll back the current transaction.
        """
        self.database.rollback()

    # ------------------------------------------------------------------
    # MAIN QUERY DISPATCH
    # ------------------------------------------------------------------

    def execute(self, query):
        """
        Execute a Query Object and return its result.
        """

        # ---------------------------------
        # INSERT
        # ---------------------------------

        if isinstance(
            query,
            InsertQuery
        ):
            return self.insert(
                query.table_name,
                query.row,
                query.column_names
            )

        # ---------------------------------
        # BEGIN
        # ---------------------------------

        if isinstance(
            query,
            BeginQuery
        ):
            return self.begin()

        # ---------------------------------
        # COMMIT
        # ---------------------------------

        if isinstance(
            query,
            CommitQuery
        ):
            return self.commit()

        # ---------------------------------
        # ROLLBACK
        # ---------------------------------

        if isinstance(
            query,
            RollbackQuery
        ):
            return self.rollback()

        # ---------------------------------
        # SELECT
        # ---------------------------------

        if isinstance(
            query,
            SelectQuery
        ):
            return self.select(
                query.table_name,
                columns=query.columns,
                condition=query.condition,
                order_by=query.order_by,
                descending=query.descending,
                limit=query.limit,
                group_by=query.group_by,
                having=query.having,
                aliases=query.aliases
            )

        # ---------------------------------
        # UPDATE
        # ---------------------------------

        if isinstance(
            query,
            UpdateQuery
        ):
            return self.update(
                query.table_name,
                query.updates,
                query.condition
            )

        # ---------------------------------
        # DELETE
        # ---------------------------------

        if isinstance(
            query,
            DeleteQuery
        ):
            return self.delete(
                query.table_name,
                query.condition
            )

        # ---------------------------------
        # CREATE TABLE
        # ---------------------------------

        if isinstance(
            query,
            CreateTableQuery
        ):
            return self.create_table(
                query.table_name,
                query.columns,
                query.primary_key
            )

        # ---------------------------------
        # CREATE INDEX
        # ---------------------------------

        if isinstance(
            query,
            CreateIndexQuery
        ):
            return self.create_index(
                query.index_name,
                query.table_name,
                query.column_name,
                query.index_type
            )

        # ---------------------------------
        # DROP INDEX
        # ---------------------------------

        if isinstance(
            query,
            DropIndexQuery
        ):
            return self.drop_index(
                query.index_name
            )

        # ---------------------------------
        # DROP TABLE
        # ---------------------------------

        if isinstance(
            query,
            DropTableQuery
        ):
            return self.database.drop_table(
                query.table_name
            )

        # ---------------------------------
        # SHOW TABLES
        # ---------------------------------

        if isinstance(
            query,
            ShowTablesQuery
        ):
            return self.database.list_tables()

        # ---------------------------------
        # DESCRIBE
        # ---------------------------------

        if isinstance(
            query,
            DescribeTableQuery
        ):
            table = self.database.get_table(
                query.table_name
            )

            return [
                {
                    "name": column.name,
                    "type": column.data_type,
                    "primary_key": (
                        column.name == table.primary_key
                    ),
                    "nullable": column.nullable,
                    "unique": column.unique
                }
                for column in table.columns
            ]

        # ---------------------------------
        # UNSUPPORTED QUERY
        # ---------------------------------

        raise ValueError(
            f"Unsupported query type: "
            f"{type(query).__name__}"
        )