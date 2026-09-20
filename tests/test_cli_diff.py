from pydb.cli import PyDBCLI
from pydb.database import Database


def test_diff_command_displays_row_changes(tmp_path):
    """
    .diff should display logical row changes between versions.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".diff 1 2"
    )

    combined = "\n".join(
        output
    )

    assert (
        "DIFF: version 1 -> 2"
        in combined
    )

    assert (
        "Table: users"
        in combined
    )

    assert (
        "+ Record 1: [1, 'Aditya']"
        in combined
    )


def test_diff_command_reports_no_changes(tmp_path):
    """
    Comparing the same version should report no changes.
    """
    db = Database(
        file_path=str(
            tmp_path / "test.json"
        )
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".diff 1 1"
    )

    assert output == [
        "DIFF: version 1 -> 1",
        "",
        "No changes."
    ]


def test_diff_command_requires_two_versions(tmp_path):
    """
    .diff should require exactly two version IDs.
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
        ".diff 1"
    )

    assert output == [
        "ERROR: Usage: .diff <version1> <version2>"
    ]


def test_diff_command_rejects_extra_arguments(tmp_path):
    """
    .diff should reject more than two version IDs.
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
        ".diff 1 2 3"
    )

    assert output == [
        "ERROR: Usage: .diff <version1> <version2>"
    ]


def test_diff_command_reports_unknown_version(tmp_path):
    """
    .diff should report an unknown historical version.
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
        ".diff 1 99"
    )

    assert output == [
        "ERROR: Version '1' does not exist"
    ]