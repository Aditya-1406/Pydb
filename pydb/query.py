class AggregateExpression:
    """
    Represents a SQL aggregate function.

    Supported functions:

        COUNT(*)
        COUNT(column)
        SUM(column)
        AVG(column)
        MIN(column)
        MAX(column)

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

    HAVING is evaluated after rows have been grouped.
    """

    def __init__(self, expression, operator, value):
        """
        Store the expression, comparison operator, and value.
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
    """

    DEFAULT = object()

    def __init__(self, table_name, row, column_names=None):
        """
        Store the target table, optional column list, and row.
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
        having=None,
        aliases=None
    ):
        """
        Store all information required to perform a SELECT.
        """
        self.table_name = table_name
        self.columns = columns
        self.condition = condition
        self.order_by = order_by
        self.descending = descending
        self.limit = limit
        self.group_by = group_by
        self.having = having

        self.aliases = (
            aliases
            if aliases is not None
            else []
        )


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


class CreateIndexQuery:
    """
    Represents a CREATE INDEX operation.

    Supported forms:

        CREATE INDEX age_idx ON users(age);

        CREATE INDEX age_idx ON users(age) USING HASH;

        CREATE INDEX age_idx ON users(age) USING BTREE;
    """

    def __init__(
        self,
        index_name,
        table_name,
        column_name,
        index_type="HASH"
    ):
        """
        Store index name, target table, indexed column,
        and index type.
        """
        index_type = index_type.upper()

        if index_type not in (
            "HASH",
            "BTREE"
        ):
            raise ValueError(
                f"Unsupported index type: {index_type}"
            )

        self.index_name = index_name
        self.table_name = table_name
        self.column_name = column_name
        self.index_type = index_type

    def __repr__(self):
        """
        Return a readable representation of the CREATE INDEX query.
        """
        return (
            f"CreateIndexQuery("
            f"{self.index_name!r}, "
            f"{self.table_name!r}, "
            f"{self.column_name!r}, "
            f"{self.index_type!r}"
            f")"
        )


class DropIndexQuery:
    """
    Represents a DROP INDEX operation.
    """

    def __init__(self, index_name):
        """
        Store the name of the index to remove.
        """
        self.index_name = index_name

    def __repr__(self):
        """
        Return a readable representation of the DROP INDEX query.
        """
        return (
            f"DropIndexQuery("
            f"{self.index_name!r}"
            f")"
        )


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


class BeginQuery:
    """
    Represents a BEGIN transaction statement.
    """

    def __init__(self):
        """
        Create a BEGIN query object.
        """
        pass


class CommitQuery:
    """
    Represents a COMMIT transaction statement.
    """

    def __init__(self):
        """
        Create a COMMIT query object.
        """
        pass


class RollbackQuery:
    """
    Represents a ROLLBACK transaction statement.
    """

    def __init__(self):
        """
        Create a ROLLBACK query object.
        """
        pass