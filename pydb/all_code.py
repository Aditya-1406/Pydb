class Column:
    """
    Represents a column in a database table.

    A column has a name, data type, nullable property,
    unique property, and optional default value.

    nullable=True means SQL NULL is allowed.

    nullable=False means the column behaves as NOT NULL
    and SQL NULL is rejected.

    unique=True means duplicate non-NULL values will be
    rejected by the Table layer.

    has_default=True means a DEFAULT clause was explicitly
    specified for the column.

    has_default=False means no DEFAULT clause was specified.

    A sentinel is used internally so that:

        no DEFAULT

    can be distinguished from:

        DEFAULT NULL
    """

    VALID_TYPES = {"INT", "TEXT", "FLOAT", "BOOL"}

    # Sentinel used to distinguish between:
    #
    #     no DEFAULT clause
    #
    # and:
    #
    #     DEFAULT NULL
    #
    # Python None represents SQL NULL, so None itself
    # cannot represent "no default specified".
    NO_DEFAULT = object()

    def __init__(
        self,
        name,
        data_type,
        nullable=True,
        unique=False,
        default=NO_DEFAULT
    ):
        """
        Create a column with the given metadata.

        default may be any value supported by the column's
        data type.

        DEFAULT NULL is represented by:

            default=None

        while the absence of DEFAULT is represented internally
        by the NO_DEFAULT sentinel.
        """
        if not name:
            raise ValueError("Column name cannot be empty")

        data_type = data_type.upper()

        if data_type not in self.VALID_TYPES:
            raise ValueError(
                f"Unsupported data type: {data_type}"
            )

        if not isinstance(nullable, bool):
            raise TypeError(
                "Column nullable property must be a boolean"
            )

        if not isinstance(unique, bool):
            raise TypeError(
                "Column unique property must be a boolean"
            )

        # Store the basic column metadata before validating
        # the default value.
        #
        # _is_valid_value() needs self.data_type to determine
        # whether the default has the correct type.
        self.name = name
        self.data_type = data_type
        self.nullable = nullable
        self.unique = unique

        # Determine whether DEFAULT was explicitly specified.
        self.has_default = default is not self.NO_DEFAULT

        # Store None when no DEFAULT was specified.
        #
        # has_default tells us whether that None means:
        #
        #     no DEFAULT
        #
        # or:
        #
        #     DEFAULT NULL
        self.default = (
            None
            if not self.has_default
            else default
        )

        # Validate the default only when a DEFAULT clause
        # was explicitly specified.
        if (
            self.has_default
            and not self._is_valid_value(self.default)
        ):
            raise ValueError(
                "Default value does not match column data type"
            )

    def _is_valid_value(self, value):
        """
        Check whether a value matches this column's data type.

        None represents SQL NULL.

        DEFAULT NULL is allowed here because the default value
        itself can be SQL NULL.

        NOT NULL enforcement remains the responsibility of
        validate() when a value is actually inserted or updated.
        """
        if value is None:
            return True

        if self.data_type == "INT":
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        if self.data_type == "TEXT":
            return isinstance(value, str)

        if self.data_type == "FLOAT":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        if self.data_type == "BOOL":
            return isinstance(value, bool)

        return False

    def validate(self, value):
        """
        Validate that a value matches the column's data type.

        None represents SQL NULL.

        NULL is allowed when the column is nullable.
        NULL is rejected when the column is NOT NULL.

        UNIQUE is not checked here because uniqueness depends
        on comparing the value with other rows in the table.
        """
        # SQL NULL is represented by Python None.
        if value is None:
            return self.nullable

        return self._is_valid_value(value)

    def __repr__(self):
        """
        Return a readable representation of the column.
        """
        return (
            f"Column("
            f"name='{self.name}', "
            f"type='{self.data_type}', "
            f"nullable={self.nullable}, "
            f"unique={self.unique}, "
            f"default={self.default!r}, "
            f"has_default={self.has_default}"
            f")"
        )
    




class Condition:
    """
    Represents a basic SQL comparison condition.

    Examples:

        age >= 22
        name = 'Aditya'

    PyDB uses simplified NULL comparison semantics:

        Any comparison involving NULL returns False.
    """

    OPERATORS = {
        "=": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
    }

    def __init__(self, column_name, operator, value):
        """
        Store the column name, comparison operator,
        and value used by the condition.
        """
        if operator not in self.OPERATORS:
            raise ValueError(
                f"Unsupported operator: {operator}"
            )

        self.column_name = column_name
        self.operator = operator
        self.value = value

    def evaluate(self, row, columns):
        """
        Evaluate the condition against one table row.

        Returns True when the comparison succeeds.

        NULL comparisons return False.
        """
        for index, column in enumerate(columns):
            if column.name == self.column_name:
                actual_value = row[index]

                # PyDB uses simplified NULL comparison
                # semantics. Any comparison involving
                # NULL returns False.
                if actual_value is None or self.value is None:
                    return False

                operation = self.OPERATORS[self.operator]

                return operation(
                    actual_value,
                    self.value
                )

        raise ValueError(
            f"Column '{self.column_name}' does not exist"
        )


class BetweenCondition:
    """
    Represents a SQL BETWEEN condition.

    Example:

        age BETWEEN 18 AND 30

    BETWEEN is inclusive, meaning both boundary values
    are included.
    """

    def __init__(
        self,
        column_name,
        lower_value,
        upper_value
    ):
        """
        Store the column name and the inclusive lower
        and upper bounds.
        """
        self.column_name = column_name
        self.lower_value = lower_value
        self.upper_value = upper_value

    def evaluate(self, row, columns):
        """
        Evaluate the BETWEEN condition against one row.

        Returns True when the column value falls within
        the inclusive lower and upper bounds.

        NULL column values return False.
        """
        for index, column in enumerate(columns):
            if column.name == self.column_name:
                actual_value = row[index]

                if actual_value is None:
                    return False

                return (
                    self.lower_value
                    <= actual_value
                    <= self.upper_value
                )

        raise ValueError(
            f"Column '{self.column_name}' does not exist"
        )


class LikeCondition:
    """
    Represents a SQL LIKE condition.

    SQL LIKE supports two special wildcard characters:

        %  -> zero or more characters
        _  -> exactly one character

    Examples:

        name LIKE 'Adi%'
        name LIKE '%itya'
        name LIKE '%dit%'
        name LIKE 'A_i%'
    """

    def __init__(self, column_name, pattern):
        """
        Store the column name and LIKE pattern.
        """
        self.column_name = column_name
        self.pattern = pattern

    def evaluate(self, row, columns):
        """
        Evaluate the LIKE pattern against one table row.

        The SQL LIKE pattern is converted into a regular
        expression where:

            % becomes .*
            _ becomes .

        All other characters are treated literally.

        NULL column values return False.
        """
        import re

        for index, column in enumerate(columns):
            if column.name == self.column_name:
                actual_value = row[index]

                if actual_value is None:
                    return False

                actual_value = str(actual_value)

                regex_pattern = ""

                for character in self.pattern:
                    if character == "%":
                        regex_pattern += ".*"

                    elif character == "_":
                        regex_pattern += "."

                    else:
                        regex_pattern += re.escape(character)

                return re.fullmatch(
                    regex_pattern,
                    actual_value
                ) is not None

        raise ValueError(
            f"Column '{self.column_name}' does not exist"
        )


