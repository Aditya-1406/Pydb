import pytest
from pydb.database import Database

def test_select_column_alias():
    db = Database()

    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Aditya')")
    db.execute("INSERT INTO users VALUES (2, 'Rajat')")

    result = db.execute(
        "SELECT name AS username FROM users"
    )

    assert result == [
        ["Aditya"],
        ["Rajat"]
    ]


def test_select_multiple_aliases():
    db = Database()

    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Aditya', 22)")

    result = db.execute(
        "SELECT name AS username, age AS user_age "
        "FROM users"
    )

    assert result == [
        ["Aditya", 22]
    ]


def test_alias_with_where():
    db = Database()

    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Aditya', 22)")
    db.execute("INSERT INTO users VALUES (2, 'Rajat', 19)")

    result = db.execute(
        "SELECT name AS username "
        "FROM users "
        "WHERE age >= 20"
    )

    assert result == [
        ["Aditya"]
    ]


def test_aggregate_alias():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, department TEXT)"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (2, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (3, 'HR')"
    )

    result = db.execute(
        "SELECT department AS dept, COUNT(*) AS total "
        "FROM users "
        "GROUP BY department"
    )

    assert result == [
        ["Engineering", 2],
        ["HR", 1]
    ]


def test_order_by_alias():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, department TEXT)"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (2, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (3, 'HR')"
    )

    result = db.execute(
        "SELECT department AS dept, COUNT(*) AS total "
        "FROM users "
        "GROUP BY department "
        "ORDER BY dept"
    )

    assert result == [
        ["Engineering", 2],
        ["HR", 1]
    ]


def test_order_by_aggregate_alias_desc():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, department TEXT)"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (2, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (3, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (4, 'HR')"
    )
    db.execute(
        "INSERT INTO users VALUES (5, 'HR')"
    )
    db.execute(
        "INSERT INTO users VALUES (6, 'Sales')"
    )

    result = db.execute(
        "SELECT department AS dept, COUNT(*) AS total "
        "FROM users "
        "GROUP BY department "
        "ORDER BY total DESC"
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2],
        ["Sales", 1]
    ]


def test_order_by_alias_with_limit():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, department TEXT)"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (2, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (3, 'Engineering')"
    )
    db.execute(
        "INSERT INTO users VALUES (4, 'HR')"
    )
    db.execute(
        "INSERT INTO users VALUES (5, 'HR')"
    )
    db.execute(
        "INSERT INTO users VALUES (6, 'Sales')"
    )

    result = db.execute(
        "SELECT department AS dept, COUNT(*) AS total "
        "FROM users "
        "GROUP BY department "
        "ORDER BY total DESC "
        "LIMIT 2"
    )

    assert result == [
        ["Engineering", 3],
        ["HR", 2]
    ]


def test_duplicate_alias_rejected():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, name TEXT)"
    )

    with pytest.raises(ValueError):
        db.execute(
            "SELECT id AS value, name AS value "
            "FROM users"
        )


def test_star_alias_rejected():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, name TEXT)"
    )

    with pytest.raises(ValueError):
        db.execute(
            "SELECT * AS users_data FROM users"
        )


def test_missing_alias_rejected():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, name TEXT)"
    )

    with pytest.raises(ValueError):
        db.execute(
            "SELECT name AS FROM users"
        )


def test_alias_does_not_rename_column():
    db = Database()

    db.execute(
        "CREATE TABLE users (id INT, name TEXT)"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya')"
    )

    result = db.execute(
        "SELECT name AS username FROM users"
    )

    assert result == [
        ["Aditya"]
    ]

    describe = db.execute(
        "DESCRIBE users"
    )

    assert any(
        row["name"] == "name"
        for row in describe
    )