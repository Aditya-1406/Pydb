from pydb.cli import PyDBCLI
from pydb.database import Database


def test_checkout_meta_command_restores_version(tmp_path):
    """
    .checkout should restore the selected historical version.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.execute(
        "INSERT INTO users VALUES (1, 'Aditya');"
    )

    db.execute(
        "INSERT INTO users VALUES (2, 'Ravi');"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".checkout 1"
    )

    assert output == [
        "Checked out version 1."
    ]

    result = db.execute(
        "SELECT * FROM users;"
    )

    assert result == []


def test_checkout_meta_command_requires_version(tmp_path):
    """
    .checkout without a version should show usage information.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".checkout"
    )

    assert output == [
        "ERROR: Usage: .checkout <version>"
    ]


def test_checkout_meta_command_rejects_multiple_arguments(tmp_path):
    """
    .checkout should accept exactly one argument.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".checkout 1 extra"
    )

    assert output == [
        "ERROR: Usage: .checkout <version>"
    ]


def test_checkout_meta_command_reports_invalid_version(tmp_path):
    """
    .checkout should surface the database version error.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".checkout 99"
    )

    assert output == [
        "ERROR: Version '99' does not exist"
    ]


def test_checkout_meta_command_blocked_during_transaction(tmp_path):
    """
    .checkout should not be allowed during an active transaction.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.begin()

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".checkout 0"
    )

    assert output == [
        "ERROR: Cannot checkout during an active transaction"
    ]