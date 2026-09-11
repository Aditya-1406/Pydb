import pytest

from pydb.parser import Parser
from pydb.executor import QueryExecutor
from pydb.database import Database


@pytest.fixture
def setup_database():
    """
    Create a fresh database containing employee data
    suitable for GROUP BY and HAVING tests.
    """
    database = Database()
    executor = QueryExecutor(database)
    parser = Parser()

    executor.execute(
        parser.parse(
            """
            CREATE TABLE employees (
                id INT PRIMARY KEY,
                name TEXT,
                department TEXT,
                age INT,
                salary INT
            );
            """
        )
    )

    rows = [
        (1, "Aditya", "Engineering", 22, 50000),
        (2, "Rahul", "Engineering", 24, 60000),
        (3, "Aditi", "Engineering", 23, 55000),
        (4, "Karan", "HR", 30, 40000),
        (5, "Simran", "HR", 28, 45000),
        (6, "Rohit", "Sales", 26, 30000),
    ]

    for row in rows:
        executor.execute(
            parser.parse(
                "INSERT INTO employees "
                "VALUES "
                f"({row[0]}, '{row[1]}', '{row[2]}', "
                f"{row[3]}, {row[4]});"
            )
        )

    return database, parser, executor


def test_group_by_count(setup_database):
    """
    GROUP BY should produce one result row per department.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2],
        ["Sales", 1]
    ]


def test_group_by_sum(setup_database):
    """
    SUM should calculate independently for every group.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, SUM(salary)
            FROM employees
            GROUP BY department;
            """
        )
    )

    assert result == [
        ["Engineering", 165000],
        ["HR", 85000],
        ["Sales", 30000]
    ]


def test_group_by_avg(setup_database):
    """
    AVG should calculate independently for every group.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, AVG(salary)
            FROM employees
            GROUP BY department;
            """
        )
    )

    assert result == [
        ["Engineering", 55000.0],
        ["HR", 42500.0],
        ["Sales", 30000.0]
    ]


def test_group_by_min_max(setup_database):
    """
    MIN and MAX should operate independently inside
    each group.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, MIN(salary), MAX(salary)
            FROM employees
            GROUP BY department;
            """
        )
    )

    assert result == [
        ["Engineering", 50000, 60000],
        ["HR", 40000, 45000],
        ["Sales", 30000, 30000]
    ]


def test_group_by_where_then_group(setup_database):
    """
    WHERE must execute before GROUP BY.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            WHERE salary >= 50000
            GROUP BY department;
            """
        )
    )

    assert result == [
        ["Engineering", 3]
    ]


def test_having_count(setup_database):
    """
    HAVING should filter groups after aggregation.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            HAVING COUNT(*) > 1;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2]
    ]


def test_having_sum(setup_database):
    """
    HAVING should work with SUM.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, SUM(salary)
            FROM employees
            GROUP BY department
            HAVING SUM(salary) > 100000;
            """
        )
    )

    assert result == [
        ["Engineering", 165000]
    ]


def test_having_avg(setup_database):
    """
    HAVING should work with AVG.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, AVG(salary)
            FROM employees
            GROUP BY department
            HAVING AVG(salary) >= 50000;
            """
        )
    )

    assert result == [
        ["Engineering", 55000.0]
    ]


def test_having_and(setup_database):
    """
    HAVING should support logical AND.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            HAVING COUNT(*) >= 2
            AND COUNT(*) < 4;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2]
    ]


def test_having_or(setup_database):
    """
    HAVING should support logical OR.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            HAVING COUNT(*) = 1
            OR COUNT(*) = 3;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["Sales", 1]
    ]


def test_multiple_group_by_columns(setup_database):
    """
    GROUP BY should support multiple columns.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, age, COUNT(*)
            FROM employees
            GROUP BY department, age;
            """
        )
    )

    assert result == [
        ["Engineering", 22, 1],
        ["Engineering", 24, 1],
        ["Engineering", 23, 1],
        ["HR", 30, 1],
        ["HR", 28, 1],
        ["Sales", 26, 1]
    ]


def test_group_by_order_by(setup_database):
    """
    ORDER BY should operate on the grouped result.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            ORDER BY department DESC;
            """
        )
    )

    assert result == [
        ["Sales", 1],
        ["HR", 2],
        ["Engineering", 3]
    ]


def test_group_by_limit(setup_database):
    """
    LIMIT should be applied after grouping.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            LIMIT 2;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2]
    ]


def test_group_by_order_and_limit(setup_database):
    """
    ORDER BY should execute before LIMIT.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            GROUP BY department
            ORDER BY department DESC
            LIMIT 2;
            """
        )
    )

    assert result == [
        ["Sales", 1],
        ["HR", 2]
    ]


def test_invalid_group_by_column(setup_database):
    """
    GROUP BY should reject unknown columns.
    """
    database, parser, executor = setup_database

    with pytest.raises(ValueError):
        executor.execute(
            parser.parse(
                """
                SELECT department, COUNT(*)
                FROM employees
                GROUP BY unknown_column;
                """
            )
        )


def test_invalid_selected_column_not_in_group_by(setup_database):
    """
    A normal selected column must appear in GROUP BY.
    """
    database, parser, executor = setup_database

    with pytest.raises(ValueError):
        executor.execute(
            parser.parse(
                """
                SELECT department, age, COUNT(*)
                FROM employees
                GROUP BY department;
                """
            )
        )


def test_invalid_having_without_group_or_aggregate(
    setup_database
):
    """
    HAVING cannot be used by an ordinary non-grouped SELECT.
    """
    database, parser, executor = setup_database

    with pytest.raises(ValueError):
        executor.execute(
            parser.parse(
                """
                SELECT department
                FROM employees
                HAVING department = 'HR';
                """
            )
        )


def test_invalid_select_star_with_group_by(
    setup_database
):
    """
    SELECT * is not allowed with GROUP BY.
    """
    database, parser, executor = setup_database

    with pytest.raises(ValueError):
        executor.execute(
            parser.parse(
                """
                SELECT *
                FROM employees
                GROUP BY department;
                """
            )
        )


def test_aggregate_without_group_by_still_works(
    setup_database
):
    """
    Existing aggregate behavior must remain unchanged.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT COUNT(*), AVG(salary), MAX(salary)
            FROM employees;
            """
        )
    )

    assert result == [
        [6, 46666.666666666664, 60000]
    ]


def test_where_having_execution_order(
    setup_database
):
    """
    WHERE must filter rows before aggregation and HAVING
    must filter the resulting groups afterward.
    """
    database, parser, executor = setup_database

    result = executor.execute(
        parser.parse(
            """
            SELECT department, COUNT(*)
            FROM employees
            WHERE salary >= 40000
            GROUP BY department
            HAVING COUNT(*) >= 2;
            """
        )
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2]
    ]