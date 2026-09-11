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