from pydb.lexer import Lexer


def test_select_tokens():
    """
    Verify that a basic SELECT query is tokenized correctly.
    """

    lexer = Lexer()

    tokens = lexer.tokenize(
        "SELECT name, age FROM users;"
    )

    assert [(token.token_type, token.value) for token in tokens] == [
        ("KEYWORD", "SELECT"),
        ("IDENTIFIER", "name"),
        ("SYMBOL", ","),
        ("IDENTIFIER", "age"),
        ("KEYWORD", "FROM"),
        ("IDENTIFIER", "users"),
        ("SYMBOL", ";"),
    ]


def test_where_condition_tokens():
    """
    Verify that a WHERE condition and comparison operator
    are tokenized correctly.
    """

    lexer = Lexer()

    tokens = lexer.tokenize(
        "SELECT * FROM users WHERE age >= 22;"
    )

    assert [(token.token_type, token.value) for token in tokens] == [
        ("KEYWORD", "SELECT"),
        ("SYMBOL", "*"),
        ("KEYWORD", "FROM"),
        ("IDENTIFIER", "users"),
        ("KEYWORD", "WHERE"),
        ("IDENTIFIER", "age"),
        ("OPERATOR", ">="),
        ("NUMBER", 22),
        ("SYMBOL", ";"),
    ]


def test_string_token():
    """
    Verify that quoted text is recognized as a STRING token.
    """

    lexer = Lexer()

    tokens = lexer.tokenize(
        "SELECT * FROM users WHERE name = 'Aditya';"
    )

    assert tokens[-2].token_type == "STRING"
    assert tokens[-2].value == "Aditya"


def test_decimal_number():
    """
    Verify that decimal values are converted to float.
    """

    lexer = Lexer()

    tokens = lexer.tokenize(
        "SELECT * FROM products WHERE price > 99.5;"
    )

    assert tokens[-2].token_type == "NUMBER"
    assert tokens[-2].value == 99.5


def test_keywords_are_case_insensitive():
    """
    Verify that SQL keywords are recognized regardless of case.
    """

    lexer = Lexer()

    tokens = lexer.tokenize(
        "select name from users;"
    )

    assert tokens[0].value == "SELECT"
    assert tokens[2].value == "FROM"


def test_unterminated_string():
    """
    Verify that an unterminated quoted string raises an error.
    """

    lexer = Lexer()

    try:
        lexer.tokenize(
            "SELECT * FROM users WHERE name = 'Aditya;"
        )
        assert False
    except ValueError as error:
        assert str(error) == "Unterminated string"


def test_tokenize_create_table_keywords():
    """
    Verify that CREATE TABLE PRIMARY KEY are recognized
    as SQL keywords.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (id INT PRIMARY KEY);"
    )

    assert tokens[0].token_type == "KEYWORD"
    assert tokens[0].value == "CREATE"

    assert tokens[1].token_type == "KEYWORD"
    assert tokens[1].value == "TABLE"

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "PRIMARY"

    assert tokens[7].token_type == "KEYWORD"
    assert tokens[7].value == "KEY"


def test_tokenize_not_null_keywords():
    """
    Verify that NOT NULL are recognized as SQL keywords
    inside a CREATE TABLE column definition.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (id INT NOT NULL);"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "NOT"

    assert tokens[7].token_type == "KEYWORD"
    assert tokens[7].value == "NULL"


def test_not_keyword_is_case_insensitive():
    """
    Verify that NOT is recognized as a keyword regardless
    of its letter case.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "create table users (id int not null);"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "NOT"

    assert tokens[7].token_type == "KEYWORD"
    assert tokens[7].value == "NULL"


def test_tokenize_unique_keyword():
    """
    Verify that UNIQUE is recognized as an SQL keyword.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (email TEXT UNIQUE);"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "UNIQUE"


def test_unique_keyword_is_case_insensitive():
    """
    Verify that UNIQUE is recognized as a keyword regardless
    of its letter case.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "create table users (email text unique);"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "UNIQUE"


def test_tokenize_not_null_unique_keywords():
    """
    Verify that NOT NULL UNIQUE are all recognized as
    SQL keywords inside a CREATE TABLE definition.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (email TEXT NOT NULL UNIQUE);"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "NOT"

    assert tokens[7].token_type == "KEYWORD"
    assert tokens[7].value == "NULL"

    assert tokens[8].token_type == "KEYWORD"
    assert tokens[8].value == "UNIQUE"


def test_tokenize_default_keyword():
    """
    Verify that DEFAULT is recognized as an SQL keyword.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (name TEXT DEFAULT 'Unknown');"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "DEFAULT"


def test_default_keyword_is_case_insensitive():
    """
    Verify that DEFAULT is recognized as a keyword regardless
    of its letter case.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "create table users (name text default 'Unknown');"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "DEFAULT"

def test_tokenize_default_keyword():
    """
    Verify that DEFAULT is recognized as an SQL keyword.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users (name TEXT DEFAULT 'Unknown');"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "DEFAULT"


def test_default_keyword_is_case_insensitive():
    """
    Verify that DEFAULT is recognized as a keyword regardless
    of its letter case.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "create table users (name text default 'Unknown');"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "DEFAULT"


def test_tokenize_not_null_default_keywords():
    """
    Verify that NOT NULL DEFAULT are all recognized correctly
    inside a CREATE TABLE definition.
    """
    lexer = Lexer()

    tokens = lexer.tokenize(
        "CREATE TABLE users "
        "(name TEXT NOT NULL DEFAULT 'Unknown');"
    )

    assert tokens[6].token_type == "KEYWORD"
    assert tokens[6].value == "NOT"

    assert tokens[7].token_type == "KEYWORD"
    assert tokens[7].value == "NULL"

    assert tokens[8].token_type == "KEYWORD"
    assert tokens[8].value == "DEFAULT"