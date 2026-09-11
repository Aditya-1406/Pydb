from pydb.index import Index


def test_index_stores_column_name():
    """
    The index should remember which column it belongs to.
    """
    index = Index("age")

    assert index.column_name == "age"


def test_insert_and_lookup_single_value():
    """
    A Record ID should be retrievable using its indexed value.
    """
    index = Index("age")

    index.insert(1, 22)

    assert index.lookup(22) == {1}


def test_multiple_record_ids_for_same_value():
    """
    Multiple rows may contain the same value.
    """
    index = Index("age")

    index.insert(1, 22)
    index.insert(2, 22)
    index.insert(3, 24)

    assert index.lookup(22) == {1, 2}
    assert index.lookup(24) == {3}


def test_lookup_missing_value_returns_empty_set():
    """
    Looking up a value that does not exist should return
    an empty set.
    """
    index = Index("age")

    index.insert(1, 22)

    assert index.lookup(99) == set()


def test_duplicate_record_id_is_not_stored_twice():
    """
    A set should prevent the same Record ID from appearing
    multiple times under one value.
    """
    index = Index("age")

    index.insert(1, 22)
    index.insert(1, 22)

    assert index.lookup(22) == {1}


def test_delete_record_id_from_index():
    """
    Deleting an indexed entry should remove only that
    Record ID from the corresponding value.
    """
    index = Index("age")

    index.insert(1, 22)
    index.insert(2, 22)
    index.insert(3, 24)

    index.delete(1, 22)

    assert index.lookup(22) == {2}
    assert index.lookup(24) == {3}


def test_delete_last_record_id_removes_value_entry():
    """
    When the last Record ID for a value is deleted, the
    value should no longer remain in the index.
    """
    index = Index("age")

    index.insert(1, 22)

    index.delete(1, 22)

    assert index.lookup(22) == set()
    assert 22 not in index.entries


def test_delete_missing_entry_does_not_crash():
    """
    Deleting a missing Record ID or value should be safe.
    """
    index = Index("age")

    index.insert(1, 22)

    index.delete(99, 22)
    index.delete(1, 99)

    assert index.lookup(22) == {1}


def test_update_moves_record_id_to_new_value():
    """
    Updating an indexed value should remove the Record ID
    from the old value and add it to the new value.
    """
    index = Index("age")

    index.insert(1, 22)

    index.update(1, 22, 25)

    assert index.lookup(22) == set()
    assert index.lookup(25) == {1}


def test_update_preserves_other_record_ids():
    """
    Updating one Record ID must not affect other entries.
    """
    index = Index("age")

    index.insert(1, 22)
    index.insert(2, 22)
    index.insert(3, 24)

    index.update(1, 22, 25)

    assert index.lookup(22) == {2}
    assert index.lookup(24) == {3}
    assert index.lookup(25) == {1}


def test_index_supports_null_values():
    """
    NULL can be an indexed value.
    """
    index = Index("age")

    index.insert(1, None)
    index.insert(2, None)
    index.insert(3, 22)

    assert index.lookup(None) == {1, 2}
    assert index.lookup(22) == {3}


def test_index_supports_different_data_types():
    """
    The standalone index should store values without imposing
    SQL type validation. Type validation belongs to Column/Table.
    """
    index = Index("value")

    index.insert(1, "Aditya")
    index.insert(2, 22)
    index.insert(3, 3.14)
    index.insert(4, True)

    assert index.lookup("Aditya") == {1}
    assert index.lookup(22) == {2}
    assert index.lookup(3.14) == {3}
    assert index.lookup(True) == {4}


def test_index_can_be_empty():
    """
    A newly created index should contain no entries.
    """
    index = Index("id")

    assert index.entries == {}