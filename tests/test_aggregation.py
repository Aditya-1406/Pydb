import pytest

from pydb.database import Database
from pydb.parser import Parser
from pydb.executor import QueryExecutor


@pytest.fixture
def database():
    """
    Create a fresh database containing test data for
    aggregation queries.
    """
    database = Database()
    executor = QueryExecutor(database)

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    executor.insert(
        "users",
        [1, "Aditya", 22]
    )

    executor.insert(
        "users",
        [2, "Aditya Sharma", 25]
    )

    executor.insert(
        "users",
        [3, "Rahul", 20]
    )

    executor.insert(
        "users",
        [4, "Karan", 30]
    )

    executor.insert(
        "users",
        [5, "Rohit", 35]
    )

    executor.insert(
        "users",
        [6, "Aditi", 28]
    )

    return database


@pytest.fixture
def executor(database):
    """
    Create a QueryExecutor for the aggregation test database.
    """
    return QueryExecutor(database)


@pytest.fixture
def parser():
    """
    Create a fresh SQL parser.
    """
    return Parser()


def execute_sql(executor, parser, sql):
    """
    Parse and execute one SQL statement.
    """
    query = parser.parse(sql)
    return executor.execute(query)


# ---------------------------------------------------------
# Parser tests
# ---------------------------------------------------------


def test_parser_count_star(parser):
    """
    COUNT(*) should be parsed as an aggregate expression.
    """
    query = parser.parse(
        "SELECT COUNT(*) FROM users;"
    )

    assert len(query.columns) == 1
    assert query.columns[0].function_name == "COUNT"
    assert query.columns[0].column_name is None
    assert query.columns[0].is_count_all


def test_parser_count_column(parser):
    """
    COUNT(column) should preserve the target column.
    """
    query = parser.parse(
        "SELECT COUNT(age) FROM users;"
    )

    assert query.columns[0].function_name == "COUNT"
    assert query.columns[0].column_name == "age"


@pytest.mark.parametrize(
    "function_name",
    ["SUM", "AVG", "MIN", "MAX"]
)
def test_parser_aggregate_functions(parser, function_name):
    """
    All supported aggregate functions should be parsed.
    """
    query = parser.parse(
        f"SELECT {function_name}(age) FROM users;"
    )

    assert query.columns[0].function_name == function_name
    assert query.columns[0].column_name == "age"


@pytest.mark.parametrize(
    "function_name",
    ["count", "Count", "COUNT", "sum", "AVG", "min", "MaX"]
)
def test_parser_aggregate_functions_are_case_insensitive(
    parser,
    function_name
):
    """
    Aggregate function names should be case-insensitive.
    """
    query = parser.parse(
        f"SELECT {function_name}(age) FROM users;"
    )

    assert query.columns[0].function_name == (
        function_name.upper()
    )


def test_parser_multiple_aggregates(parser):
    """
    Multiple aggregate expressions should be accepted.
    """
    query = parser.parse(
        "SELECT COUNT(*), AVG(age), MAX(age) FROM users;"
    )

    assert len(query.columns) == 3

    assert query.columns[0].function_name == "COUNT"
    assert query.columns[1].function_name == "AVG"
    assert query.columns[2].function_name == "MAX"


def test_parser_rejects_mixed_normal_and_aggregate_columns(parser):
    """
    Normal columns and aggregates are intentionally not mixed
    in the current aggregation scope.
    """
    with pytest.raises(ValueError):
        parser.parse(
            "SELECT name, COUNT(*) FROM users;"
        )


def test_parser_rejects_sum_star(parser):
    """
    SUM(*) is not a valid PyDB aggregate.
    """
    with pytest.raises(ValueError):
        parser.parse(
            "SELECT SUM(*) FROM users;"
        )


def test_parser_rejects_count_without_argument(parser):
    """
    COUNT() must be rejected.
    """
    with pytest.raises(ValueError):
        parser.parse(
            "SELECT COUNT() FROM users;"
        )


def test_parser_rejects_missing_closing_parenthesis(parser):
    """
    Aggregate expressions require a closing parenthesis.
    """
    with pytest.raises(ValueError):
        parser.parse(
            "SELECT AVG(age FROM users;"
        )


def test_parser_rejects_unsupported_aggregate(parser):
    """
    Unsupported function names should be rejected.
    """
    with pytest.raises(ValueError):
        parser.parse(
            "SELECT MEDIAN(age) FROM users;"
        )


# ---------------------------------------------------------
# COUNT tests
# ---------------------------------------------------------


def test_count_star(executor, parser):
    """
    COUNT(*) should count every row.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users;"
    )

    assert result == [[6]]


def test_count_column(executor, parser):
    """
    COUNT(column) should count non-NULL values.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(age) FROM users;"
    )

    assert result == [[6]]


# ---------------------------------------------------------
# SUM / AVG tests
# ---------------------------------------------------------


def test_sum(executor, parser):
    """
    SUM should add all non-NULL numeric values.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT SUM(age) FROM users;"
    )

    assert result == [[160]]


def test_avg(executor, parser):
    """
    AVG should calculate the arithmetic mean.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT AVG(age) FROM users;"
    )

    assert result == [[160 / 6]]


# ---------------------------------------------------------
# MIN / MAX tests
# ---------------------------------------------------------


def test_min(executor, parser):
    """
    MIN should return the smallest non-NULL value.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT MIN(age) FROM users;"
    )

    assert result == [[20]]


def test_max(executor, parser):
    """
    MAX should return the largest non-NULL value.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT MAX(age) FROM users;"
    )

    assert result == [[35]]


# ---------------------------------------------------------
# Multiple aggregates
# ---------------------------------------------------------


