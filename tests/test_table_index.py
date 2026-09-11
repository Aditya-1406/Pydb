from pydb.table import Table


def test_table_starts_with_no_indexes():
    """
    A newly created table should not have any indexes.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    assert table.indexes == {}


def test_create_index_for_existing_column():
    """
    An index can be created for an existing table column.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    assert "age" in table.indexes
    assert table.indexes["age"].column_name == "age"


def test_create_index_builds_entries_from_existing_rows():
    """
    Creating an index after rows already exist should build
    the index using the existing rows and Record IDs.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert(["Aditya", 22])
    table.insert(["Rajat", 22])
    table.insert(["Aman", 25])

    table.create_index("age")

    assert table.indexes["age"].lookup(22) == {1, 2}
    assert table.indexes["age"].lookup(25) == {3}


def test_insert_updates_index():
    """
    Inserting a new row should automatically update
    an existing index.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])

    assert table.indexes["age"].lookup(22) == {1}


def test_multiple_inserts_update_index():
    """
    Multiple inserted rows should all appear under the
    correct indexed values.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])
    table.insert(["Rajat", 22])
    table.insert(["Aman", 25])

    assert table.indexes["age"].lookup(22) == {1, 2}
    assert table.indexes["age"].lookup(25) == {3}


def test_update_indexed_column():
    """
    Updating an indexed column should move the Record ID
    from the old value to the new value.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])

    affected = table.update(
        {"age": 25}
    )

    assert affected == 1
    assert table.indexes["age"].lookup(22) == set()
    assert table.indexes["age"].lookup(25) == {1}


def test_update_non_indexed_column_does_not_affect_index():
    """
    Updating a different column should leave the existing
    index unchanged.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])

    table.update(
        {"name": "Aditi"}
    )

    assert table.indexes["age"].lookup(22) == {1}


def test_delete_updates_index():
    """
    Deleting a row should remove its Record ID from
    the relevant index.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])
    table.insert(["Rajat", 25])

    deleted = table.delete()

    assert deleted == 2

    assert table.indexes["age"].lookup(22) == set()
    assert table.indexes["age"].lookup(25) == set()


def test_delete_with_condition_updates_index():
    """
    Conditional deletion should remove only the deleted
    rows from the index.
    """
    from pydb.condition import Condition

    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])
    table.insert(["Rajat", 25])
    table.insert(["Aman", 25])

    condition = Condition("age", "=", 25)

    deleted = table.delete(condition)

    assert deleted == 2

    assert table.indexes["age"].lookup(22) == {1}
    assert table.indexes["age"].lookup(25) == set()


def test_multiple_indexes_stay_in_sync():
    """
    Multiple indexes should independently track the same
    table rows.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("name")
    table.create_index("age")

    table.insert(["Aditya", 22])

    assert table.indexes["name"].lookup("Aditya") == {1}
    assert table.indexes["age"].lookup(22) == {1}


def test_update_multiple_indexed_columns():
    """
    Updating multiple indexed columns should update every
    affected index.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("name")
    table.create_index("age")

    table.insert(["Aditya", 22])

    table.update(
        {
            "name": "Rajat",
            "age": 25
        }
    )

    assert table.indexes["name"].lookup("Aditya") == set()
    assert table.indexes["name"].lookup("Rajat") == {1}

    assert table.indexes["age"].lookup(22) == set()
    assert table.indexes["age"].lookup(25) == {1}


def test_index_supports_null_values():
    """
    An index should correctly track NULL values.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", None])
    table.insert(["Rajat", None])
    table.insert(["Aman", 22])

    assert table.indexes["age"].lookup(None) == {1, 2}
    assert table.indexes["age"].lookup(22) == {3}


def test_create_index_on_missing_column_fails():
    """
    An index cannot be created for a column that does not exist.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    try:
        table.create_index("salary")
        assert False
    except ValueError as error:
        assert "salary" in str(error)


def test_duplicate_index_creation_is_rejected():
    """
    Creating the same index twice should be rejected rather
    than silently replacing the existing index.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    try:
        table.create_index("age")
        assert False
    except ValueError:
        pass


def test_drop_index():
    """
    An existing index can be removed from the table.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    assert table.has_index("age") is True

    table.drop_index("age")

    assert table.has_index("age") is False
    assert "age" not in table.indexes


def test_drop_missing_index_is_safe():
    """
    Dropping an index that does not exist should be safe.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.drop_index("age")

    assert table.indexes == {}


def test_record_ids_remain_stable_with_index():
    """
    Index integration must not change the existing Record ID
    behavior.
    """
    table = Table(
        "users",
        [
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.create_index("age")

    table.insert(["Aditya", 22])
    table.insert(["Rajat", 24])

    table.delete()

    table.insert(["Aman", 30])

    assert table.record_ids == [3]
    assert table.indexes["age"].lookup(30) == {3}