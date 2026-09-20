from pydb.cli import PyDBCLI
from pydb.database import Database


def test_replay_command(tmp_path):
    """
    .replay should execute the historical SQL and report the new
    version.
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
        ".replay 2"
    )

    assert output == [
        "Replayed version 2 as version 3."
    ]


def test_replay_command_requires_version(tmp_path):
    """
    .replay should require one version ID.
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
        ".replay"
    )

    assert output == [
        "ERROR: Usage: .replay <version>"
    ]


def test_replay_command_rejects_multiple_arguments(tmp_path):
    """
    .replay should reject multiple arguments.
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
        ".replay 2 extra"
    )

    assert output == [
        "ERROR: Usage: .replay <version>"
    ]


def test_replay_command_reports_non_replayable_version(tmp_path):
    """
    .replay should report when a version has no SQL payload.
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
        ".replay 0"
    )

    assert output == [
        "ERROR: Version '0' does not contain replayable SQL"
    ]