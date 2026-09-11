from pydb.table import Table
from pydb.condition import Condition


def create_users_table():
    """
    Create a simple table used by the Record ID tests.
    """
    return Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )


def test_record_ids_are_generated():
    """
    Every inserted row should receive a unique internal
    Record ID.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 24])

    assert table.record_ids == [1, 2]


def test_record_ids_remain_stable_after_delete():
    """
    Deleting a row must not change the Record IDs of the
    remaining rows.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 24])
    table.insert([3, "Aman", 21])

    condition = Condition("id", "=", 2)

    table.delete(condition)

    assert table.rows == [
        [1, "Aditya", 22],
        [3, "Aman", 21]
    ]

    assert table.record_ids == [1, 3]


def test_new_rows_receive_new_record_ids():
    """
    A newly inserted row must receive a new Record ID rather
    than reusing the ID of a deleted row.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 24])

    condition = Condition("id", "=", 1)

    table.delete(condition)

    table.insert([3, "Aman", 21])

    assert table.rows == [
        [2, "Rajat", 24],
        [3, "Aman", 21]
    ]

    assert table.record_ids == [2, 3]


def test_record_ids_are_not_visible_in_select():
    """
    Internal Record IDs must not appear in normal SELECT
    results.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])

    result = table.select()

    assert result == [
        [1, "Aditya", 22]
    ]


def test_record_ids_are_not_used_as_primary_keys():
    """
    Internal Record IDs are separate from SQL primary keys.
    A table without a primary key must still generate them.
    """
    table = create_users_table()

    assert table.primary_key is None

    table.insert([100, "Aditya", 22])
    table.insert([200, "Rajat", 24])

    assert table.record_ids == [1, 2]


def test_record_ids_continue_after_multiple_deletions():
    """
    Record IDs should continue increasing even when several
    rows have been deleted.
    """
    table = create_users_table()

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rajat", 24])
    table.insert([3, "Aman", 21])
    table.insert([4, "Simran", 23])

    table.delete(Condition("id", "=", 2))
    table.delete(Condition("id", "=", 4))

    table.insert([5, "Neha", 25])

    assert table.record_ids == [1, 3, 5]