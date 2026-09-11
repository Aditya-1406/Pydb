from pydb.parser import Parser
from pydb.query import InsertQuery, UpdateQuery, DeleteQuery
from pydb.condition import (
    Condition,
    AndCondition,
    OrCondition
)


def test_parse_select_all():
    """
    Test parsing SELECT * FROM table.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users;"
    )

    assert query.table_name == "users"
    assert query.columns is None


def test_parse_select_specific_columns():
    """
    Test parsing SELECT with multiple columns.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT name, age FROM users;"
    )

    assert query.table_name == "users"
    assert query.columns == ["name", "age"]


def test_parse_select_single_column():
    """
    Test parsing SELECT with a single column.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT name FROM users;"
    )

    assert query.table_name == "users"
    assert query.columns == ["name"]


def test_parse_select_missing_from():
    """
    Test that SELECT without FROM raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT name;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_select_missing_table():
    """
    Test that FROM without a table name raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT name FROM;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_select_missing_columns():
    """
    Test that SELECT without columns raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT FROM users;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_select_with_where():
    """
    Test parsing a SELECT query with a WHERE condition.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users WHERE age >= 22;"
    )

    assert query.table_name == "users"
    assert query.columns is None

    assert query.condition.column_name == "age"
    assert query.condition.operator == ">="
    assert query.condition.value == 22


def test_parse_select_with_string_where():
    """
    Test parsing a WHERE condition using a string value.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT name FROM users WHERE name = 'Aditya';"
    )

    assert query.condition.column_name == "name"
    assert query.condition.operator == "="
    assert query.condition.value == "Aditya"


def test_parse_where_missing_condition():
    """
    Test that WHERE without a condition raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_where_missing_operator():
    """
    Test that a WHERE column without an operator raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE age;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_where_missing_value():
    """
    Test that a WHERE operator without a value raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE age >=;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_where_with_and():
    """
    Test parsing two conditions connected by AND.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age >= 22 AND name = 'Aditya';"
    )

    assert isinstance(query.condition, AndCondition)

    assert query.condition.left.column_name == "age"
    assert query.condition.left.operator == ">="
    assert query.condition.left.value == 22

    assert query.condition.right.column_name == "name"
    assert query.condition.right.operator == "="
    assert query.condition.right.value == "Aditya"


def test_parse_where_with_or():
    """
    Test parsing two conditions connected by OR.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users "
        "WHERE age >= 22 OR age < 18;"
    )

    assert isinstance(query.condition, OrCondition)

    assert query.condition.left.column_name == "age"
    assert query.condition.left.operator == ">="
    assert query.condition.left.value == 22

    assert query.condition.right.column_name == "age"
    assert query.condition.right.operator == "<"
    assert query.condition.right.value == 18


def test_parse_where_and_missing_condition():
    """
    Test that AND must be followed by another condition.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE age >= 22 AND;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_where_or_missing_condition():
    """
    Test that OR must be followed by another condition.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE age >= 22 OR;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_where_missing_column_after_and():
    """
    Test that AND cannot be followed by an invalid token.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users WHERE age >= 22 AND >= 18;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_order_by():
    """
    Test parsing ORDER BY with the default ascending order.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users ORDER BY age;"
    )

    assert query.order_by == "age"
    assert query.descending is False


def test_parse_order_by_desc():
    """
    Test parsing ORDER BY with descending order.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT name, age FROM users ORDER BY age DESC;"
    )

    assert query.columns == ["name", "age"]
    assert query.order_by == "age"
    assert query.descending is True


