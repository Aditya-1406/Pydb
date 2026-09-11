from pydb.table import Table
from pydb.condition import (
    Condition,
    BetweenCondition
)


def create_users_table():
    """
    Create a small users table for execution-statistics tests.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT"),
        ],
        primary_key="id"
    )

    table.insert(
        [1, "Aditya", 22]
    )

    table.insert(
        [2, "Rahul", 25]
    )

    table.insert(
        [3, "Aman", 30]
    )

    table.insert(
        [4, "Neha", 35]
    )

    table.insert(
        [5, "Riya", 40]
    )

    return table


def test_full_scan_execution_stats():
    """
    Without an index, every row must be evaluated.
    """
    table = create_users_table()

    rows, stats = table.select_with_stats(
        condition=Condition(
            "age",
            ">",
            20
        )
    )

    assert len(rows) == 5

    assert stats["access_path"] == "FULL_SCAN"

    assert stats["table_rows"] == 5

    assert stats["table_rows_visited"] == 5

    assert stats["index_candidates"] is None

    assert stats["condition_evaluations"] == 5

    assert stats["rows_matched"] == 5


def test_hash_index_execution_stats():
    """
    A hash index should reduce the number of condition
    evaluations for equality lookup.
    """
    table = create_users_table()

    table.create_index("age")

    rows, stats = table.select_with_stats(
        condition=Condition(
            "age",
            "=",
            30
        )
    )

    assert rows == [
        [3, "Aman", 30]
    ]

    assert stats["access_path"] == "HASH_INDEX"

    assert stats["table_rows"] == 5

    # Current implementation still walks the table list.
    assert stats["table_rows_visited"] == 5

    assert stats["index_candidates"] == 1

    assert stats["condition_evaluations"] == 1

    assert stats["rows_matched"] == 1


def test_bplus_tree_equality_execution_stats():
    """
    A B+Tree equality lookup should produce a small
    candidate set.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    rows, stats = table.select_with_stats(
        condition=Condition(
            "age",
            "=",
            30
        )
    )

    assert rows == [
        [3, "Aman", 30]
    ]

    assert stats["access_path"] == "BTREE_INDEX"

    assert stats["table_rows"] == 5

    assert stats["table_rows_visited"] == 5

    assert stats["index_candidates"] == 1

    assert stats["condition_evaluations"] == 1

    assert stats["rows_matched"] == 1


def test_bplus_tree_range_execution_stats():
    """
    A B+Tree range lookup should only evaluate conditions
    for its candidate rows.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    rows, stats = table.select_with_stats(
        condition=Condition(
            "age",
            ">",
            30
        )
    )

    assert rows == [
        [4, "Neha", 35],
        [5, "Riya", 40]
    ]

    assert stats["access_path"] == "BTREE_RANGE"

    assert stats["table_rows"] == 5

    assert stats["table_rows_visited"] == 5

    # B+Tree returns 35 and 40 as candidates.
    assert stats["index_candidates"] == 3

    assert stats["condition_evaluations"] == 3

    assert stats["rows_matched"] == 2


def test_bplus_tree_between_execution_stats():
    """
    BETWEEN should use the B+Tree range access path.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    rows, stats = table.select_with_stats(
        condition=BetweenCondition(
            "age",
            25,
            35
        )
    )

    assert rows == [
        [2, "Rahul", 25],
        [3, "Aman", 30],
        [4, "Neha", 35]
    ]

    assert stats["access_path"] == "BTREE_RANGE"

    assert stats["index_candidates"] == 3

    assert stats["condition_evaluations"] == 3

    assert stats["rows_matched"] == 3


def test_stats_do_not_change_normal_select_results():
    """
    Adding statistics must not change normal SELECT behavior.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    condition = Condition(
        "age",
        ">=",
        30
    )

    normal_result = table.select(
        condition=condition
    )

    stats_result, stats = table.select_with_stats(
        condition=condition
    )

    assert stats_result == normal_result

    assert stats["access_path"] == "BTREE_RANGE"


def test_null_condition_still_uses_full_scan():
    """
    NULL comparisons remain outside index access paths.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    rows, stats = table.select_with_stats(
        condition=Condition(
            "age",
            "=",
            None
        )
    )

    assert rows == []

    assert stats["access_path"] == "FULL_SCAN"

    assert stats["index_candidates"] is None

    assert stats["condition_evaluations"] == 5

    assert stats["rows_matched"] == 0