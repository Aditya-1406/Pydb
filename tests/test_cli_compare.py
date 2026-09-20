from pydb.cli import PyDBCLI
from pydb.database import Database


def test_compare_command(tmp_path):
    """
    .compare should display query behavior for two versions.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, age INT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".compare 1 2 SELECT * FROM users WHERE age > 20;"
    )

    combined = "\n".join(
        output
    )

    assert (
        "QUERY COMPARISON"
        in combined
    )

    assert (
        "Version 1"
        in combined
    )

    assert (
        "Version 2"
        in combined
    )

    assert (
        "Rows returned:"
        in combined
    )

    assert (
        "Result:"
        in combined
    )


def test_compare_command_requires_two_versions_and_query(
    tmp_path
):
    """
    .compare should require two version IDs and a SELECT statement.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".compare 1"
    )

    assert output == [
        "ERROR: Usage: .compare <version1> <version2> <SELECT>"
    ]


def test_compare_command_rejects_non_select(
    tmp_path
):
    """
    .compare should reject non-SELECT SQL.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".compare 0 0 DELETE FROM users;"
    )

    assert output == [
        "ERROR: .compare only supports SELECT statements"
    ]