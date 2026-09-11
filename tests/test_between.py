import pytest

from pydb.condition import (
    BetweenCondition,
    Condition,
    AndCondition,
    OrCondition
)
from pydb.lexer import Lexer
from pydb.parser import Parser
from pydb.table import Table


@pytest.fixture
def users_table():
    """
    Create a sample users table for BETWEEN tests.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])
    table.insert([3, "Karan", 20])
    table.insert([4, "Arjun", 30])
    table.insert([5, "Rohit", 35])

    return table


def test_between_includes_lower_boundary(users_table):
    """
    The lower boundary of BETWEEN should be included.
    """
    condition = BetweenCondition("age", 20, 30)

    result = users_table.select(condition=condition)

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25],
        [3, "Karan", 20],
        [4, "Arjun", 30]
    ]


def test_between_includes_upper_boundary(users_table):
    """
    The upper boundary of BETWEEN should be included.
    """
    condition = BetweenCondition("age", 25, 30)

    result = users_table.select(condition=condition)

    assert result == [
        [2, "Rahul", 25],
        [4, "Arjun", 30]
    ]


def test_between_excludes_values_outside_range(users_table):
    """
    Values outside the BETWEEN range should be excluded.
    """
    condition = BetweenCondition("age", 21, 29)

    result = users_table.select(condition=condition)

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_between_with_invalid_column(users_table):
    """
    BETWEEN should reject a column that does not exist.
    """
    condition = BetweenCondition("salary", 10000, 50000)

    with pytest.raises(ValueError):
        users_table.select(condition=condition)


def test_parser_parses_between():
    """
    The parser should create a BetweenCondition
    for a BETWEEN expression.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age BETWEEN 18 AND 30"
    )

    assert isinstance(
        query.condition,
        BetweenCondition
    )

    assert query.condition.column_name == "age"
    assert query.condition.lower_value == 18
    assert query.condition.upper_value == 30


def test_between_is_case_insensitive():
    """
    SQL keywords should remain case-insensitive.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age between 18 and 30"
    )

    assert isinstance(
        query.condition,
        BetweenCondition
    )


def test_between_executes_through_parser(users_table):
    """
    A parsed BETWEEN query should work when executed
    against a table.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age BETWEEN 20 AND 30"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25],
        [3, "Karan", 20],
        [4, "Arjun", 30]
    ]


def test_between_with_logical_and(users_table):
    """
    BETWEEN should work correctly with a logical AND.

    The first AND belongs to BETWEEN.
    The second AND is the logical operator.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age BETWEEN 20 AND 30 "
        "AND name = 'Aditya'"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22]
    ]


def test_between_with_logical_or(users_table):
    """
    BETWEEN should work correctly with a logical OR.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age BETWEEN 20 AND 22 "
        "OR age = 35"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Karan", 20],
        [5, "Rohit", 35]
    ]


def test_between_requires_lower_value():
    """
    BETWEEN must have a lower boundary.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age BETWEEN"
        )


def test_between_requires_and():
    """
    BETWEEN must contain the AND keyword between
    its lower and upper boundaries.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age BETWEEN 18 30"
        )


def test_between_requires_upper_value():
    """
    BETWEEN must have an upper boundary.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age BETWEEN 18 AND"
        )


def test_between_rejects_invalid_lower_value():
    """
    BETWEEN should reject an invalid lower value.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age BETWEEN NULL AND 30"
        )


def test_between_rejects_invalid_upper_value():
    """
    BETWEEN should reject an invalid upper value.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age BETWEEN 18 AND NULL"
        )


def test_between_with_reversed_range_returns_no_rows(users_table):
    """
    A reversed range is valid syntax but should not match
    any values.
    """
    condition = BetweenCondition("age", 30, 20)

    result = users_table.select(condition=condition)

    assert result == []


def test_between_can_compare_strings():
    """
    BETWEEN can also work with comparable string values.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    table.insert([1, "Aditya"])
    table.insert([2, "Karan"])
    table.insert([3, "Rahul"])
    table.insert([4, "Zoya"])

    condition = BetweenCondition(
        "name",
        "Karan",
        "Rahul"
    )

    result = table.select(condition=condition)

    assert result == [
        [2, "Karan"],
        [3, "Rahul"]
    ]