class InCondition:
    """
    Represents a SQL IN condition.

    Example:

        age IN (18, 20, 22, 25)

    The condition is True when the column value is equal
    to at least one value in the supplied list.
    """

    def __init__(self, column_name, values):
        """
        Store the column name and the values allowed
        by the IN condition.
        """
        if not values:
            raise ValueError(
                "IN requires at least one value"
            )

        self.column_name = column_name
        self.values = values

    def evaluate(self, row, columns):
        """
        Evaluate the IN condition against one table row.

        NULL column values return False.
        """
        for index, column in enumerate(columns):
            if column.name == self.column_name:
                actual_value = row[index]

                if actual_value is None:
                    return False

                return actual_value in self.values

        raise ValueError(
            f"Column '{self.column_name}' does not exist"
        )


class AndCondition:
    """
    Represents a logical AND between two conditions.
    """

    def __init__(self, left, right):
        """
        Store the left and right conditions.
        """
        self.left = left
        self.right = right

    def evaluate(self, row, columns):
        """
        Return True only when both conditions are True.
        """
        return (
            self.left.evaluate(row, columns)
            and self.right.evaluate(row, columns)
        )


class OrCondition:
    """
    Represents a logical OR between two conditions.
    """

    def __init__(self, left, right):
        """
        Store the left and right conditions.
        """
        self.left = left
        self.right = right

    def evaluate(self, row, columns):
        """
        Return True when at least one condition is True.
        """
        return (
            self.left.evaluate(row, columns)
            or self.right.evaluate(row, columns)
        )
    



#database.py
from pydb.table import Table
from pydb.storage import StorageEngine
from pydb.parser import Parser
from pydb.executor import QueryExecutor


class Database:
    """
    Represents the main database engine.

    The Database manages tables, persistence, and transactions.
    SQL parsing and query execution are delegated to the Parser
    and QueryExecutor respectively.
    """

    def __init__(self, file_path="pydb.json"):
        """
        Initialize the database, parser, and query executor.

        Existing database data is loaded from storage when the
        Database object is created.
        """
        self.tables = {}
        self.storage = StorageEngine(file_path)

        self.dirty = False
        self._snapshot = None

        # Create the SQL parser.
        self.parser = Parser()

        # Create the query executor and give it this database.
        self.executor = QueryExecutor(self)

        self._load()

    def create_table(self, name, columns, primary_key=None):
        """
        Create a new table in the database.

        primary_key optionally specifies the name of the column
        that should act as the table's primary key.

        Creating a table changes the database state, so the
        database is marked as dirty.
        """
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")

        table = Table(
            name,
            columns,
            primary_key=primary_key
        )

        self.tables[name] = table

        # Schema changes must be persisted.
        self.mark_dirty()

        return table

    def get_table(self, name):
        """
        Return an existing table by name.
        """
        if name not in self.tables:
            raise ValueError(f"Table '{name}' does not exist")

        return self.tables[name]

    def list_tables(self):
        """
        Return a list containing all table names.
        """
        return list(self.tables.keys())

    def drop_table(self, name):
        """
        Remove an existing table from the database.

        Dropping a table changes the database state, so the
        database is marked as dirty.
        """
        if name not in self.tables:
            raise ValueError(f"Table '{name}' does not exist")

        del self.tables[name]

        # Schema changes must be persisted.
        self.mark_dirty()

    def execute(self, sql):
        """
        Execute a SQL statement.

        The SQL statement is first converted into a Query Object
        by the Parser. The resulting Query Object is then passed
        to the QueryExecutor for execution.
        """
        query = self.parser.parse(sql)

        return self.executor.execute(query)

    def save(self):
        """
        Persist the current database state to storage.
        """
        data = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            }
        }

        self.storage.save(data)
        self.dirty = False

    def _load(self):
        """
        Load previously stored tables from the storage engine.
        """
        data = self.storage.load()

        for name, table_data in data.get("tables", {}).items():
            self.tables[name] = Table.from_dict(table_data)

    def mark_dirty(self):
        """
        Mark the database as containing unsaved changes.
        """
        self.dirty = True

    def begin(self):
        """
        Start a new database transaction.

        The current database state is copied into an in-memory
        snapshot so that it can later be restored if rollback
        is requested.
        """
        if self._snapshot is not None:
            raise RuntimeError("Transaction already active")

        self._snapshot = {
            name: table.to_dict()
            for name, table in self.tables.items()
        }

    def rollback(self):
        """
        Roll back the current transaction.

        The database is restored to the state captured when
        the transaction started.
        """
        if self._snapshot is None:
            raise RuntimeError("No active transaction")

        self.tables = {
            name: Table.from_dict(table_data)
            for name, table_data in self._snapshot.items()
        }

        self._snapshot = None
        self.dirty = False

    def commit(self):
        """
        Commit the current transaction.

        All current changes are persisted to storage and the
        transaction snapshot is removed.
        """
        if self._snapshot is None:
            raise RuntimeError("No active transaction")

        self.save()
        self._snapshot = None















