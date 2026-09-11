from pydb.table import Table
from pydb.condition import Condition,BetweenCondition



def create_users_table():
    """
    Create a simple table used by the B+Tree integration tests.
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


def test_create_bplus_tree_index():
    """
    A B+Tree index can be created for an existing column.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    assert table.has_bplus_tree_index("age")


def test_bplus_tree_index_indexes_existing_rows():
    """
    Creating a B+Tree index after rows already exist should
    index those existing rows.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 25])
    table.insert([3, "Aaryan", 22])

    table.create_bplus_tree_index("age")

    assert table.bplus_indexes["age"].lookup(22) == {1, 3}
    assert table.bplus_indexes["age"].lookup(25) == {2}


def test_insert_updates_bplus_tree_index():
    """
    A newly inserted row must immediately appear in the
    B+Tree index.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", 22])

    assert table.bplus_indexes["age"].lookup(22) == {1}


def test_duplicate_values_are_stored_in_same_bucket():
    """
    Multiple Record IDs can share the same indexed value.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 22])
    table.insert([3, "Aaryan", 25])

    assert table.bplus_indexes["age"].lookup(22) == {1, 2}
    assert table.bplus_indexes["age"].lookup(25) == {3}


def test_update_synchronizes_bplus_tree_index():
    """
    Updating an indexed value must remove the Record ID
    from the old bucket and add it to the new bucket.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 25])

    table.update(
    {"age": 30},
        Condition("id", "=", 1)
    )

    assert table.bplus_indexes["age"].lookup(22) == set()
    assert table.bplus_indexes["age"].lookup(30) == {1}
    assert table.bplus_indexes["age"].lookup(25) == {2}


def test_delete_synchronizes_bplus_tree_index():
    """
    Deleting a row must remove its Record ID from the
    B+Tree index.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 25])

    table.delete()

    assert table.bplus_indexes["age"].lookup(22) == set()
    assert table.bplus_indexes["age"].lookup(25) == set()


def test_bplus_tree_range_lookup_returns_record_ids():
    """
    B+Tree indexes can perform ordered range lookups.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])
    table.insert([5, "E", 30])

    result = table.bplus_tree_range_lookup(
        "age",
        20,
        25
    )

    assert result == {2, 3, 4}


def test_bplus_tree_range_lookup_with_duplicate_values():
    """
    Range lookup must return every Record ID belonging
    to duplicate indexed values.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "A", 20])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])
    table.insert([5, "E", 25])

    result = table.bplus_tree_range_lookup(
        "age",
        20,
        25
    )

    assert result == {1, 2, 3, 4, 5}


def test_bplus_tree_index_ignores_null():
    """
    NULL values must not be inserted into the ordered B+Tree.
    """
    table = create_users_table()

    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", None])
    table.insert([2, "Rajat", 22])

    assert table.bplus_indexes["age"].lookup(22) == {2}

    assert table.bplus_indexes["age"].lookup(
        None
    ) == set()


def test_bplus_tree_index_survives_persistence():
    """
    B+Tree index definitions must survive database
    serialization and reconstruction.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 25])

    table.create_bplus_tree_index("age")

    data = table.to_dict()

    restored = Table.from_dict(data)

    assert restored.has_bplus_tree_index("age")

    assert (
        restored.bplus_indexes["age"].lookup(22)
        == {1}
    )

    assert (
        restored.bplus_indexes["age"].lookup(25)
        == {2}
    )


def test_hash_and_bplus_indexes_can_coexist():
    """
    The existing hash index and the new B+Tree index
    can exist simultaneously on the same column.
    """
    table = create_users_table()

    table.create_index("age")
    table.create_bplus_tree_index("age")

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 25])

    assert table.indexes["age"].lookup(22) == {1}

    assert (
        table.bplus_indexes["age"].lookup(22)
        == {1}
    )

def test_select_uses_bplus_tree_for_equality():
    """
    B+Tree indexes can provide equality candidates when
    no hash index exists.
    """
    table = create_users_table()

    table.insert([1, "A", 20])
    table.insert([2, "B", 22])
    table.insert([3, "C", 22])
    table.insert([4, "D", 30])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "=",
            22
        )
    )

    assert result == [
        [2, "B", 22],
        [3, "C", 22]
    ]


def test_select_uses_bplus_tree_for_greater_than():
    """
    B+Tree range candidates are filtered by the original
    condition so > remains exclusive.
    """
    table = create_users_table()

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])
    table.insert([5, "E", 30])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            ">",
            20
        )
    )

    assert result == [
        [3, "C", 22],
        [4, "D", 25],
        [5, "E", 30]
    ]


def test_select_uses_bplus_tree_for_greater_than_or_equal():
    """
    >= should include the boundary value.
    """
    table = create_users_table()

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            ">=",
            20
        )
    )

    assert result == [
        [2, "B", 20],
        [3, "C", 22]
    ]


def test_select_uses_bplus_tree_for_less_than():
    """
    < should exclude the upper boundary.
    """
    table = create_users_table()

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "<",
            22
        )
    )

    assert result == [
        [1, "A", 18],
        [2, "B", 20]
    ]


def test_select_uses_bplus_tree_for_less_than_or_equal():
    """
    <= should include the upper boundary.
    """
    table = create_users_table()

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "<=",
            22
        )
    )

    assert result == [
        [1, "A", 18],
        [2, "B", 20],
        [3, "C", 22]
    ]


def test_select_uses_bplus_tree_for_between():
    """
    BETWEEN should use the B+Tree ordered range.
    """
    table = create_users_table()

    table.insert([1, "A", 18])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])
    table.insert([5, "E", 30])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=BetweenCondition(
            "age",
            20,
            25
        )
    )

    assert result == [
        [2, "B", 20],
        [3, "C", 22],
        [4, "D", 25]
    ]


def test_select_bplus_tree_preserves_table_order():
    """
    Using an index must not change the order of returned rows
    when ORDER BY is not requested.
    """
    table = create_users_table()

    table.insert([1, "A", 22])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "=",
            22
        )
    )

    assert result == [
        [1, "A", 22],
        [3, "C", 22]
    ]


def test_select_bplus_tree_with_null_values():
    """
    NULL rows should not break B+Tree range access.
    """
    table = create_users_table()

    table.insert([1, "A", None])
    table.insert([2, "B", 20])
    table.insert([3, "C", 22])
    table.insert([4, "D", 25])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            ">",
            20
        )
    )

    assert result == [
        [3, "C", 22],
        [4, "D", 25]
    ]


def test_not_equal_falls_back_from_bplus_tree():
    """
    != is not treated as one contiguous B+Tree range.
    """
    table = create_users_table()

    table.insert([1, "A", 20])
    table.insert([2, "B", 22])
    table.insert([3, "C", 25])

    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "!=",
            22
        )
    )

    assert result == [
        [1, "A", 20],
        [3, "C", 25]
    ]


def test_hash_index_is_preferred_for_equality():
    """
    When both index types exist, the existing hash-index
    equality path remains the preferred access path.

    This test verifies result correctness; the actual
    planner-selection behavior is kept in Table.
    """
    table = create_users_table()

    table.insert([1, "A", 20])
    table.insert([2, "B", 22])
    table.insert([3, "C", 22])

    table.create_index("age")
    table.create_bplus_tree_index("age")

    result = table.select(
        condition=Condition(
            "age",
            "=",
            22
        )
    )

    assert result == [
        [2, "B", 22],
        [3, "C", 22]
    ]