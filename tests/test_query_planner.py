from pydb.table import Table
from pydb.condition import (
    Condition,
    BetweenCondition
)


def create_users_table():
    """
    Create a table for query-planner tests.
    """
    return Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT"),
        ],
        primary_key="id"
    )


def test_no_condition_uses_full_scan():
    """
    A SELECT without WHERE must use a full scan.
    """
    table = create_users_table()

    plan = table.explain_select()

    assert plan["type"] == "FULL_SCAN"


def test_hash_index_is_preferred_for_equality():
    """
    When both hash and B+Tree indexes exist, the hash
    index remains the preferred equality access path.
    """
    table = create_users_table()

    table.create_index("age")
    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "=", 22)
    )

    assert plan["type"] == "HASH_INDEX"


def test_bplus_tree_handles_equality():
    """
    When no hash index exists, B+Tree can handle equality.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "=", 22)
    )

    assert plan["type"] == "BTREE_INDEX"


def test_bplus_tree_handles_greater_than():
    """
    B+Tree is suitable for an ordered > lookup.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", ">", 20)
    )

    assert plan["type"] == "BTREE_RANGE"


def test_bplus_tree_handles_greater_than_or_equal():
    """
    B+Tree is suitable for >=.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", ">=", 20)
    )

    assert plan["type"] == "BTREE_RANGE"


def test_bplus_tree_handles_less_than():
    """
    B+Tree is suitable for <.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "<", 30)
    )

    assert plan["type"] == "BTREE_RANGE"


def test_bplus_tree_handles_less_than_or_equal():
    """
    B+Tree is suitable for <=.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "<=", 30)
    )

    assert plan["type"] == "BTREE_RANGE"


def test_bplus_tree_handles_between():
    """
    B+Tree is suitable for BETWEEN.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        BetweenCondition(
            "age",
            20,
            30
        )
    )

    assert plan["type"] == "BTREE_RANGE"


def test_not_equal_uses_full_scan():
    """
    != is not represented as one contiguous B+Tree range.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "!=", 22)
    )

    assert plan["type"] == "FULL_SCAN"


def test_missing_index_uses_full_scan():
    """
    A condition with no applicable index must fall back
    to a full scan.
    """
    table = create_users_table()

    plan = table.explain_select(
        Condition("age", ">", 20)
    )

    assert plan["type"] == "FULL_SCAN"


def test_null_equality_uses_full_scan():
    """
    NULL comparisons are not handled by the index.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    plan = table.explain_select(
        Condition("age", "=", None)
    )

    assert plan["type"] == "FULL_SCAN"