from pydb.query import (
    InsertQuery,
    SelectQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    DropTableQuery,
    ShowTablesQuery,
    DescribeTableQuery,
    AggregateExpression,
    HavingCondition,
    HavingAndCondition,
    HavingOrCondition
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
                    # Explicit NULL remains None.
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

        # Duplicate column names are ambiguous because
        # there would be more than one value for the same
        # table column.
        if len(column_names) != len(set(column_names)):
            raise ValueError(
                "Duplicate column names are not allowed"
            )

        table_column_names = {
            column.name
            for column in table.columns
        }

        # Every supplied column must exist.
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
                    # Explicit NULL is preserved.
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

    def select(
        self,
        table_name,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None,
        group_by=None,
        having=None
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

        Normal SELECT queries continue using Table.select().

        Grouped and aggregate queries are handled by the executor
        because grouping and aggregation are query-level operations.
        """
        table = self.database.get_table(table_name)

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

            return table.select(
                columns=columns,
                condition=condition,
                order_by=order_by,
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

            # SELECT * is not meaningful for grouped queries
            # because the result represents groups rather than
            # individual source rows.
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

                    # Every normal selected column must be part
                    # of GROUP BY. Therefore all rows in the group
                    # contain the same logical value for it.
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

    def _contains_aggregate(self, columns):
        """
        Return True when the SELECT column list contains
        aggregate expressions.
        """
        if columns is None:
            return False

        return any(
            isinstance(column, AggregateExpression)
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

        This keeps the simplified PyDB NULL behavior consistent
        with filtering elsewhere in the engine.
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

    def _order_grouped_results(
        self,
        table,
        rows,
        expressions,
        order_by,
        descending
    ):
        """
        Sort grouped query results.

        ORDER BY can reference a selected normal expression.

        The current result format stores values only, so the
        expression must correspond to a selected expression.
        """
        order_index = None

        for index, expression in enumerate(expressions):
            if (
                isinstance(expression, str)
                and expression == order_by
            ):
                order_index = index
                break

        if order_index is None:
            raise ValueError(
                f"ORDER BY column '{order_by}' "
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

        if function_name in ("SUM", "AVG"):
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

        if column.data_type not in ("INT", "FLOAT"):
            raise TypeError(
                f"{column.data_type} column "
                f"'{column.name}' cannot be used with "
                f"SUM or AVG"
            )

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

    def execute(self, query):
        """
        Execute a Query Object and return its result.
        """

        if isinstance(query, InsertQuery):
            return self.insert(
                query.table_name,
                query.row,
                query.column_names
            )

        if isinstance(query, SelectQuery):
            return self.select(
                query.table_name,
                columns=query.columns,
                condition=query.condition,
                order_by=query.order_by,
                descending=query.descending,
                limit=query.limit,
                group_by=query.group_by,
                having=query.having
            )

        if isinstance(query, UpdateQuery):
            return self.update(
                query.table_name,
                query.updates,
                query.condition
            )

        if isinstance(query, DeleteQuery):
            return self.delete(
                query.table_name,
                query.condition
            )

        if isinstance(query, CreateTableQuery):
            return self.create_table(
                query.table_name,
                query.columns,
                query.primary_key
            )

        if isinstance(query, DropTableQuery):
            return self.database.drop_table(
                query.table_name
            )

        if isinstance(query, ShowTablesQuery):
            return self.database.list_tables()

        if isinstance(query, DescribeTableQuery):
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

        raise ValueError(
            f"Unsupported query type: {type(query).__name__}"
        )



class Token:
    """
    Represents one token produced by the SQL lexer.
    """

    def __init__(self, token_type, value):
        """
        Store the token's type and its actual value.
        """
        self.token_type = token_type
        self.value = value

    def __repr__(self):
        """
        Return a readable representation of the token.
        """
        return f"Token({self.token_type!r}, {self.value!r})"


class Lexer:
    """
    Converts a SQL query string into a sequence of tokens.
    """

    KEYWORDS = {
        "SELECT",
        "FROM",
        "WHERE",
        "INSERT",
        "INTO",
        "VALUES",
        "UPDATE",
        "SET",
        "DELETE",
        "CREATE",
        "TABLE",
        "TABLES",
        "DROP",
        "SHOW",
        "DESCRIBE",
        "NULL",
        "NOT",
        "UNIQUE",
        "DEFAULT",
        "PRIMARY",
        "KEY",
        "ORDER",
        "BY",
        "LIMIT",
        "AND",
        "OR",
        "BETWEEN",
        "LIKE",
        "IN",
        "ASC",
        "DESC",
        "GROUP",
        "HAVING",
    }

    OPERATORS = {
        "=",
        "!=",
        ">",
        "<",
        ">=",
        "<=",
    }

    def tokenize(self, sql):
        """
        Convert SQL text into a list of Token objects.
        """
        tokens = []
        position = 0

        while position < len(sql):
            character = sql[position]

            if character.isspace():
                position += 1
                continue

            if character in ",;()*":
                tokens.append(
                    Token("SYMBOL", character)
                )
                position += 1
                continue

            if character in "'\"":
                quote = character
                position += 1

                start = position

                while position < len(sql):
                    if sql[position] == quote:
                        break

                    position += 1

                if position >= len(sql):
                    raise ValueError(
                        "Unterminated string"
                    )

                value = sql[start:position]

                tokens.append(
                    Token("STRING", value)
                )

                position += 1
                continue

            if character.isdigit():
                start = position

                while position < len(sql) and (
                    sql[position].isdigit()
                    or sql[position] == "."
                ):
                    position += 1

                value = sql[start:position]

                if "." in value:
                    value = float(value)
                else:
                    value = int(value)

                tokens.append(
                    Token("NUMBER", value)
                )

                continue

            if character in "<>!=":
                operator = character

                if (
                    position + 1 < len(sql)
                    and sql[position + 1] == "="
                ):
                    operator += "="
                    position += 1

                if operator not in self.OPERATORS:
                    raise ValueError(
                        f"Unsupported operator: {operator}"
                    )

                tokens.append(
                    Token("OPERATOR", operator)
                )

                position += 1
                continue

            if character.isalpha() or character == "_":
                start = position

                while position < len(sql) and (
                    sql[position].isalnum()
                    or sql[position] == "_"
                ):
                    position += 1

                value = sql[start:position]

                upper_value = value.upper()

                if upper_value in self.KEYWORDS:
                    tokens.append(
                        Token("KEYWORD", upper_value)
                    )
                else:
                    tokens.append(
                        Token("IDENTIFIER", value)
                    )

                continue

            raise ValueError(
                f"Unexpected character: {character}"
            )

        return tokens
    

from pydb.lexer import Lexer
from pydb.condition import (
    Condition,
    BetweenCondition,
    LikeCondition,
    InCondition,
    AndCondition,
    OrCondition
)
from pydb.query import (
    SelectQuery,
    InsertQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    DropTableQuery,
    ShowTablesQuery,
    DescribeTableQuery,
    AggregateExpression,
    HavingCondition,
    HavingAndCondition,
    HavingOrCondition
)


class Parser:
    """
    Converts SQL text into Query Objects.
    """

    NO_DEFAULT = object()

    def __init__(self):
        """
        Create a lexer that will convert SQL text into tokens.
        """
        self.lexer = Lexer()

    def _parse_value(self, token, allow_default=False):
        """
        Convert a value token into the corresponding Python value.

        SQL NULL is represented internally by Python None.

        SQL DEFAULT is represented by InsertQuery.DEFAULT
        when allow_default=True.
        """
        if token.token_type == "NUMBER":
            return token.value

        if token.token_type == "STRING":
            return token.value

        if (
            token.token_type == "KEYWORD"
            and token.value == "NULL"
        ):
            return None

        if (
            allow_default
            and token.token_type == "KEYWORD"
            and token.value == "DEFAULT"
        ):
            return InsertQuery.DEFAULT

        raise ValueError(
            "Expected a valid value"
        )

    def parse(self, sql):
        """
        Tokenize SQL and parse it into a Query Object.
        """
        tokens = self.lexer.tokenize(sql)

        if not tokens:
            raise ValueError(
                "SQL query cannot be empty"
            )

        if tokens[0].token_type != "KEYWORD":
            raise ValueError(
                "Query must start with a SQL keyword"
            )

        if tokens[0].value == "SELECT":
            return self._parse_select(tokens)

        if tokens[0].value == "INSERT":
            return self._parse_insert(tokens)

        if tokens[0].value == "UPDATE":
            return self._parse_update(tokens)

        if tokens[0].value == "DELETE":
            return self._parse_delete(tokens)

        if tokens[0].value == "CREATE":
            return self._parse_create_table(tokens)

        if tokens[0].value == "DROP":
            return self._parse_drop_table(tokens)

        if tokens[0].value == "SHOW":
            return self._parse_show_tables(tokens)

        if tokens[0].value == "DESCRIBE":
            return self._parse_describe_table(tokens)

        raise ValueError(
            f"Unsupported SQL command: {tokens[0].value}"
        )

    def _parse_drop_table(self, tokens):
        """
        Parse DROP TABLE.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DROP requires TABLE"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLE"
        ):
            raise ValueError(
                "Expected TABLE after DROP"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "DROP TABLE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after TABLE"
            )

        table_name = token.value
        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DROP TABLE"
        )

        return DropTableQuery(
            table_name=table_name
        )

    def _parse_describe_table(self, tokens):
        """
        Parse DESCRIBE table_name.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DESCRIBE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after DESCRIBE"
            )

        table_name = token.value
        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DESCRIBE"
        )

        return DescribeTableQuery(
            table_name=table_name
        )

    def _parse_show_tables(self, tokens):
        """
        Parse SHOW TABLES.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "SHOW requires TABLES"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLES"
        ):
            raise ValueError(
                "Expected TABLES after SHOW"
            )

        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "SHOW TABLES"
        )

        return ShowTablesQuery()

    def _parse_condition(self, tokens, position):
        """
        Parse a single WHERE condition.
        """
        if position >= len(tokens):
            raise ValueError(
                "Expected column name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected column name in condition"
            )

        column_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "Expected operator after column name"
            )

        token = tokens[position]

        if (
            token.token_type == "KEYWORD"
            and token.value == "BETWEEN"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires a lower value"
                )

            lower_token = tokens[position]

            if lower_token.token_type not in (
                "NUMBER",
                "STRING"
            ):
                raise ValueError(
                    "BETWEEN requires a valid lower value"
                )

            lower_value = lower_token.value
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires AND"
                )

            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value != "AND"
            ):
                raise ValueError(
                    "BETWEEN requires AND"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires an upper value"
                )

            upper_token = tokens[position]

            if upper_token.token_type not in (
                "NUMBER",
                "STRING"
            ):
                raise ValueError(
                    "BETWEEN requires a valid upper value"
                )

            upper_value = upper_token.value
            position += 1

            return (
                BetweenCondition(
                    column_name,
                    lower_value,
                    upper_value
                ),
                position
            )

        if (
            token.token_type == "KEYWORD"
            and token.value == "LIKE"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "LIKE requires a pattern"
                )

            pattern_token = tokens[position]

            if pattern_token.token_type != "STRING":
                raise ValueError(
                    "LIKE requires a string pattern"
                )

            position += 1

            return (
                LikeCondition(
                    column_name,
                    pattern_token.value
                ),
                position
            )

        if (
            token.token_type == "KEYWORD"
            and token.value == "IN"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "IN requires parentheses"
                )

            token = tokens[position]

            if not (
                token.token_type == "SYMBOL"
                and token.value == "("
            ):
                raise ValueError(
                    "Expected '(' after IN"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "IN requires at least one value"
                )

            if (
                tokens[position].token_type == "SYMBOL"
                and tokens[position].value == ")"
            ):
                raise ValueError(
                    "IN requires at least one value"
                )

            values = []

            while position < len(tokens):
                token = tokens[position]

                if token.token_type not in (
                    "NUMBER",
                    "STRING"
                ):
                    raise ValueError(
                        "IN requires valid values"
                    )

                values.append(token.value)
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "IN requires closing parenthesis"
                    )

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "Expected value after comma in IN"
                        )

                    if (
                        tokens[position].token_type == "SYMBOL"
                        and tokens[position].value == ")"
                    ):
                        raise ValueError(
                            "Expected value after comma in IN"
                        )

                    continue

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ")"
                ):
                    position += 1
                    break

                raise ValueError(
                    "Expected ',' or ')' in IN list"
                )

            return (
                InCondition(
                    column_name,
                    values
                ),
                position
            )

        if token.token_type != "OPERATOR":
            raise ValueError(
                "Expected operator after column name"
            )

        operator = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "Expected value after operator"
            )

        token = tokens[position]

        if token.token_type not in (
            "NUMBER",
            "STRING"
        ):
            raise ValueError(
                "Expected value after operator"
            )

        value = token.value
        position += 1

        return (
            Condition(
                column_name,
                operator,
                value
            ),
            position
        )

    def _parse_logical_conditions(self, tokens, position):
        """
        Parse a condition followed by optional AND/OR conditions.
        """
        condition, position = self._parse_condition(
            tokens,
            position
        )

        while position < len(tokens):
            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value not in ("AND", "OR")
            ):
                break

            logical_operator = token.value
            position += 1

            right_condition, position = (
                self._parse_condition(
                    tokens,
                    position
                )
            )

            if logical_operator == "AND":
                condition = AndCondition(
                    condition,
                    right_condition
                )
            else:
                condition = OrCondition(
                    condition,
                    right_condition
                )

        return condition, position

    def _parse_select_expression(self, tokens, position):
        """
        Parse one SELECT expression.

        Supported expressions:

            column
            COUNT(*)
            COUNT(column)
            SUM(column)
            AVG(column)
            MIN(column)
            MAX(column)
        """
        if position >= len(tokens):
            raise ValueError(
                "Expected a SELECT expression"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected a column name or aggregate function"
            )

        name = token.value
        position += 1

        if position >= len(tokens):
            return name, position

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            return name, position

        function_name = name.upper()

        if function_name not in (
            AggregateExpression.SUPPORTED_FUNCTIONS
        ):
            raise ValueError(
                f"Unsupported aggregate function: {name}"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                f"{function_name} requires an argument"
            )

        token = tokens[position]

        if (
            token.token_type == "SYMBOL"
            and token.value == "*"
        ):
            if function_name != "COUNT":
                raise ValueError(
                    f"{function_name}(*) is not supported"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    f"{function_name}(*) requires closing parenthesis"
                )

            token = tokens[position]

            if not (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                raise ValueError(
                    f"{function_name}(*) requires closing parenthesis"
                )

            position += 1

            return (
                AggregateExpression(
                    "COUNT",
                    None
                ),
                position
            )

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                f"{function_name} requires a column name"
            )

        column_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                f"{function_name} requires closing parenthesis"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == ")"
        ):
            raise ValueError(
                f"{function_name} requires closing parenthesis"
            )

        position += 1

        return (
            AggregateExpression(
                function_name,
                column_name
            ),
            position
        )

    def _parse_having_condition(self, tokens, position):
        """
        Parse one HAVING comparison.

        Supported forms:

            HAVING COUNT(*) > 2
            HAVING COUNT(id) >= 2
            HAVING AVG(age) > 20
            HAVING department = 'Engineering'

        Returns the created HAVING condition and the next
        token position.
        """
        if position >= len(tokens):
            raise ValueError(
                "HAVING requires a condition"
            )

        token = tokens[position]

        # ---------------------------------
        # Aggregate expression
        # ---------------------------------

        if (
            token.token_type == "IDENTIFIER"
            and position + 1 < len(tokens)
            and tokens[position + 1].token_type == "SYMBOL"
            and tokens[position + 1].value == "("
        ):
            expression, position = (
                self._parse_select_expression(
                    tokens,
                    position
                )
            )

            if not isinstance(
                expression,
                AggregateExpression
            ):
                raise ValueError(
                    "HAVING expression must be an aggregate "
                    "or GROUP BY column"
                )

        # ---------------------------------
        # Normal GROUP BY column
        # ---------------------------------

        else:
            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected aggregate or column in HAVING"
                )

            expression = token.value
            position += 1

        # ---------------------------------
        # Comparison operator
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "HAVING requires an operator"
            )

        token = tokens[position]

        if token.token_type != "OPERATOR":
            raise ValueError(
                "Expected operator in HAVING"
            )

        operator = token.value
        position += 1

        # ---------------------------------
        # Comparison value
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "HAVING requires a comparison value"
            )

        token = tokens[position]

        if token.token_type not in (
            "NUMBER",
            "STRING",
            "KEYWORD"
        ):
            raise ValueError(
                "Expected a valid HAVING value"
            )

        value = self._parse_value(token)
        position += 1

        return (
            HavingCondition(
                expression,
                operator,
                value
            ),
            position
        )

    def _parse_group_by(self, tokens, position):
        """
        Parse a GROUP BY column list.

        Example:

            GROUP BY department

        or:

            GROUP BY department, city
        """
        if position >= len(tokens):
            raise ValueError(
                "GROUP BY requires at least one column"
            )

        columns = []

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name after GROUP BY"
                )

            columns.append(token.value)
            position += 1

            if position >= len(tokens):
                break

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "Expected column after GROUP BY comma"
                    )

                continue

            break

        return columns, position

    def _parse_select(self, tokens):
        """
        Parse a SELECT statement and create a SelectQuery object.

        Supported syntax:

            SELECT *
            SELECT name, age

        Aggregate syntax:

            SELECT COUNT(*)
            SELECT COUNT(age)
            SELECT SUM(age)
            SELECT AVG(age)
            SELECT MIN(age)
            SELECT MAX(age)

        GROUP BY syntax:

            SELECT department, COUNT(*)
            FROM users
            GROUP BY department

        HAVING syntax:

            SELECT department, COUNT(*)
            FROM users
            GROUP BY department
            HAVING COUNT(*) > 2
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "SELECT requires columns"
            )

        # ---------------------------------
        # SELECT expressions
        # ---------------------------------

        if (
            tokens[position].token_type == "SYMBOL"
            and tokens[position].value == "*"
        ):
            columns = None
            position += 1

        else:
            columns = []

            while position < len(tokens):

                expression, position = (
                    self._parse_select_expression(
                        tokens,
                        position
                    )
                )

                columns.append(expression)

                if position >= len(tokens):
                    break

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "Expected column after comma"
                        )

                    continue

                break

        # ---------------------------------
        # FROM
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "SELECT requires FROM"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "FROM"
        ):
            raise ValueError(
                "Expected FROM after column list"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "FROM requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after FROM"
            )

        table_name = token.value
        position += 1

        # ---------------------------------
        # WHERE
        # ---------------------------------

        condition = None

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "WHERE"
            ):
                position += 1

                condition, position = (
                    self._parse_condition(
                        tokens,
                        position
                    )
                )

                while position < len(tokens):
                    token = tokens[position]

                    if (
                        token.token_type != "KEYWORD"
                        or token.value not in ("AND", "OR")
                    ):
                        break

                    logical_operator = token.value
                    position += 1

                    right_condition, position = (
                        self._parse_condition(
                            tokens,
                            position
                        )
                    )

                    if logical_operator == "AND":
                        condition = AndCondition(
                            condition,
                            right_condition
                        )

                    else:
                        condition = OrCondition(
                            condition,
                            right_condition
                        )

        # ---------------------------------
        # GROUP BY
        # ---------------------------------

        group_by = None

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "GROUP"
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "GROUP requires BY"
                    )

                token = tokens[position]

                if (
                    token.token_type != "KEYWORD"
                    or token.value != "BY"
                ):
                    raise ValueError(
                        "Expected BY after GROUP"
                    )

                position += 1

                group_by = []

                while position < len(tokens):

                    token = tokens[position]

                    if token.token_type != "IDENTIFIER":
                        raise ValueError(
                            "Expected column name after GROUP BY"
                        )

                    group_by.append(token.value)
                    position += 1

                    if position >= len(tokens):
                        break

                    token = tokens[position]

                    if (
                        token.token_type == "SYMBOL"
                        and token.value == ","
                    ):
                        position += 1

                        if position >= len(tokens):
                            raise ValueError(
                                "Expected column after comma"
                            )

                        continue

                    break

        # ---------------------------------
        # HAVING
        # ---------------------------------

        having = None

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "HAVING"
            ):
                position += 1

                having, position = (
                    self._parse_having_condition(
                        tokens,
                        position
                    )
                )

                while position < len(tokens):
                    token = tokens[position]

                    if (
                        token.token_type != "KEYWORD"
                        or token.value not in ("AND", "OR")
                    ):
                        break

                    logical_operator = token.value
                    position += 1

                    right_condition, position = (
                        self._parse_having_condition(
                            tokens,
                            position
                        )
                    )

                    if logical_operator == "AND":
                        having = HavingAndCondition(
                            having,
                            right_condition
                        )

                    else:
                        having = HavingOrCondition(
                            having,
                            right_condition
                        )

        # ---------------------------------
        # ORDER BY
        # ---------------------------------

        order_by = None
        descending = False

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "ORDER"
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "ORDER requires BY"
                    )

                token = tokens[position]

                if (
                    token.token_type != "KEYWORD"
                    or token.value != "BY"
                ):
                    raise ValueError(
                        "Expected BY after ORDER"
                    )

                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "ORDER BY requires a column"
                    )

                token = tokens[position]

                if token.token_type != "IDENTIFIER":
                    raise ValueError(
                        "Expected column name after ORDER BY"
                    )

                order_by = token.value
                position += 1

                if position < len(tokens):
                    token = tokens[position]

                    if (
                        token.token_type == "KEYWORD"
                        and token.value in ("ASC", "DESC")
                    ):
                        descending = (
                            token.value == "DESC"
                        )
                        position += 1

        # ---------------------------------
        # LIMIT
        # ---------------------------------

        limit = None

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "LIMIT"
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "LIMIT requires a number"
                    )

                token = tokens[position]

                if (
                    token.token_type != "NUMBER"
                    or not isinstance(token.value, int)
                ):
                    raise ValueError(
                        "LIMIT requires an integer"
                    )

                if token.value < 0:
                    raise ValueError(
                        "LIMIT cannot be negative"
                    )

                limit = token.value
                position += 1

        # ---------------------------------
        # Semicolon
        # ---------------------------------

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ";"
            ):
                position += 1

        if position < len(tokens):
            raise ValueError(
                "Unexpected token after SELECT statement"
            )

        # ---------------------------------
        # Query-level validation
        # ---------------------------------

        has_aggregate = (
            columns is not None
            and any(
                isinstance(
                    column,
                    AggregateExpression
                )
                for column in columns
            )
        )

        has_normal_column = (
            columns is not None
            and any(
                isinstance(
                    column,
                    str
                )
                for column in columns
            )
        )

        # Mixing normal columns and aggregates is now allowed
        # when GROUP BY is present.
        if (
            has_aggregate
            and has_normal_column
            and group_by is None
        ):
            raise ValueError(
                "Cannot mix aggregate and normal columns "
                "without GROUP BY"
            )

        if group_by is not None and columns is None:
            raise ValueError(
                "SELECT * cannot be used with GROUP BY"
            )

        if having is not None and (
            group_by is None
            and not has_aggregate
        ):
            raise ValueError(
                "HAVING requires GROUP BY or an aggregate query"
            )

        return SelectQuery(
            table_name=table_name,
            columns=columns,
            condition=condition,
            order_by=order_by,
            descending=descending,
            limit=limit,
            group_by=group_by,
            having=having
        )

    def _validate_select_grouping(
        self,
        columns,
        group_by
    ):
        """
        Validate combinations of normal columns, aggregates,
        and GROUP BY.

        Without GROUP BY:

            SELECT COUNT(*)
                -> valid

            SELECT name, COUNT(*)
                -> invalid

        With GROUP BY:

            SELECT department, COUNT(*)
                GROUP BY department
                -> valid

            SELECT name, COUNT(*)
                GROUP BY department
                -> invalid
        """
        if columns is None:
            if group_by:
                raise ValueError(
                    "GROUP BY cannot be used with SELECT *"
                )

            return

        has_aggregate = any(
            isinstance(
                column,
                AggregateExpression
            )
            for column in columns
        )

        has_normal_column = any(
            isinstance(
                column,
                str
            )
            for column in columns
        )

        if not group_by:
            if has_aggregate and has_normal_column:
                raise ValueError(
                    "Cannot mix aggregate and normal columns "
                    "without GROUP BY"
                )

            return

        # GROUP BY is present.
        for column in columns:
            if isinstance(column, str):
                if column not in group_by:
                    raise ValueError(
                        f"Column '{column}' must appear "
                        f"in GROUP BY"
                    )

    def _consume_semicolon(self, tokens, position):
        """
        Consume an optional semicolon.
        """
        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ";"
            ):
                position += 1

        return position

    def _ensure_end(
        self,
        tokens,
        position,
        statement_name
    ):
        """
        Ensure that no unexpected tokens remain.
        """
        if position < len(tokens):
            raise ValueError(
                f"Unexpected token after "
                f"{statement_name} statement"
            )

    def _parse_insert(self, tokens):
        """
        Parse an INSERT statement.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "INSERT requires INTO"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "INTO"
        ):
            raise ValueError(
                "Expected INTO after INSERT"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "INSERT INTO requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after INTO"
            )

        table_name = token.value
        position += 1

        column_names = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "SYMBOL"
            and tokens[position].value == "("
        ):
            position += 1
            column_names = []

            if position >= len(tokens):
                raise ValueError(
                    "INSERT column list cannot be empty"
                )

            while position < len(tokens):
                token = tokens[position]

                if token.token_type != "IDENTIFIER":
                    raise ValueError(
                        "Expected column name in INSERT column list"
                    )

                column_names.append(token.value)
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "Expected ')' after INSERT column list"
                    )

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1
                    continue

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ")"
                ):
                    position += 1
                    break

                raise ValueError(
                    "Expected ',' or ')' after INSERT column name"
                )

        if position >= len(tokens):
            raise ValueError(
                "INSERT requires VALUES"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "VALUES"
        ):
            raise ValueError(
                "Expected VALUES after table name or column list"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "VALUES requires parentheses"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            raise ValueError(
                "Expected '(' after VALUES"
            )

        position += 1

        row = []

        if position >= len(tokens):
            raise ValueError(
                "VALUES requires at least one value"
            )

        while position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                raise ValueError(
                    "VALUES requires at least one value"
                )

            row.append(
                self._parse_value(
                    token,
                    allow_default=True
                )
            )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "VALUES requires closing parenthesis"
                )

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                position += 1
                break

            raise ValueError(
                "Expected ',' or ')' after value"
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "INSERT"
        )

        if (
            column_names is not None
            and len(column_names) != len(row)
        ):
            raise ValueError(
                "Number of columns must match number of values"
            )

        return InsertQuery(
            table_name=table_name,
            row=row,
            column_names=column_names
        )

    def _parse_update(self, tokens):
        """
        Parse an UPDATE statement.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "UPDATE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after UPDATE"
            )

        table_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "UPDATE requires SET"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "SET"
        ):
            raise ValueError(
                "Expected SET after table name"
            )

        position += 1

        updates = {}

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name after SET"
                )

            column_name = token.value
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected '=' after column name"
                )

            token = tokens[position]

            if not (
                token.token_type == "OPERATOR"
                and token.value == "="
            ):
                raise ValueError(
                    "Expected '=' after column name"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected value after '='"
                )

            updates[column_name] = self._parse_value(
                tokens[position]
            )

            position += 1

            if position >= len(tokens):
                break

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "KEYWORD"
                and token.value == "WHERE"
            ):
                break

            if (
                token.token_type == "SYMBOL"
                and token.value == ";"
            ):
                break

            raise ValueError(
                "Expected ',' or WHERE after update value"
            )

        condition = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "WHERE"
        ):
            position += 1

            condition, position = (
                self._parse_logical_conditions(
                    tokens,
                    position
                )
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "UPDATE"
        )

        return UpdateQuery(
            table_name=table_name,
            updates=updates,
            condition=condition
        )

    def _parse_delete(self, tokens):
        """
        Parse a DELETE statement.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DELETE requires FROM"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "FROM"
        ):
            raise ValueError(
                "Expected FROM after DELETE"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "DELETE FROM requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after FROM"
            )

        table_name = token.value
        position += 1

        condition = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "WHERE"
        ):
            position += 1

            condition, position = (
                self._parse_logical_conditions(
                    tokens,
                    position
                )
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DELETE"
        )

        return DeleteQuery(
            table_name=table_name,
            condition=condition
        )

    def _parse_create_table(self, tokens):
        """
        Parse CREATE TABLE with NOT NULL, UNIQUE,
        PRIMARY KEY and DEFAULT constraints.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE requires TABLE"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLE"
        ):
            raise ValueError(
                "Expected TABLE after CREATE"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE TABLE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after TABLE"
            )

        table_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE TABLE requires column definitions"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            raise ValueError(
                "Expected '(' after table name"
            )

        position += 1

        columns = []
        primary_key = None

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name"
                )

            column_name = token.value
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected data type after column name"
                )

            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected data type after column name"
                )

            data_type = token.value.upper()
            position += 1

            nullable = True
            unique = False
            is_primary_key = False
            default = self.NO_DEFAULT

            while position < len(tokens):
                token = tokens[position]

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "NOT"
                ):
                    if position + 1 >= len(tokens):
                        raise ValueError(
                            "Expected NULL after NOT"
                        )

                    next_token = tokens[position + 1]

                    if (
                        next_token.token_type != "KEYWORD"
                        or next_token.value != "NULL"
                    ):
                        raise ValueError(
                            "Expected NULL after NOT"
                        )

                    nullable = False
                    position += 2
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "UNIQUE"
                ):
                    unique = True
                    position += 1
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "PRIMARY"
                ):
                    if position + 1 >= len(tokens):
                        raise ValueError(
                            "Expected KEY after PRIMARY"
                        )

                    next_token = tokens[position + 1]

                    if (
                        next_token.token_type != "KEYWORD"
                        or next_token.value != "KEY"
                    ):
                        raise ValueError(
                            "Expected KEY after PRIMARY"
                        )

                    is_primary_key = True
                    position += 2
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "DEFAULT"
                ):
                    if default is not self.NO_DEFAULT:
                        raise ValueError(
                            "Duplicate DEFAULT constraint"
                        )

                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "DEFAULT requires a value"
                        )

                    default = self._parse_value(
                        tokens[position]
                    )

                    position += 1
                    continue

                break

            if is_primary_key:
                if primary_key is not None:
                    raise ValueError(
                        "Multiple primary keys are not supported"
                    )

                primary_key = column_name

            if default is not self.NO_DEFAULT:
                columns.append(
                    (
                        column_name,
                        data_type,
                        nullable,
                        unique,
                        default
                    )
                )

            elif unique:
                columns.append(
                    (
                        column_name,
                        data_type,
                        nullable,
                        True
                    )
                )

            elif nullable:
                columns.append(
                    (column_name, data_type)
                )

            else:
                columns.append(
                    (
                        column_name,
                        data_type,
                        False
                    )
                )

            if position >= len(tokens):
                raise ValueError(
                    "Expected ',' or ')' after column definition"
                )

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                position += 1
                break

            raise ValueError(
                "Expected ',' or ')' after column definition"
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "CREATE TABLE"
        )

        return CreateTableQuery(
            table_name=table_name,
            columns=columns,
            primary_key=primary_key
        )
    


class AggregateExpression:
    """
    Represents a SQL aggregate function.

    Supported aggregate functions:

        COUNT(*)
        COUNT(column)
        SUM(column)
        AVG(column)
        MIN(column)
        MAX(column)

    AggregateExpression only stores the parsed SQL information.
    The actual calculation is performed by QueryExecutor.
    """

    SUPPORTED_FUNCTIONS = {
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX"
    }

    def __init__(self, function_name, column_name=None):
        """
        Store the aggregate function and target column.

        column_name=None is used specifically for COUNT(*).
        """
        function_name = function_name.upper()

        if function_name not in self.SUPPORTED_FUNCTIONS:
            raise ValueError(
                f"Unsupported aggregate function: {function_name}"
            )

        self.function_name = function_name
        self.column_name = column_name

    @property
    def is_count_all(self):
        """
        Return True when this expression represents COUNT(*).
        """
        return (
            self.function_name == "COUNT"
            and self.column_name is None
        )

    def __repr__(self):
        """
        Return a readable representation of the aggregate.
        """
        if self.is_count_all:
            return "AggregateExpression('COUNT', '*')"

        return (
            f"AggregateExpression("
            f"{self.function_name!r}, "
            f"{self.column_name!r}"
            f")"
        )


class HavingCondition:
    """
    Represents one condition used by the SQL HAVING clause.

    HAVING is evaluated after rows have been grouped, so it is
    different from the normal WHERE Condition.

    Examples:

        HAVING COUNT(*) > 2
        HAVING AVG(age) >= 20
        HAVING department = 'Engineering'
    """

    def __init__(self, expression, operator, value):
        """
        Store the expression, comparison operator, and value.

        expression can be either:

            - an AggregateExpression
            - a normal column name
        """
        self.expression = expression
        self.operator = operator
        self.value = value

    def __repr__(self):
        """
        Return a readable representation of the HAVING condition.
        """
        return (
            f"HavingCondition("
            f"{self.expression!r}, "
            f"{self.operator!r}, "
            f"{self.value!r}"
            f")"
        )


class HavingAndCondition:
    """
    Represents a logical AND between two HAVING conditions.
    """

    def __init__(self, left, right):
        """
        Store the left and right HAVING conditions.
        """
        self.left = left
        self.right = right


class HavingOrCondition:
    """
    Represents a logical OR between two HAVING conditions.
    """

    def __init__(self, left, right):
        """
        Store the left and right HAVING conditions.
        """
        self.left = left
        self.right = right


class InsertQuery:
    """
    Represents an INSERT operation.

    An INSERT query contains:

        - the target table name
        - the values to insert
        - an optional list of column names

    When column_names is None, values are interpreted according
    to the table's complete column order.

    When column_names is provided, values correspond only to
    those specified columns.
    """

    # Sentinel used to represent SQL DEFAULT.
    #
    # None is already used for SQL NULL, so DEFAULT must have
    # its own distinct representation.
    DEFAULT = object()

    def __init__(self, table_name, row, column_names=None):
        """
        Store the target table, optional column list, and row
        values that should be inserted.

        column_names=None means that the INSERT uses the
        complete table column order.
        """
        self.table_name = table_name
        self.row = row
        self.column_names = column_names


class SelectQuery:
    """
    Represents a SELECT operation.
    """

    def __init__(
        self,
        table_name,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None,
        group_by=None,
        having=None
    ):
        """
        Store all information required to perform a SELECT.

        columns can contain:

            None
                SELECT *

            column-name strings
                Normal column selection

            AggregateExpression objects
                SQL aggregate functions

        group_by contains the column names used for grouping.

        having contains the condition evaluated after grouping.
        """
        self.table_name = table_name
        self.columns = columns
        self.condition = condition
        self.order_by = order_by
        self.descending = descending
        self.limit = limit
        self.group_by = group_by
        self.having = having


class UpdateQuery:
    """
    Represents an UPDATE operation.
    """

    def __init__(self, table_name, updates, condition=None):
        """
        Store the table, values to update, and optional condition.
        """
        self.table_name = table_name
        self.updates = updates
        self.condition = condition


class DeleteQuery:
    """
    Represents a DELETE operation.
    """

    def __init__(self, table_name, condition=None):
        """
        Store the target table and optional deletion condition.
        """
        self.table_name = table_name
        self.condition = condition


class CreateTableQuery:
    """
    Represents a CREATE TABLE operation.
    """

    def __init__(self, table_name, columns, primary_key=None):
        """
        Store the table name, column definitions, and optional
        primary-key column.
        """
        self.table_name = table_name
        self.columns = columns
        self.primary_key = primary_key


class DropTableQuery:
    """
    Represents a DROP TABLE operation.
    """

    def __init__(self, table_name):
        """
        Store the name of the table that should be removed.
        """
        self.table_name = table_name


class ShowTablesQuery:
    """
    Represents a SHOW TABLES operation.
    """

    def __init__(self):
        """
        Create a query object for listing all database tables.
        """
        pass


class DescribeTableQuery:
    """
    Represents a DESCRIBE TABLE operation.
    """

    def __init__(self, table_name):
        """
        Store the name of the table whose schema should be
        inspected.
        """
        self.table_name = table_name


#storage.py

import json
from pathlib import Path


class StorageEngine:
    """
    Handles persistent storage of database data.

    A normal file path stores data on disk.

    The special path ':memory:' creates an in-memory storage
    engine that does not read from or write to a file.
    """

    def __init__(self, file_path="pydb.json"):
        """
        Initialize the storage engine.

        ':memory:' is treated as a special in-memory mode.
        """
        self.file_path = Path(file_path)
        self.in_memory = file_path == ":memory:"

    def save(self, data):
        """
        Save database data to disk.

        In-memory databases do not persist their data to disk.
        """
        if self.in_memory:
            return

        with self.file_path.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4
            )

    def load(self):
        """
        Load database data from disk.

        In-memory databases always start with an empty state.
        """
        if self.in_memory:
            return {}

        if not self.file_path.exists():
            return {}

        with self.file_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)


from pydb.column import Column


class Table:
    """
    Represents a database table.

    A table contains a schema defined by its columns and the
    rows belonging to that schema. A table can optionally have
    a primary key column.

    Column definitions support:

        (name, data_type)

        (name, data_type, nullable)

        (name, data_type, nullable, unique)

        (name, data_type, nullable, unique, default)

    The two-value format keeps nullable=True and unique=False
    as the defaults.

    The five-value format additionally stores a DEFAULT value.
    """

    def __init__(self, name, columns, primary_key=None):
        """
        Create a table with the given columns and optional
        primary key.

        Each column definition can contain:

            (column_name, data_type)

            (column_name, data_type, nullable)

            (column_name, data_type, nullable, unique)

            (column_name, data_type, nullable, unique, default)

        nullable=True means NULL values are allowed.

        nullable=False means the column behaves as NOT NULL.

        unique=True means duplicate non-NULL values are rejected
        by the table.

        The five-value format specifies a DEFAULT value.

        DEFAULT metadata is stored by the Table, but the default
        is not automatically applied during INSERT yet.

        primary_key must be the name of one of the table's
        columns when provided.
        """
        if not name:
            raise ValueError("Table name cannot be empty")

        if not columns:
            raise ValueError("Table must have at least one column")

        self.name = name

        self.columns = []

        for column_definition in columns:
            if len(column_definition) == 2:
                column_name, data_type = column_definition

                nullable = True
                unique = False
                default = Column.NO_DEFAULT

            elif len(column_definition) == 3:
                column_name, data_type, nullable = column_definition

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

            self.columns.append(
                Column(
                    column_name,
                    data_type,
                    nullable=nullable,
                    unique=unique,
                    default=default
                )
            )

        # Store the primary-key column name.
        self.primary_key = primary_key

        # Validate that the primary key refers to an existing column.
        if self.primary_key is not None:
            if not any(
                column.name == self.primary_key
                for column in self.columns
            ):
                raise ValueError(
                    f"Primary key column "
                    f"'{self.primary_key}' does not exist"
                )

        self.rows = []

    def _validate_row(self, row):
        """
        Validate that a row has the correct number of values
        and that every value matches its column's data type.

        Column validation also handles the NULL / NOT NULL
        constraint.
        """
        if len(row) != len(self.columns):
            raise ValueError(
                f"Expected {len(self.columns)} values, got {len(row)}"
            )

        for column, value in zip(self.columns, row):
            if not column.validate(value):
                raise TypeError(
                    f"Column '{column.name}' expects {column.data_type}"
                )

    def _validate_primary_key(self, row):
        """
        Validate that the primary-key value is unique.

        A duplicate primary-key value is not allowed.
        """
        if self.primary_key is None:
            return

        primary_key_index = None

        for index, column in enumerate(self.columns):
            if column.name == self.primary_key:
                primary_key_index = index
                break

        primary_key_value = row[primary_key_index]

        for existing_row in self.rows:
            if existing_row[primary_key_index] == primary_key_value:
                raise ValueError(
                    f"Duplicate primary key value: "
                    f"{primary_key_value}"
                )

    def _validate_unique_constraints(self, row):
        """
        Validate UNIQUE constraints for a new row.

        NULL values are ignored because a nullable UNIQUE column
        is allowed to contain multiple NULL values.

        Uniqueness is checked against all existing rows.
        """
        for column_index, column in enumerate(self.columns):
            if not column.unique:
                continue

            value = row[column_index]

            # Multiple NULL values are allowed for a nullable
            # UNIQUE column.
            if value is None:
                continue

            for existing_row in self.rows:
                if existing_row[column_index] == value:
                    raise ValueError(
                        f"Duplicate value for UNIQUE column "
                        f"'{column.name}': {value}"
                    )

    def insert(self, row):
        """
        Insert a new row after validating its structure,
        data types, NULL constraints, primary-key uniqueness,
        and UNIQUE constraints.

        DEFAULT values are not applied here yet.
        """
        self._validate_row(row)
        self._validate_primary_key(row)
        self._validate_unique_constraints(row)

        self.rows.append(row)

    def to_dict(self):
        """
        Convert the table into a dictionary suitable for
        persistent storage.

        The nullable, unique, and default properties of every
        column are persisted so that schema metadata survives
        database reloads.

        has_default is also persisted so that the database can
        distinguish between:

            no DEFAULT

        and:

            DEFAULT NULL
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
            "rows": [row.copy() for row in self.rows]
        }

    @classmethod
    def from_dict(cls, data):
        """
        Reconstruct a Table object from its stored dictionary.

        Older database files may not contain the nullable,
        unique, default, or has_default properties.

        In those cases:

            nullable defaults to True

            unique defaults to False

            no DEFAULT is assumed

        This preserves backward compatibility with older
        PyDB database files.
        """
        columns = []

        for column in data["columns"]:
            nullable = column.get("nullable", True)
            unique = column.get("unique", False)

            # Determine whether this column originally had
            # an explicit DEFAULT clause.
            #
            # New database files store has_default explicitly.
            # Older files do not, so they are treated as having
            # no DEFAULT.
            has_default = column.get("has_default", False)

            if has_default:
                default = column.get("default")
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
            primary_key=data.get("primary_key")
        )

        for row in data["rows"]:
            table.insert(row)

        return table

    def select(
        self,
        columns=None,
        condition=None,
        order_by=None,
        descending=False,
        limit=None
    ):
        """
        Retrieve rows matching the requested columns, condition,
        ordering, and limit without modifying the table.
        """
        rows = self.rows.copy()

        if condition is not None:
            rows = [
                row for row in rows
                if condition.evaluate(row, self.columns)
            ]

        if order_by is not None:
            column_index = None

            for index, column in enumerate(self.columns):
                if column.name == order_by:
                    column_index = index
                    break

            if column_index is None:
                raise ValueError(
                    f"Column '{order_by}' does not exist"
                )

            rows.sort(
                key=lambda row: row[column_index],
                reverse=descending
            )

        if limit is not None:
            if limit < 0:
                raise ValueError("Limit cannot be negative")

            rows = rows[:limit]

        if columns is None:
            return rows

        column_indexes = []

        for column_name in columns:
            for index, column in enumerate(self.columns):
                if column.name == column_name:
                    column_indexes.append(index)
                    break
            else:
                raise ValueError(
                    f"Column '{column_name}' does not exist"
                )

        return [
            [row[index] for index in column_indexes]
            for row in rows
        ]

    def update(self, updates, condition=None):
        """
        Update rows that satisfy the given condition.

        Column validation is performed before assigning each new
        value, which also enforces NULL / NOT NULL constraints.

        Primary-key uniqueness and UNIQUE constraints are
        checked before changing values.

        DEFAULT values are not applied during UPDATE.
        """
        affected_rows = 0

        primary_key_index = None

        if self.primary_key is not None:
            for index, column in enumerate(self.columns):
                if column.name == self.primary_key:
                    primary_key_index = index
                    break

        for row in self.rows:
            if condition is not None:
                if not condition.evaluate(row, self.columns):
                    continue

            # Check whether this update changes the primary key.
            if self.primary_key in updates:
                new_primary_key = updates[self.primary_key]

                if not self.columns[primary_key_index].validate(
                    new_primary_key
                ):
                    raise TypeError(
                        f"Column '{self.primary_key}' expects "
                        f"{self.columns[primary_key_index].data_type}"
                    )

                for existing_row in self.rows:
                    if (
                        existing_row is not row
                        and existing_row[primary_key_index]
                        == new_primary_key
                    ):
                        raise ValueError(
                            f"Duplicate primary key value: "
                            f"{new_primary_key}"
                        )

            # Check UNIQUE constraints before changing the row.
            for column_name, new_value in updates.items():
                for index, column in enumerate(self.columns):
                    if column.name == column_name:

                        if not column.validate(new_value):
                            raise TypeError(
                                f"Column '{column.name}' expects "
                                f"{column.data_type}"
                            )

                        if column.unique and new_value is not None:
                            for existing_row in self.rows:
                                if (
                                    existing_row is not row
                                    and existing_row[index] == new_value
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

            # All validation passed, so apply the updates.
            for column_name, new_value in updates.items():
                for index, column in enumerate(self.columns):
                    if column.name == column_name:
                        row[index] = new_value
                        break

            affected_rows += 1

        return affected_rows

    def delete(self, condition=None):
        """
        Delete rows that satisfy the given condition.

        If no condition is provided, all rows are deleted.
        """
        original_count = len(self.rows)

        if condition is None:
            self.rows.clear()
        else:
            self.rows = [
                row for row in self.rows
                if not condition.evaluate(row, self.columns)
            ]

        return original_count - len(self.rows)