def test_parse_order_by_asc():
    """
    Test parsing ORDER BY with explicit ascending order.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users ORDER BY age ASC;"
    )

    assert query.order_by == "age"
    assert query.descending is False


def test_parse_order_without_by():
    """
    Test that ORDER must be followed by BY.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users ORDER age;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_order_by_without_column():
    """
    Test that ORDER BY must specify a column.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users ORDER BY;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_order_by_invalid_direction():
    """
    Test that ORDER BY only accepts ASC or DESC.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users ORDER BY age RANDOM;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_limit():
    """
    Test parsing LIMIT with an integer value.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users LIMIT 5;"
    )

    assert query.limit == 5


def test_parse_limit_zero():
    """
    Test parsing LIMIT 0.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT * FROM users LIMIT 0;"
    )

    assert query.limit == 0


def test_parse_full_select_with_limit():
    """
    Test parsing SELECT with WHERE, ORDER BY, and LIMIT.
    """
    parser = Parser()

    query = parser.parse(
        "SELECT name, age "
        "FROM users "
        "WHERE age >= 18 "
        "ORDER BY age DESC "
        "LIMIT 2;"
    )

    assert query.table_name == "users"
    assert query.columns == ["name", "age"]

    assert query.condition.column_name == "age"
    assert query.condition.operator == ">="
    assert query.condition.value == 18

    assert query.order_by == "age"
    assert query.descending is True

    assert query.limit == 2


def test_parse_limit_missing_number():
    """
    Test that LIMIT without a number raises an error.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users LIMIT;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_limit_decimal():
    """
    Test that LIMIT only accepts integers.
    """
    parser = Parser()

    try:
        parser.parse(
            "SELECT * FROM users LIMIT 5.5;"
        )
        assert False
    except ValueError:
        assert True


# ============================================================
# INSERT tests
# ============================================================


def test_parse_insert():
    """
    Test parsing a basic INSERT statement.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (1, 'Aditya', 22);"
    )

    assert isinstance(query, InsertQuery)

    assert query.table_name == "users"
    assert query.row == [1, "Aditya", 22]


def test_parse_insert_without_semicolon():
    """
    Test parsing INSERT without a trailing semicolon.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (1, 'Aditya', 22)"
    )

    assert query.table_name == "users"
    assert query.row == [1, "Aditya", 22]


def test_parse_insert_multiple_values():
    """
    Test parsing an INSERT statement with multiple values.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES "
        "(1, 'Aditya', 22, 9.28);"
    )

    assert query.row == [
        1,
        "Aditya",
        22,
        9.28
    ]


def test_parse_insert_missing_into():
    """
    Test that INSERT must be followed by INTO.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT users VALUES (1, 'Aditya', 22);"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_missing_table():
    """
    Test that INSERT INTO must specify a table.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO VALUES (1, 'Aditya', 22);"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_missing_values():
    """
    Test that INSERT must contain VALUES.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_missing_parentheses():
    """
    Test that VALUES must be followed by parentheses.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users VALUES 1, 'Aditya', 22;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_empty_values():
    """
    Test that an empty VALUES list is invalid.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users VALUES ();"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_missing_value_after_comma():
    """
    Test that a comma must be followed by another value.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users VALUES (1, 'Aditya',);"
        )
        assert False
    except ValueError:
        assert True


# ============================================================
# INSERT DEFAULT tests
# ============================================================


def test_parse_insert_with_default():
    """
    Verify that INSERT can contain the DEFAULT keyword.

    DEFAULT must remain distinct from SQL NULL because the
    executor will later resolve DEFAULT using the column's
    configured default value.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (DEFAULT);"
    )

    assert isinstance(query, InsertQuery)

    assert query.row == [
        InsertQuery.DEFAULT
    ]


def test_parse_insert_with_null():
    """
    Verify that INSERT continues to parse SQL NULL as Python
    None rather than treating it as DEFAULT.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (NULL);"
    )

    assert query.row == [
        None
    ]


