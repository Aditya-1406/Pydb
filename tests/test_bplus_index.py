from pydb.bplus_index import BPlusTreeIndex


def test_bplus_index_insert_and_lookup():
    """
    Verify that a Record ID can be indexed and found
    through an exact-value lookup.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)

    assert index.lookup(22) == {1}


def test_bplus_index_supports_duplicate_values():
    """
    Multiple records may have the same indexed value.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)
    index.insert(4, 22)
    index.insert(8, 22)

    assert index.lookup(22) == {
        1,
        4,
        8
    }


def test_bplus_index_missing_value():
    """
    Missing values should return an empty Record ID set.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)

    assert index.lookup(99) == set()


def test_bplus_index_delete_record():
    """
    Verify that one Record ID can be removed from
    a value bucket without affecting other records.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)
    index.insert(4, 22)
    index.insert(8, 22)

    index.delete(4, 22)

    assert index.lookup(22) == {
        1,
        8
    }


def test_bplus_index_delete_last_record():
    """
    Verify that deleting the final Record ID for a value
    makes that value return no matching records.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)

    index.delete(1, 22)

    assert index.lookup(22) == set()


def test_bplus_index_update():
    """
    Verify that updating an indexed value moves the
    Record ID to the new value.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 22)

    index.update(
        1,
        22,
        25
    )

    assert index.lookup(22) == set()
    assert index.lookup(25) == {1}


def test_bplus_index_range_lookup():
    """
    Verify that range lookup collects Record IDs from
    multiple ordered B+Tree keys.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 20)
    index.insert(2, 21)
    index.insert(3, 25)
    index.insert(4, 30)
    index.insert(5, 35)

    assert index.range_lookup(
        21,
        30
    ) == {
        2,
        3,
        4
    }


def test_bplus_index_range_lookup_with_duplicates():
    """
    Verify range lookup when multiple records share
    the same indexed value.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 20)
    index.insert(2, 20)
    index.insert(3, 25)
    index.insert(4, 25)
    index.insert(5, 30)

    assert index.range_lookup(
        20,
        25
    ) == {
        1,
        2,
        3,
        4
    }


def test_bplus_index_items_are_sorted():
    """
    Verify that indexed values are returned in sorted
    order because the underlying structure is a B+Tree.
    """
    index = BPlusTreeIndex("age")

    index.insert(1, 30)
    index.insert(2, 10)
    index.insert(3, 20)

    assert index.items() == [
        (10, {2}),
        (20, {3}),
        (30, {1}),
    ]