def test_multiple_aggregates(executor, parser):
    """
    Multiple aggregate functions should be calculated in
    the same SELECT query.
    """
    result = execute_sql(
        executor,
        parser,
        """
        SELECT COUNT(*), SUM(age), AVG(age), MIN(age), MAX(age)
        FROM users;
        """
    )

    assert result == [
        [
            6,
            160,
            160 / 6,
            20,
            35
        ]
    ]


# ---------------------------------------------------------
# WHERE integration
# ---------------------------------------------------------


def test_count_with_where(executor, parser):
    """
    Aggregates should operate on rows filtered by WHERE.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users WHERE age >= 25;"
    )

    assert result == [[4]]


def test_sum_with_where(executor, parser):
    """
    SUM should aggregate only rows matching WHERE.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT SUM(age) FROM users WHERE age >= 25;"
    )

    assert result == [[118]]


def test_avg_with_between(executor, parser):
    """
    Aggregates should work with the existing BETWEEN condition.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT AVG(age) FROM users "
        "WHERE age BETWEEN 20 AND 30;"
    )

    assert result == [[25]]


def test_max_with_in(executor, parser):
    """
    Aggregates should work with the existing IN condition.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT MAX(age) FROM users "
        "WHERE age IN (20, 25, 30);"
    )

    assert result == [[30]]


def test_avg_with_like(executor, parser):
    """
    Aggregates should work with the existing LIKE condition.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT AVG(age) FROM users "
        "WHERE name LIKE 'Adi%';"
    )

    assert result == [[25]]


def test_aggregate_with_and_condition(executor, parser):
    """
    Aggregates should work with compound AND conditions.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users "
        "WHERE age >= 20 AND age <= 25;"
    )

    assert result == [[3]]


def test_aggregate_with_or_condition(executor, parser):
    """
    Aggregates should work with compound OR conditions.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users "
        "WHERE name LIKE 'Adi%' OR age = 20;"
    )

    assert result == [[4]]


# ---------------------------------------------------------
# NULL behavior
# ---------------------------------------------------------


def test_count_column_ignores_null(executor, parser):
    """
    COUNT(column) must ignore NULL values.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(age) FROM users;"
    )

    assert result == [[6]]


def test_count_star_includes_null_rows(executor, parser):
    """
    COUNT(*) must count rows even when their columns contain NULL.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users;"
    )

    assert result == [[7]]


def test_sum_ignores_null(executor, parser):
    """
    SUM must ignore NULL values.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT SUM(age) FROM users;"
    )

    assert result == [[160]]


def test_avg_ignores_null(executor, parser):
    """
    AVG must ignore NULL values.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT AVG(age) FROM users;"
    )

    assert result == [[160 / 6]]


def test_min_ignores_null(executor, parser):
    """
    MIN must ignore NULL values.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT MIN(age) FROM users;"
    )

    assert result == [[20]]


def test_max_ignores_null(executor, parser):
    """
    MAX must ignore NULL values.
    """
    executor.insert(
        "users",
        [7, "NULL Age", None]
    )

    result = execute_sql(
        executor,
        parser,
        "SELECT MAX(age) FROM users;"
    )

    assert result == [[35]]


# ---------------------------------------------------------
# Empty result behavior
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "SELECT COUNT(*) FROM users WHERE age > 100;",
            [[0]]
        ),
        (
            "SELECT COUNT(age) FROM users WHERE age > 100;",
            [[0]]
        ),
        (
            "SELECT SUM(age) FROM users WHERE age > 100;",
            [[None]]
        ),
        (
            "SELECT AVG(age) FROM users WHERE age > 100;",
            [[None]]
        ),
        (
            "SELECT MIN(age) FROM users WHERE age > 100;",
            [[None]]
        ),
        (
            "SELECT MAX(age) FROM users WHERE age > 100;",
            [[None]]
        )
    ]
)
def test_aggregate_empty_result(
    executor,
    parser,
    query,
    expected
):
    """
    Verify SQL-style aggregate behavior when no rows match.
    """
    result = execute_sql(
        executor,
        parser,
        query
    )

    assert result == expected


# ---------------------------------------------------------
# Data-type validation
# ---------------------------------------------------------


def test_sum_rejects_text_column(executor, parser):
    """
    SUM should only operate on numeric columns.
    """
    with pytest.raises(TypeError):
        execute_sql(
            executor,
            parser,
            "SELECT SUM(name) FROM users;"
        )


def test_avg_rejects_text_column(executor, parser):
    """
    AVG should only operate on numeric columns.
    """
    with pytest.raises(TypeError):
        execute_sql(
            executor,
            parser,
            "SELECT AVG(name) FROM users;"
        )


def test_aggregate_rejects_missing_column(executor, parser):
    """
    Aggregating an unknown column should raise a clear error.
    """
    with pytest.raises(ValueError):
        execute_sql(
            executor,
            parser,
            "SELECT MAX(salary) FROM users;"
        )


# ---------------------------------------------------------
# Aggregate restrictions
# ---------------------------------------------------------

# ---------------------------------------------------------
# Aggregate restrictions
# ---------------------------------------------------------


def test_aggregate_rejects_order_by(executor, parser):
    """
    ORDER BY is not meaningful for a plain aggregate query.
    """
    with pytest.raises(ValueError):
        execute_sql(
            executor,
            parser,
            "SELECT COUNT(*) FROM users ORDER BY age;"
        )


def test_aggregate_allows_limit(executor, parser):
    """
    LIMIT is supported for aggregate queries.

    A plain aggregate produces one result row, so LIMIT 1
    still returns that single aggregate result.
    """
    result = execute_sql(
        executor,
        parser,
        "SELECT COUNT(*) FROM users LIMIT 1;"
    )

    assert result == [[6]]