def test_parse_insert_with_value_and_default():
    """
    Verify that DEFAULT can appear alongside normal values.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES ('Aditya', DEFAULT);"
    )

    assert query.row[0] == "Aditya"
    assert query.row[1] is InsertQuery.DEFAULT


def test_parse_insert_with_multiple_defaults():
    """
    Verify that multiple DEFAULT values can appear in the
    same INSERT statement.
    """
    parser = Parser()

    query = parser.parse(
        "INSERT INTO users VALUES (DEFAULT, DEFAULT);"
    )

    assert query.row == [
        InsertQuery.DEFAULT,
        InsertQuery.DEFAULT
    ]


def test_parse_insert_default_with_trailing_comma():
    """
    Verify that DEFAULT cannot be followed by a trailing comma.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users VALUES (DEFAULT,);"
        )
        assert False
    except ValueError:
        assert True


def test_parse_insert_default_without_comma():
    """
    Verify that two consecutive values must be separated by
    a comma.
    """
    parser = Parser()

    try:
        parser.parse(
            "INSERT INTO users VALUES (DEFAULT DEFAULT);"
        )
        assert False
    except ValueError:
        assert True


# ============================================================
# UPDATE tests
# ============================================================


def test_parse_update():
    """
    Test parsing a basic UPDATE statement.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users SET age = 23;"
    )

    assert isinstance(query, UpdateQuery)

    assert query.table_name == "users"
    assert query.updates == {
        "age": 23
    }

    assert query.condition is None


def test_parse_update_with_string():
    """
    Test parsing UPDATE with a string value.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users SET name = 'Aditya';"
    )

    assert query.table_name == "users"
    assert query.updates == {
        "name": "Aditya"
    }


def test_parse_update_multiple_columns():
    """
    Test parsing UPDATE with multiple column assignments.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users "
        "SET age = 23, name = 'Rahul';"
    )

    assert query.updates == {
        "age": 23,
        "name": "Rahul"
    }


def test_parse_update_with_where():
    """
    Test parsing an UPDATE statement with a WHERE condition.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users "
        "SET age = 23 "
        "WHERE name = 'Aditya';"
    )

    assert query.updates == {
        "age": 23
    }

    assert isinstance(
        query.condition,
        Condition
    )

    assert query.condition.column_name == "name"
    assert query.condition.operator == "="
    assert query.condition.value == "Aditya"


def test_parse_update_with_and_condition():
    """
    Test parsing UPDATE with multiple WHERE conditions
    connected using AND.
    """
    parser = Parser()

    query = parser.parse(
        "UPDATE users "
        "SET age = 23 "
        "WHERE name = 'Aditya' AND age >= 22;"
    )

    assert isinstance(
        query.condition,
        AndCondition
    )

    assert query.condition.left.column_name == "name"
    assert query.condition.left.value == "Aditya"

    assert query.condition.right.column_name == "age"
    assert query.condition.right.operator == ">="
    assert query.condition.right.value == 22


