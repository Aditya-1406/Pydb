from pydb.table import Table
from pydb.condition import Condition

def test_index_definition_is_persisted():
    """
    Index definitions should survive table serialization.
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

    table.create_index("age")

    data = table.to_dict()

    assert data["indexes"] == ["age"]


def test_index_is_rebuilt_after_reload():
    """
    Reloading a table should reconstruct its indexes
    from the persisted index definitions and table data.
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

    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    assert restored_table.has_index("age")

    assert restored_table.indexes["age"].lookup(22) == {1, 3}
    assert restored_table.indexes["age"].lookup(24) == {2}


def test_record_ids_are_preserved_when_indexes_are_rebuilt():
    """
    Index rebuilding must use the original Record IDs rather
    than assigning new IDs.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    table.insert([1, 22])
    table.insert([2, 24])
    table.insert([3, 22])

    table.delete()

    table.insert([4, 30])
    table.insert([5, 35])

    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    assert restored_table.record_ids == [4, 5]

    assert restored_table.indexes["age"].lookup(30) == {4}
    assert restored_table.indexes["age"].lookup(35) == {5}


def test_multiple_indexes_are_rebuilt():
    """
    All persisted index definitions should be reconstructed.
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

    table.create_index("name")
    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    assert restored_table.has_index("name")
    assert restored_table.has_index("age")

    assert restored_table.indexes["name"].lookup("Aditya") == {1}
    assert restored_table.indexes["name"].lookup("Rajat") == {2}

    assert restored_table.indexes["age"].lookup(22) == {1}
    assert restored_table.indexes["age"].lookup(24) == {2}


def test_old_table_without_index_metadata_still_loads():
    """
    Older PyDB database files did not contain index metadata.

    Such files should continue loading successfully and simply
    contain no indexes.
    """
    data = {
        "name": "users",
        "columns": [
            {
                "name": "id",
                "data_type": "INT",
                "nullable": True,
                "unique": False,
                "default": None,
                "has_default": False
            },
            {
                "name": "age",
                "data_type": "INT",
                "nullable": True,
                "unique": False,
                "default": None,
                "has_default": False
            }
        ],
        "primary_key": None,
        "rows": [
            [1, 22],
            [2, 24]
        ],
        "record_ids": [1, 2],
        "next_record_id": 3
    }

    restored_table = Table.from_dict(data)

    assert restored_table.rows == [
        [1, 22],
        [2, 24]
    ]

    assert restored_table.record_ids == [1, 2]
    assert restored_table.next_record_id == 3
    assert restored_table.indexes == {}


def test_rebuilt_index_stays_synchronized_after_insert():
    """
    An index rebuilt during loading must continue behaving like
    a normally created index.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    table.insert([1, 22])
    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    restored_table.insert([2, 24])

    assert restored_table.indexes["age"].lookup(22) == {1}
    assert restored_table.indexes["age"].lookup(24) == {2}


def test_rebuilt_index_stays_synchronized_after_update():
    """
    A rebuilt index must remain synchronized after UPDATE.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    table.insert([1, 22])
    table.insert([2, 24])

    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    restored_table.update(
        {"age": 25},
        condition=Condition("id", "=", 1)
    )

    assert restored_table.indexes["age"].lookup(22) == set()
    assert restored_table.indexes["age"].lookup(25) == {1}
    assert restored_table.indexes["age"].lookup(24) == {2}

def test_rebuilt_index_stays_synchronized_after_delete():
    """
    A rebuilt index must remain synchronized after DELETE.
    """
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ]
    )

    table.insert([1, 22])
    table.insert([2, 24])

    table.create_index("age")

    data = table.to_dict()

    restored_table = Table.from_dict(data)

    restored_table.delete()

    assert restored_table.indexes["age"].entries == {}