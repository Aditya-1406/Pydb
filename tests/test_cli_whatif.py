from pydb.cli import PyDBCLI
from pydb.database import Database


def test_whatif_command(tmp_path):
    """
    .whatif should display the actual and hypothetical plans.
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
        ".whatif "
        "CREATE INDEX age_idx "
        "ON users(age) USING BTREE; "
        "SELECT * FROM users WHERE age = 22;"
    )

    combined = "\n".join(
        output
    )

    assert (
        "WHAT-IF ANALYSIS"
        in combined
    )

    assert (
        "WITHOUT INDEX"
        in combined
    )

    assert (
        "WITH HYPOTHETICAL INDEX"
        in combined
    )

    assert (
        "age_idx"
        in combined
    )

    assert (
        "Access path changed: YES"
        in combined
    )


def test_whatif_command_requires_both_queries(
    tmp_path
):
    """
    .whatif should require CREATE INDEX and SELECT separated by
    a semicolon.
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
        ".whatif CREATE INDEX age_idx ON users(age);"
    )

    assert output == [
    "ERROR: SELECT query cannot be empty"
]


def test_whatif_command_surfaces_database_error(
    tmp_path
):
    """
    CLI should surface errors from what-if analysis.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT);"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".whatif "
        "CREATE INDEX id_idx ON users(id); "
        "DELETE FROM users;"
    )

    assert output == [
        "ERROR: .whatif only supports SELECT workloads"
    ]