def test_parse_update_missing_set():
    """
    Test that UPDATE must contain SET.
    """
    parser = Parser()

    try:
        parser.parse(
            "UPDATE users age = 23;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_update_missing_column():
    """
    Test that SET must be followed by a column name.
    """
    parser = Parser()

    try:
        parser.parse(
            "UPDATE users SET = 23;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_update_missing_value():
    """
    Test that an assignment must contain a value.
    """
    parser = Parser()

    try:
        parser.parse(
            "UPDATE users SET age =;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_update_missing_value_after_comma():
    """
    Test that a comma must be followed by another assignment.
    """
    parser = Parser()

    try:
        parser.parse(
            "UPDATE users SET age = 23,;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_update_invalid_operator():
    """
    Test that UPDATE assignments only support '='.
    """
    parser = Parser()

    try:
        parser.parse(
            "UPDATE users SET age >= 23;"
        )
        assert False
    except ValueError:
        assert True


# ============================================================
# DELETE tests
# ============================================================


def test_parse_delete():
    """
    Test parsing a basic DELETE statement.
    """
    parser = Parser()

    query = parser.parse(
        "DELETE FROM users;"
    )

    assert isinstance(query, DeleteQuery)

    assert query.table_name == "users"
    assert query.condition is None


def test_parse_delete_without_semicolon():
    """
    Test parsing DELETE without a trailing semicolon.
    """
    parser = Parser()

    query = parser.parse(
        "DELETE FROM users"
    )

    assert query.table_name == "users"
    assert query.condition is None


def test_parse_delete_with_where():
    """
    Test parsing DELETE with a WHERE condition.
    """
    parser = Parser()

    query = parser.parse(
        "DELETE FROM users WHERE age < 18;"
    )

    assert query.table_name == "users"

    assert isinstance(
        query.condition,
        Condition
    )

    assert query.condition.column_name == "age"
    assert query.condition.operator == "<"
    assert query.condition.value == 18


def test_parse_delete_with_string_condition():
    """
    Test parsing DELETE with a string WHERE condition.
    """
    parser = Parser()

    query = parser.parse(
        "DELETE FROM users WHERE name = 'Aditya';"
    )

    assert query.condition.column_name == "name"
    assert query.condition.operator == "="
    assert query.condition.value == "Aditya"


def test_parse_delete_with_and_condition():
    """
    Test parsing DELETE with multiple conditions using AND.
    """
    parser = Parser()

    query = parser.parse(
        "DELETE FROM users "
        "WHERE age < 18 AND name = 'Aditya';"
    )

    assert isinstance(
        query.condition,
        AndCondition
    )

    assert query.condition.left.column_name == "age"
    assert query.condition.left.operator == "<"
    assert query.condition.left.value == 18

    assert query.condition.right.column_name == "name"
    assert query.condition.right.operator == "="
    assert query.condition.right.value == "Aditya"


def test_parse_delete_missing_from():
    """
    Test that DELETE must be followed by FROM.
    """
    parser = Parser()

    try:
        parser.parse(
            "DELETE users;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_delete_missing_table():
    """
    Test that DELETE FROM must specify a table.
    """
    parser = Parser()

    try:
        parser.parse(
            "DELETE FROM;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_delete_missing_where_condition():
    """
    Test that WHERE must contain a valid condition.
    """
    parser = Parser()

    try:
        parser.parse(
            "DELETE FROM users WHERE;"
        )
        assert False
    except ValueError:
        assert True


# ============================================================
# CREATE TABLE tests
# ============================================================


from pydb.query import CreateTableQuery


def test_parse_create_table():
    """
    Verify that a basic CREATE TABLE statement is parsed.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    assert isinstance(query, CreateTableQuery)

    assert query.table_name == "users"

    assert query.columns == [
        ("id", "INT"),
        ("name", "TEXT")
    ]

    assert query.primary_key is None


def test_parse_create_table_with_primary_key():
    """
    Verify that PRIMARY KEY is correctly parsed.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT PRIMARY KEY, "
        "name TEXT, "
        "age INT"
        ");"
    )

    assert isinstance(query, CreateTableQuery)

    assert query.table_name == "users"

    assert query.columns == [
        ("id", "INT"),
        ("name", "TEXT"),
        ("age", "INT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_without_semicolon():
    """
    Verify that the semicolon is optional.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users (id INT, name TEXT)"
    )

    assert query.table_name == "users"

    assert query.columns == [
        ("id", "INT"),
        ("name", "TEXT")
    ]


def test_parse_create_table_requires_table():
    """
    Verify that CREATE must be followed by TABLE.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE users (id INT);"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_requires_columns():
    """
    Verify that CREATE TABLE requires column definitions.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users;"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_rejects_empty_columns():
    """
    Verify that an empty column list is rejected.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users ();"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_rejects_multiple_primary_keys():
    """
    Verify that multiple primary-key columns are rejected.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users ("
            "id INT PRIMARY KEY, "
            "user_id INT PRIMARY KEY"
            ");"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_with_not_null():
    """
    Verify that NOT NULL is correctly parsed for a column.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT NOT NULL, "
        "name TEXT"
        ");"
    )

    assert isinstance(query, CreateTableQuery)

    assert query.table_name == "users"

    assert query.columns == [
        ("id", "INT", False),
        ("name", "TEXT")
    ]

    assert query.primary_key is None


def test_parse_create_table_without_not_null_remains_nullable():
    """
    Verify that columns without NOT NULL keep the existing
    nullable-by-default behavior.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT, "
        "name TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT"),
        ("name", "TEXT")
    ]


def test_parse_create_table_not_null_is_case_insensitive():
    """
    Verify that NOT NULL can be written using different
    combinations of uppercase and lowercase letters.
    """
    parser = Parser()

    query = parser.parse(
        "create table users ("
        "id INT not null, "
        "name TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", False),
        ("name", "TEXT")
    ]


def test_parse_create_table_not_without_null_is_invalid():
    """
    Verify that NOT by itself is not accepted as a valid
    column constraint.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users ("
            "id INT NOT, "
            "name TEXT"
            ");"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_not_null_with_primary_key():
    """
    Verify that NOT NULL and PRIMARY KEY can be used together.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT NOT NULL PRIMARY KEY, "
        "name TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", False),
        ("name", "TEXT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_with_unique():
    """
    Verify that UNIQUE is correctly parsed for a column.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT, "
        "email TEXT UNIQUE"
        ");"
    )

    assert isinstance(query, CreateTableQuery)

    assert query.columns == [
        ("id", "INT"),
        ("email", "TEXT", True, True)
    ]

    assert query.primary_key is None


def test_parse_create_table_with_not_null_unique():
    """
    Verify that NOT NULL and UNIQUE can be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT, "
        "email TEXT NOT NULL UNIQUE"
        ");"
    )

    assert query.columns == [
        ("id", "INT"),
        ("email", "TEXT", False, True)
    ]


def test_parse_create_table_with_unique_not_null():
    """
    Verify that UNIQUE and NOT NULL can be written
    in the opposite order.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT, "
        "email TEXT UNIQUE NOT NULL"
        ");"
    )

    assert query.columns == [
        ("id", "INT"),
        ("email", "TEXT", False, True)
    ]


def test_parse_create_table_unique_is_case_insensitive():
    """
    Verify that UNIQUE is recognized regardless of case.
    """
    parser = Parser()

    query = parser.parse(
        "create table users ("
        "email text unique"
        ");"
    )

    assert query.columns == [
        ("email", "TEXT", True, True)
    ]


def test_parse_create_table_unique_with_primary_key():
    """
    Verify that UNIQUE and PRIMARY KEY can be used
    together on a column.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT PRIMARY KEY UNIQUE, "
        "email TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", True, True),
        ("email", "TEXT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_unique_primary_key_reverse_order():
    """
    Verify that UNIQUE can appear before PRIMARY KEY.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT UNIQUE PRIMARY KEY, "
        "email TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", True, True),
        ("email", "TEXT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_not_null_unique_primary_key():
    """
    Verify that NOT NULL, UNIQUE, and PRIMARY KEY
    can all be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT NOT NULL UNIQUE PRIMARY KEY, "
        "email TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", False, True),
        ("email", "TEXT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_unique_not_null_primary_key():
    """
    Verify that UNIQUE, NOT NULL, and PRIMARY KEY
    can be written in another supported order.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT UNIQUE NOT NULL PRIMARY KEY, "
        "email TEXT"
        ");"
    )

    assert query.columns == [
        ("id", "INT", False, True),
        ("email", "TEXT")
    ]

    assert query.primary_key == "id"


def test_parse_create_table_unique_without_primary_key():
    """
    Verify that UNIQUE does not automatically become
    a primary key.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "email TEXT UNIQUE"
        ");"
    )

    assert query.primary_key is None
    assert query.columns == [
        ("email", "TEXT", True, True)
    ]


# ============================================================
# CREATE TABLE DEFAULT tests
# ============================================================


def test_parse_create_table_with_default():
    """
    Verify that DEFAULT is correctly parsed for a column.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "age INT DEFAULT 18"
        ");"
    )

    assert query.columns == [
        ("age", "INT", True, False, 18)
    ]


def test_parse_create_table_with_text_default():
    """
    Verify that a TEXT column can have a string DEFAULT value.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "name TEXT DEFAULT 'Unknown'"
        ");"
    )

    assert query.columns == [
        ("name", "TEXT", True, False, "Unknown")
    ]


def test_parse_create_table_with_null_default():
    """
    Verify that DEFAULT NULL is distinct from having no DEFAULT.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "name TEXT DEFAULT NULL"
        ");"
    )

    assert query.columns == [
        ("name", "TEXT", True, False, None)
    ]


def test_parse_create_table_default_with_not_null():
    """
    Verify that DEFAULT and NOT NULL can be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "age INT DEFAULT 18 NOT NULL"
        ");"
    )

    assert query.columns == [
        ("age", "INT", False, False, 18)
    ]


def test_parse_create_table_not_null_with_default():
    """
    Verify that NOT NULL and DEFAULT can be written
    in the opposite order.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "age INT NOT NULL DEFAULT 18"
        ");"
    )

    assert query.columns == [
        ("age", "INT", False, False, 18)
    ]


def test_parse_create_table_default_with_unique():
    """
    Verify that DEFAULT and UNIQUE can be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "email TEXT DEFAULT 'unknown@example.com' UNIQUE"
        ");"
    )

    assert query.columns == [
        (
            "email",
            "TEXT",
            True,
            True,
            "unknown@example.com"
        )
    ]


def test_parse_create_table_unique_with_default():
    """
    Verify that UNIQUE and DEFAULT can be written
    in the opposite order.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "email TEXT UNIQUE DEFAULT 'unknown@example.com'"
        ");"
    )

    assert query.columns == [
        (
            "email",
            "TEXT",
            True,
            True,
            "unknown@example.com"
        )
    ]


