from pydb.cli import PyDBCLI
from pydb.database import Database


def test_branches_command_displays_branches(tmp_path):
    """
    .branches should display the available branches and their
    current heads.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
    )

    db.execute(
        "CREATE TABLE users (id INT, name TEXT);"
    )

    db.create_branch(
        "experiment"
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".branches"
    )

    assert len(output) == 1

    assert "branch" in output[0]
    assert "head" in output[0]
    assert "main" in output[0]
    assert "experiment" in output[0]


def test_create_branch_command_creates_branch(tmp_path):
    """
    .create_branch should create a branch at the current version.
    """
    db = Database(
        file_path=str(tmp_path / "test.json")
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
        ".create_branch experiment"
    )

    assert output == [
        "Branch 'experiment' created at version 1."
    ]

    assert (
        db.get_branch_head("experiment")
        == 1
    )


def test_use_command_switches_branch(tmp_path):
    """
    .use should switch the active branch and restore its head state.
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

    db.create_branch(
        "experiment",
        from_version_id=1
    )

    output = []

    cli = PyDBCLI(
        database=db,
        output_fn=output.append
    )

    cli._handle_input(
        ".use experiment"
    )

    assert output == [
        "Switched to branch 'experiment' at version 1."
    ]

    assert (
        db.get_current_branch()
        == "experiment"
    )

    assert (
        db.get_current_version().version_id
        == 1
    )

    assert (
        db.get_table("users").rows
        == []
    )


def test_use_unknown_branch_reports_error(tmp_path):
    """
    .use should report an error for an unknown branch.
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
        ".use experiment"
    )

    assert output == [
        "ERROR: Branch 'experiment' does not exist"
    ]


def test_create_branch_requires_name(tmp_path):
    """
    .create_branch should require exactly one branch name.
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
        ".create_branch"
    )

    assert output == [
        "ERROR: Usage: .create_branch <name>"
    ]


def test_create_branch_rejects_multiple_arguments(tmp_path):
    """
    .create_branch should reject multiple arguments.
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
        ".create_branch experiment extra"
    )

    assert output == [
        "ERROR: Usage: .create_branch <name>"
    ]


def test_use_requires_branch_name(tmp_path):
    """
    .use should require exactly one branch name.
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
        ".use"
    )

    assert output == [
        "ERROR: Usage: .use <branch>"
    ]


def test_use_rejects_multiple_arguments(tmp_path):
    """
    .use should reject multiple arguments.
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
        ".use experiment extra"
    )

    assert output == [
        "ERROR: Usage: .use <branch>"
    ]