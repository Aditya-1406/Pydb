import pytest

from pydb.condition import (
    Condition,
    LikeCondition,
    InCondition,
    AndCondition,
    OrCondition
)
from pydb.parser import Parser
from pydb.table import Table


@pytest.fixture
def users_table():
    """
    Create a sample users table for LIKE and IN tests.
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
    table.insert([2, "Aditya Sharma", 25])
    table.insert([3, "Rahul", 20])
    table.insert([4, "Karan", 30])
    table.insert([5, "Rohit", 35])
    table.insert([6, "Aditi", 28])

    return table


# =========================================
# LIKE TESTS
# =========================================

def test_like_starts_with(users_table):
    """
    '%' should match zero or more characters after
    the supplied prefix.
    """
    condition = LikeCondition(
        "name",
        "Adi%"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [6, "Aditi", 28]
    ]


def test_like_ends_with(users_table):
    """
    '%' at the beginning should match any prefix.
    """
    condition = LikeCondition(
        "name",
        "%hul"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [3, "Rahul", 20]
    ]


def test_like_contains(users_table):
    """
    '%' on both sides should match a substring.
    """
    condition = LikeCondition(
        "name",
        "%dit%"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [6, "Aditi", 28]
    ]


def test_like_exact_match(users_table):
    """
    LIKE without wildcards behaves like an exact match.
    """
    condition = LikeCondition(
        "name",
        "Rahul"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [3, "Rahul", 20]
    ]


def test_like_single_character_wildcard(users_table):
    """
    '_' should match exactly one character.
    """
    condition = LikeCondition(
        "name",
        "R_hul"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [3, "Rahul", 20]
    ]


def test_like_combines_percent_and_underscore(users_table):
    """
    LIKE should support both SQL wildcard types
    in the same pattern.
    """
    condition = LikeCondition(
        "name",
        "A_i%"
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [6, "Aditi", 28]
    ]


def test_like_invalid_column(users_table):
    """
    LIKE should reject a column that does not exist.
    """
    condition = LikeCondition(
        "email",
        "%gmail%"
    )

    with pytest.raises(ValueError):
        users_table.select(
            condition=condition
        )


def test_like_null_value_does_not_match():
    """
    SQL NULL should not match a LIKE pattern.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ]
    )

    table.insert([1, None])

    condition = LikeCondition(
        "name",
        "%"
    )

    result = table.select(
        condition=condition
    )

    assert result == []


def test_parser_parses_like():
    """
    The parser should create a LikeCondition.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE name LIKE 'Adi%'"
    )

    assert isinstance(
        query.condition,
        LikeCondition
    )

    assert query.condition.column_name == "name"
    assert query.condition.pattern == "Adi%"


def test_like_is_case_insensitive_keyword():
    """
    LIKE as a SQL keyword should be case-insensitive.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE name like 'Adi%'"
    )

    assert isinstance(
        query.condition,
        LikeCondition
    )


def test_like_requires_pattern():
    """
    LIKE must have a string pattern.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE name LIKE"
        )


def test_like_rejects_non_string_pattern():
    """
    LIKE patterns must currently be strings.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age LIKE 2"
        )


# =========================================
# IN TESTS
# =========================================

def test_in_matches_multiple_values(users_table):
    """
    IN should match any value contained in the list.
    """
    condition = InCondition(
        "age",
        [20, 22, 25]
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [3, "Rahul", 20]
    ]


def test_in_matches_single_value(users_table):
    """
    IN should also work with a single value.
    """
    condition = InCondition(
        "age",
        [30]
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [4, "Karan", 30]
    ]


def test_in_excludes_values_not_in_list(users_table):
    """
    Values outside the IN list should be excluded.
    """
    condition = InCondition(
        "age",
        [21, 23, 24]
    )

    result = users_table.select(
        condition=condition
    )

    assert result == []


def test_in_with_strings(users_table):
    """
    IN should support string values.
    """
    condition = InCondition(
        "name",
        ["Aditya", "Rahul"]
    )

    result = users_table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Rahul", 20]
    ]


def test_in_invalid_column(users_table):
    """
    IN should reject a column that does not exist.
    """
    condition = InCondition(
        "salary",
        [10000, 20000]
    )

    with pytest.raises(ValueError):
        users_table.select(
            condition=condition
        )


def test_in_rejects_empty_values():
    """
    IN cannot contain an empty value list.
    """
    with pytest.raises(ValueError):
        InCondition(
            "age",
            []
        )


def test_parser_parses_in():
    """
    The parser should create an InCondition.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age IN (20, 22, 25)"
    )

    assert isinstance(
        query.condition,
        InCondition
    )

    assert query.condition.column_name == "age"
    assert query.condition.values == [
        20,
        22,
        25
    ]


def test_parser_parses_string_in():
    """
    IN should support a list of strings.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE name IN ('Aditya', 'Rahul')"
    )

    assert isinstance(
        query.condition,
        InCondition
    )

    assert query.condition.values == [
        "Aditya",
        "Rahul"
    ]


def test_in_is_case_insensitive_keyword():
    """
    IN as a SQL keyword should be case-insensitive.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age in (20, 22)"
    )

    assert isinstance(
        query.condition,
        InCondition
    )


def test_in_requires_parentheses():
    """
    IN must use parentheses around its values.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age IN 20"
        )


def test_in_rejects_empty_list():
    """
    IN () is invalid.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age IN ()"
        )


def test_in_rejects_trailing_comma():
    """
    IN (20, 22,) is invalid.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age IN (20, 22,)"
        )


def test_in_rejects_missing_closing_parenthesis():
    """
    IN must have a closing parenthesis.
    """
    parser = Parser()

    with pytest.raises(ValueError):
        parser.parse(
            "SELECT * FROM users WHERE age IN (20, 22"
        )


# =========================================
# LIKE + IN + LOGICAL CONDITIONS
# =========================================

def test_like_with_and(users_table):
    """
    LIKE should work with a logical AND.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE name LIKE 'Adi%' "
        "AND age > 23"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [2, "Aditya Sharma", 25],
        [6, "Aditi", 28]
    ]


def test_in_with_and(users_table):
    """
    IN should work with a logical AND.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age IN (20, 22, 25) "
        "AND name LIKE 'A%'"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25]
    ]


def test_like_with_or(users_table):
    """
    LIKE should work with a logical OR.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE name LIKE 'Adi%' "
        "OR name LIKE 'Rah%'"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [3, "Rahul", 20],
        [6, "Aditi", 28]
    ]


def test_in_with_or(users_table):
    """
    IN should work with a logical OR.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age IN (20, 22) "
        "OR age IN (30, 35)"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Rahul", 20],
        [4, "Karan", 30],
        [5, "Rohit", 35]
    ]


def test_like_and_in_together(users_table):
    """
    LIKE and IN should work together in the same WHERE clause.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE name LIKE 'A%' "
        "AND age IN (22, 25, 28)"
    )

    result = users_table.select(
        condition=query.condition
    )

    assert result == [
        [1, "Aditya", 22],
        [2, "Aditya Sharma", 25],
        [6, "Aditi", 28]
    ]