def test_parse_create_table_default_with_primary_key():
    """
    Verify that DEFAULT and PRIMARY KEY can be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT DEFAULT 1 PRIMARY KEY"
        ");"
    )

    assert query.columns == [
        ("id", "INT", True, False, 1)
    ]

    assert query.primary_key == "id"


def test_parse_create_table_primary_key_with_default():
    """
    Verify that PRIMARY KEY and DEFAULT can be written
    in the opposite order.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT PRIMARY KEY DEFAULT 1"
        ");"
    )

    assert query.columns == [
        ("id", "INT", True, False, 1)
    ]

    assert query.primary_key == "id"


def test_parse_create_table_default_not_null_unique_primary_key():
    """
    Verify that DEFAULT, NOT NULL, UNIQUE, and PRIMARY KEY
    can all be combined.
    """
    parser = Parser()

    query = parser.parse(
        "CREATE TABLE users ("
        "id INT DEFAULT 1 NOT NULL UNIQUE PRIMARY KEY"
        ");"
    )

    assert query.columns == [
        ("id", "INT", False, True, 1)
    ]

    assert query.primary_key == "id"


def test_parse_create_table_duplicate_default_is_invalid():
    """
    Verify that a column cannot declare DEFAULT more than once.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users ("
            "age INT DEFAULT 18 DEFAULT 21"
            ");"
        )
        assert False
    except ValueError:
        assert True


def test_parse_create_table_default_without_value_is_invalid():
    """
    Verify that DEFAULT must be followed by a value.
    """
    parser = Parser()

    try:
        parser.parse(
            "CREATE TABLE users ("
            "age INT DEFAULT"
            ");"
        )
        assert False
    except ValueError:
        assert True