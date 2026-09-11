import pytest
from pydb.condition import Condition
from pydb.table import Table
from pydb.condition import Condition, AndCondition, OrCondition

@pytest.fixture
def users_table():
    table = Table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    table.insert([1, "Aditya", 22])
    table.insert([2, "Rahul", 25])
    table.insert([3, "Karan", 20])

    return table


def test_greater_than(users_table):
    condition = Condition("age", ">", 22)

    result = users_table.select(condition=condition)

    assert result == [
        [2, "Rahul", 25]
    ]


def test_greater_than_or_equal(users_table):
    condition = Condition("age", ">=", 22)

    result = users_table.select(condition=condition)

    assert result == [
        [1, "Aditya", 22],
        [2, "Rahul", 25]
    ]


def test_equal(users_table):
    condition = Condition("age", "=", 22)

    result = users_table.select(condition=condition)

    assert result == [
        [1, "Aditya", 22]
    ]


def test_not_equal(users_table):
    condition = Condition("age", "!=", 22)

    result = users_table.select(condition=condition)

    assert result == [
        [2, "Rahul", 25],
        [3, "Karan", 20]
    ]


def test_less_than(users_table):
    condition = Condition("age", "<", 22)

    result = users_table.select(condition=condition)

    assert result == [
        [3, "Karan", 20]
    ]


def test_invalid_operator():
    with pytest.raises(ValueError):
        Condition("age", "LIKE", 22)


def test_invalid_column(users_table):
    condition = Condition("salary", ">", 50000)

    with pytest.raises(ValueError):
        users_table.select(condition=condition)

def test_and_condition(users_table):
    age_condition = Condition("age", ">", 20)
    name_condition = Condition("name", "=", "Aditya")

    condition = AndCondition(
        age_condition,
        name_condition
    )

    result = users_table.select(condition=condition)

    assert result == [
        [1, "Aditya", 22]
    ]

def test_or_condition(users_table):
    young_condition = Condition("age", "<", 21)
    old_condition = Condition("age", ">", 24)

    condition = OrCondition(
        young_condition,
        old_condition
    )

    result = users_table.select(condition=condition)

    assert result == [
        [2, "Rahul", 25],
        [3, "Karan", 20]
    ]