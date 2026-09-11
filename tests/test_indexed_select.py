from pydb.table import Table
from pydb.condition import Condition


def create_users_table():
    """
    Create a reusable table containing duplicate indexed values.
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
    table.insert([2, "Rajat", 24])
    table.insert([3, "Aman", 22])
    table.insert([4, "Simran", 30])

    return table


def test_select_uses_index_for_equality_condition():
    """
    SELECT with an equality condition should use the index
    when one exists.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        22
    )

    result = table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Aman", 22]
    ]


def test_select_without_index_still_uses_normal_scan():
    """
    Equality SELECT must continue working when no index exists.
    """
    table = create_users_table()

    condition = Condition(
        "age",
        "=",
        22
    )

    result = table.select(
        condition=condition
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Aman", 22]
    ]


def test_indexed_lookup_for_missing_value_returns_no_rows():
    """
    An indexed equality lookup for a value that does not exist
    should return an empty result.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        99
    )

    result = table.select(
        condition=condition
    )

    assert result == []


def test_indexed_lookup_preserves_table_order():
    """
    Index entries are sets, so SELECT must reconstruct results
    using the table's original row order.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        22
    )

    result = table.select(
        condition=condition
    )

    assert [row[0] for row in result] == [1, 3]


def test_indexed_select_supports_projection():
    """
    Index-assisted filtering must still work with SELECT
    column projection.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        22
    )

    result = table.select(
        columns=["name"],
        condition=condition
    )

    assert result == [
        ["Aditya"],
        ["Aman"]
    ]


def test_indexed_select_supports_order_by():
    """
    Index-assisted filtering must remain compatible with
    ORDER BY.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        22
    )

    result = table.select(
        condition=condition,
        order_by="id",
        descending=True
    )

    assert result == [
        [3, "Aman", 22],
        [1, "Aditya", 22]
    ]


def test_non_equality_condition_falls_back_to_scan():
    """
    Operators other than equality should continue using the
    normal condition evaluation path for now.
    """
    table = create_users_table()

    table.create_index("age")

    condition = Condition(
        "age",
        ">",
        22
    )

    result = table.select(
        condition=condition
    )

    assert result == [
        [2, "Rajat", 24],
        [4, "Simran", 30]
    ]


def test_indexed_lookup_handles_null():
    """
    Index lookup should not accidentally change PyDB's NULL
    comparison semantics.

    WHERE age = NULL returns no rows.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    table.insert([1, None])
    table.insert([2, 22])

    table.create_index("age")

    condition = Condition(
        "age",
        "=",
        None
    )

    result = table.select(
        condition=condition
    )

    assert result == []


def test_indexed_select_stays_correct_after_update():
    """
    Index-assisted SELECT must see the updated index state.
    """
    table = create_users_table()

    table.create_index("age")

    table.update(
        {"age": 25},
        Condition("id", "=", 1)
    )

    result = table.select(
        condition=Condition("age", "=", 25)
    )

    assert result == [
        [1, "Aditya", 25]
    ]


def test_indexed_select_stays_correct_after_delete():
    """
    Index-assisted SELECT must see the updated index state
    after deletion.
    """
    table = create_users_table()

    table.create_index("age")

    table.delete(
        Condition("id", "=", 1)
    )

    result = table.select(
        condition=Condition("age", "=", 22)
    )

    assert result == [
        [3, "Aman", 22]
    ]


def test_indexed_select_stays_correct_after_reload():
    """
    Rebuilt indexes must also be usable by SELECT.
    """
    table = create_users_table()

    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    result = restored_table.select(
        condition=Condition("age", "=", 22)
    )

    assert result == [
        [1, "Aditya", 22],
        [3, "Aman", 22]
    ]