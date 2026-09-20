from pydb.cli import PyDBCLI
from pydb.database import Database


class FakeInput:
    """
    Provide predefined CLI input for tests.
    """

    def __init__(self, lines):
        self.lines = iter(lines)

    def __call__(self, prompt=""):
        try:
            return next(self.lines)
        except StopIteration:
            raise EOFError


class CapturedOutput:
    """
    Capture CLI output for assertions.
    """

    def __init__(self):
        self.messages = []

    def __call__(self, message=""):
        self.messages.append(
            str(message)
        )


def create_database(tmp_path):
    """
    Create an isolated database for one CLI test.

    A pytest temporary directory is used so CLI tests never
    depend on the real pydb.json database.
    """
    return Database(
        file_path=str(
            tmp_path / "test_pydb.json"
        )
    )


def test_cli_starts_and_exits(tmp_path):
    """
    CLI should start and exit cleanly.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    assert cli.running is False

    assert "PyDB v2.0" in output.messages


def test_help_command(tmp_path):
    """
    .help should display supported CLI commands.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".help",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert ".help" in combined_output
    assert ".tables" in combined_output
    assert ".schema <table>" in combined_output
    assert ".indexes <table>" in combined_output
    assert ".exit" in combined_output


def test_tables_command(tmp_path):
    """
    .tables should display database table names
    using the CLI table formatter.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    input_fn = FakeInput(
        [
            ".tables",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "| table |" in combined_output
    assert "| users |" in combined_output
    assert "1 table" in combined_output


def test_tables_command_with_multiple_tables(tmp_path):
    """
    .tables should display every table.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    database.create_table(
        "orders",
        [
            ("id", "INT")
        ]
    )

    input_fn = FakeInput(
        [
            ".tables",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "| users  |" in combined_output
    assert "| orders |" in combined_output
    assert "2 tables" in combined_output


def test_tables_command_when_empty(tmp_path):
    """
    .tables should clearly report an empty database.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".tables",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    assert "No tables." in output.messages


def test_schema_command(tmp_path):
    """
    .schema should display table columns and constraints
    using the CLI table formatter.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT", False, True)
        ],
        primary_key="id"
    )

    input_fn = FakeInput(
        [
            ".schema users",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "| column |" in combined_output
    assert "| id     | INT" in combined_output
    assert "| name   | TEXT" in combined_output

    assert "YES" in combined_output
    assert "NOT" not in combined_output


def test_indexes_command(tmp_path):
    """
    .indexes should display both hash and B+Tree indexes.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    table = database.get_table(
        "users"
    )

    table.create_index(
        "age"
    )

    table.create_bplus_tree_index(
        "age"
    )

    input_fn = FakeInput(
        [
            ".indexes users",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "| column | type  |" in combined_output
    assert "| age    | HASH  |" in combined_output
    assert "| age    | BTREE |" in combined_output


def test_indexes_command_without_indexes(tmp_path):
    """
    .indexes should clearly report when no indexes exist.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT")
        ]
    )

    input_fn = FakeInput(
        [
            ".indexes users",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    assert "No indexes." in output.messages


def test_format_table(tmp_path):
    """
    The CLI should render rows as a readable ASCII table.
    """
    database = create_database(
        tmp_path
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        output_fn=output
    )

    table = cli._format_table(
        ["id", "name", "age"],
        [
            [1, "Aditya", 22],
            [2, "Rahul", 25]
        ]
    )

    assert "| id | name   | age |" in table

    assert "| 1  | Aditya | 22  |" in table

    assert "| 2  | Rahul  | 25  |" in table

    assert "+" in table


def test_format_table_handles_null(tmp_path):
    """
    Python None should be displayed as SQL NULL.
    """
    database = create_database(
        tmp_path
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        output_fn=output
    )

    table = cli._format_table(
        ["id", "name"],
        [
            [1, None]
        ]
    )

    assert "NULL" in table


def test_select_result_is_formatted(tmp_path):
    """
    SELECT results should be displayed using column headers
    and an ASCII table.
    """
    database = create_database(
        tmp_path
    )

    database.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name TEXT,
            age INT
        );
        """
    )

    database.execute(
        "INSERT INTO users VALUES (1, 'Aditya', 22);"
    )

    input_fn = FakeInput(
        [
            "SELECT * FROM users;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "| id | name   | age |" in combined_output

    assert "| 1  | Aditya | 22  |" in combined_output

    assert "1 row" in combined_output


def test_select_empty_result_is_formatted(tmp_path):
    """
    An empty SELECT result should be displayed clearly.
    """
    database = create_database(
        tmp_path
    )

    database.execute(
        """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name TEXT,
            age INT
        );
        """
    )

    input_fn = FakeInput(
        [
            "SELECT * FROM users;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "(0 rows)" in combined_output


def test_multiline_sql_is_executed(tmp_path):
    """
    SQL can span multiple lines until ';' is encountered.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    input_fn = FakeInput(
        [
            "INSERT INTO users",
            "VALUES (1, 'Aditya');",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    table = database.get_table(
        "users"
    )

    assert table.rows == [
        [1, "Aditya"]
    ]


def test_sql_error_is_reported(tmp_path):
    """
    SQL errors should be displayed as CLI errors rather
    than terminating the shell.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            "SELECT * FROM missing_table;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "ERROR:" in combined_output
    assert "missing_table" in combined_output


def test_unknown_meta_command_is_reported(tmp_path):
    """
    Unknown dot commands should not be treated as SQL.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".foobar",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    assert (
        "Unknown command: .foobar"
        in output.messages
    )

def test_explain_command_for_bplus_tree(tmp_path):
    """
    .explain should show the access path selected by
    the existing PyDB planner.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    table = database.get_table(
        "users"
    )

    table.create_bplus_tree_index(
        "age"
    )

    input_fn = FakeInput(
        [
            ".explain SELECT * FROM users WHERE age > 30;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "access_path" in combined_output
    assert "BTREE_RANGE" in combined_output
    assert "age" in combined_output
    assert ">" in combined_output


def test_explain_command_requires_select(tmp_path):
    """
    .explain should reject non-SELECT statements.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".explain INSERT INTO users VALUES (1);",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert (
        ".explain only supports SELECT statements"
        in combined_output
    )


def test_stats_command_for_full_scan(tmp_path):
    """
    .stats should expose statistics for a full table scan.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    table = database.get_table(
        "users"
    )

    table.insert(
        [1, "Aditya", 22]
    )

    table.insert(
        [2, "Rahul", 25]
    )

    table.insert(
        [3, "Aman", 30]
    )

    input_fn = FakeInput(
        [
            ".stats SELECT * FROM users WHERE age > 20;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "FULL_SCAN" in combined_output
    assert "table_rows" in combined_output
    assert "3" in combined_output
    assert "condition_evaluations" in combined_output
    assert "rows_matched" in combined_output


def test_stats_command_for_bplus_tree(tmp_path):
    """
    .stats should expose B+Tree execution statistics.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    table = database.get_table(
        "users"
    )

    table.insert(
        [1, "Aditya", 22]
    )

    table.insert(
        [2, "Rahul", 25]
    )

    table.insert(
        [3, "Aman", 30]
    )

    table.insert(
        [4, "Neha", 35]
    )

    table.create_bplus_tree_index(
        "age"
    )

    input_fn = FakeInput(
        [
            ".stats SELECT * FROM users WHERE age > 30;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "BTREE_RANGE" in combined_output
    assert "table_rows" in combined_output
    assert "4" in combined_output
    assert "index_candidates" in combined_output
    assert "condition_evaluations" in combined_output
    assert "rows_matched" in combined_output


def test_stats_rejects_group_by(tmp_path):
    """
    .stats should clearly report that grouped queries are not
    covered by the current statistics implementation.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT"),
            ("age", "INT")
        ]
    )

    input_fn = FakeInput(
        [
            ".stats SELECT age, COUNT(*) FROM users GROUP BY age;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert (
        ".stats does not yet support GROUP BY queries"
        in combined_output
    )


def test_help_includes_explain_and_stats(tmp_path):
    """
    .help should advertise the new diagnostic commands.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            ".help",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert ".explain <SELECT>" in combined_output
    assert ".stats <SELECT>" in combined_output

def test_insert_feedback(tmp_path):
    """
    INSERT should produce a user-friendly success message.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("name", "TEXT")
        ],
        primary_key="id"
    )

    input_fn = FakeInput(
        [
            "INSERT INTO users VALUES (1, 'Aditya');",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "1 row inserted." in combined_output
    assert "Changes saved." in combined_output
    assert "Goodbye." in combined_output


def test_update_feedback(tmp_path):
    """
    UPDATE should report the number of affected rows.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT"),
            ("age", "INT")
        ],
        primary_key="id"
    )

    database.execute(
        "INSERT INTO users VALUES (1, 22);"
    )

    input_fn = FakeInput(
        [
            "UPDATE users SET age = 23 WHERE id = 1;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "1 row updated." in combined_output


def test_delete_feedback(tmp_path):
    """
    DELETE should report the number of deleted rows.
    """
    database = create_database(
        tmp_path
    )

    database.create_table(
        "users",
        [
            ("id", "INT")
        ],
        primary_key="id"
    )

    database.execute(
        "INSERT INTO users VALUES (1);"
    )

    input_fn = FakeInput(
        [
            "DELETE FROM users WHERE id = 1;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "1 row deleted." in combined_output


def test_transaction_feedback(tmp_path):
    """
    BEGIN, COMMIT, and ROLLBACK should provide clear CLI
    feedback.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            "BEGIN;",
            "ROLLBACK;",
            "BEGIN;",
            "COMMIT;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert "Transaction started." in combined_output
    assert "Transaction rolled back." in combined_output
    assert "Transaction committed." in combined_output


def test_exit_saves_dirty_database(tmp_path):
    """
    Normal non-transaction changes should be persisted automatically
    when the CLI exits.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            """
            CREATE TABLE users (
                id INT PRIMARY KEY,
                name TEXT
            );
            """,
            "INSERT INTO users VALUES (1, 'Aditya');",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    assert database.dirty is False

    combined_output = "\n".join(
        output.messages
    )

    assert "Changes saved." in combined_output


def test_exit_blocked_during_transaction(tmp_path):
    """
    CLI should not exit while a transaction is active.
    """
    database = create_database(
        tmp_path
    )

    input_fn = FakeInput(
        [
            "BEGIN;",
            ".exit",
            "ROLLBACK;",
            ".exit"
        ]
    )

    output = CapturedOutput()

    cli = PyDBCLI(
        database=database,
        input_fn=input_fn,
        output_fn=output
    )

    cli.run()

    combined_output = "\n".join(
        output.messages
    )

    assert (
        "Active transaction. "
        "Use COMMIT or ROLLBACK before exiting."
        in combined_output
    )

    assert "Transaction rolled back." in combined_output

    assert "Goodbye." in combined_output