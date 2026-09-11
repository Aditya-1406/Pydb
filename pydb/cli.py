from pydb.database import Database
from pydb.query import (
    SelectQuery,
    AggregateExpression,
    InsertQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    DropTableQuery,
    ShowTablesQuery,
    DescribeTableQuery,
    BeginQuery,
    CommitQuery,
    RollbackQuery
)


class PyDBCLI:
    """
    Interactive command-line interface for PyDB.

    The CLI is intentionally kept separate from the database engine.

    Architecture:

        CLI
         ↓
        Database
         ↓
        Parser
         ↓
        QueryExecutor
         ↓
        Table
    """

    PROMPT = "pydb> "
    CONTINUATION_PROMPT = "...> "

    def __init__(
        self,
        database=None,
        input_fn=input,
        output_fn=print
    ):
        """
        Initialize the CLI.

        database:
            Existing Database instance.

            When omitted, a new Database instance is created.

        input_fn:
            Function used to receive user input.

        output_fn:
            Function used to display output.

        input_fn and output_fn are injectable so the CLI can
        be tested without requiring real terminal input.
        """
        self.database = (
            database
            if database is not None
            else Database()
        )

        self.input_fn = input_fn
        self.output_fn = output_fn

        self.running = True

        # Stores SQL entered across multiple lines.
        self._sql_buffer = []

    # ------------------------------------------------------------------
    # OUTPUT HELPERS
    # ------------------------------------------------------------------

    def _print(self, message=""):
        """
        Display a message through the configured output function.
        """
        self.output_fn(message)

    # ------------------------------------------------------------------
    # HELP
    # ------------------------------------------------------------------

    def _show_help(self):
        """
        Display the commands supported by the CLI.
        """
        self._print(
            "\n"
            "PyDB commands:\n"
            "  .help                 Show this help message\n"
            "  .tables               List all tables\n"
            "  .schema <table>      Show table schema\n"
            "  .indexes <table>     Show table indexes\n"
            "  .explain <SELECT>    Show SELECT access path\n"
            "  .stats <SELECT>      Show SELECT execution statistics\n"
            "  .exit                 Exit PyDB\n"
            "  .quit                 Exit PyDB\n"
        )

    # ------------------------------------------------------------------
    # TABLE LIST
    # ------------------------------------------------------------------

    def _show_tables(self):
        """
        Display all tables currently present in the database.
        """
        tables = self.database.list_tables()

        if not tables:
            self._print("No tables.")
            return

        self._print(
            self._format_table(
                ["table"],
                [
                    [table_name]
                    for table_name in tables
                ]
            )
        )

        count = len(tables)

        self._print(
            f"{count} table"
            f"{'' if count == 1 else 's'}"
        )

    # ------------------------------------------------------------------
    # SCHEMA
    # ------------------------------------------------------------------

    def _show_schema(self, table_name):
        """
        Display the schema of a table.

        This uses the Table object directly because .schema is a
        CLI command rather than SQL.
        """
        table = self.database.get_table(
            table_name
        )

        rows = []

        for column in table.columns:
            rows.append(
                [
                    column.name,
                    column.data_type,
                    "YES" if (
                        column.name == table.primary_key
                    ) else "NO",
                    "YES" if not column.nullable else "NO",
                    "YES" if column.unique else "NO"
                ]
            )

        self._print(
            self._format_table(
                [
                    "column",
                    "type",
                    "primary_key",
                    "not_null",
                    "unique"
                ],
                rows
            )
        )

    # ------------------------------------------------------------------
    # INDEXES
    # ------------------------------------------------------------------

    def _show_indexes(self, table_name):
        """
        Display all indexes defined on a table.

        PyDB currently supports:

            - hash indexes
            - B+Tree indexes
        """
        table = self.database.get_table(
            table_name
        )

        rows = []

        for column_name in table.indexes:
            rows.append(
                [
                    column_name,
                    "HASH"
                ]
            )

        for column_name in table.bplus_indexes:
            rows.append(
                [
                    column_name,
                    "BTREE"
                ]
            )

        if not rows:
            self._print("No indexes.")
            return

        self._print(
            self._format_table(
                ["column", "type"],
                rows
            )
        )

    # ------------------------------------------------------------------
    # TABLE FORMATTING
    # ------------------------------------------------------------------

    def _format_table(
        self,
        headers,
        rows
    ):
        """
        Format rows as a simple ASCII table.

        Example:

            +----+--------+-----+
            | id | name   | age |
            +----+--------+-----+
            | 1  | Aditya | 22  |
            +----+--------+-----+

        Values are converted to strings and each column receives
        enough width to fit both its header and largest value.
        """
        if not headers:
            return ""

        normalized_headers = [
            str(header)
            for header in headers
        ]

        normalized_rows = [
            [
                self._format_value(value)
                for value in row
            ]
            for row in rows
        ]

        column_count = len(
            normalized_headers
        )

        # Make malformed short rows safe.
        normalized_rows = [
            row + [""] * (
                column_count - len(row)
            )
            for row in normalized_rows
        ]

        # Ignore extra values if a malformed row contains
        # more values than the header.
        normalized_rows = [
            row[:column_count]
            for row in normalized_rows
        ]

        widths = [
            len(normalized_headers[index])
            for index in range(column_count)
        ]

        for row in normalized_rows:
            for index, value in enumerate(row):
                widths[index] = max(
                    widths[index],
                    len(value)
                )

        border = (
            "+"
            + "+".join(
                "-" * (width + 2)
                for width in widths
            )
            + "+"
        )

        lines = [
            border
        ]

        # Header row.
        lines.append(
            "|"
            + "|".join(
                f" {normalized_headers[index]:<{widths[index]}} "
                for index in range(column_count)
            )
            + "|"
        )

        lines.append(
            border
        )

        # Data rows.
        for row in normalized_rows:
            lines.append(
                "|"
                + "|".join(
                    f" {row[index]:<{widths[index]}} "
                    for index in range(column_count)
                )
                + "|"
            )

        lines.append(
            border
        )

        return "\n".join(lines)

    def _format_value(self, value):
        """
        Convert a database value into CLI display text.

        Python None is displayed as SQL-style NULL.
        """
        if value is None:
            return "NULL"

        return str(value)

    # ------------------------------------------------------------------
    # SELECT HEADER RESOLUTION
    # ------------------------------------------------------------------

    def _get_select_headers(self, query):
        """
        Determine the column headers for a SELECT query.

        Cases handled:

            SELECT *
                → actual table column names

            SELECT id, name
                → selected column names

            SELECT name AS username
                → alias

            SELECT COUNT(*)
                → readable aggregate name
        """
        table = self.database.get_table(
            query.table_name
        )

        columns = query.columns

        if columns is None:
            return [
                column.name
                for column in table.columns
            ]

        aliases = getattr(
            query,
            "aliases",
            None
        )

        if aliases is None:
            aliases = []

        headers = []

        for index, expression in enumerate(columns):

            # Explicit SELECT alias.
            if (
                index < len(aliases)
                and aliases[index] is not None
            ):
                headers.append(
                    str(aliases[index])
                )
                continue

            # Normal column.
            if isinstance(
                expression,
                str
            ):
                headers.append(
                    expression
                )
                continue

            # Aggregate expression.
            if isinstance(
                expression,
                AggregateExpression
            ):
                function_name = getattr(
                    expression,
                    "function_name",
                    "AGGREGATE"
                )

                if getattr(
                    expression,
                    "is_count_all",
                    False
                ):
                    headers.append(
                        f"{function_name}(*)"
                    )
                else:
                    column_name = getattr(
                        expression,
                        "column_name",
                        "?"
                    )

                    headers.append(
                        f"{function_name}({column_name})"
                    )

                continue

            headers.append(
                str(expression)
            )

        return headers

    # ------------------------------------------------------------------
    # SELECT RESULT DISPLAY
    # ------------------------------------------------------------------

    def _display_select_result(
        self,
        query,
        result
    ):
        """
        Display a SELECT result as a formatted table.

        Empty SELECT results are reported separately.
        """
        headers = self._get_select_headers(
            query
        )

        if not result:
            self._print(
                "(0 rows)"
            )
            return

        self._print(
            self._format_table(
                headers,
                result
            )
        )

        count = len(result)

        self._print(
            f"{count} row"
            f"{'' if count == 1 else 's'}"
        )

    # ------------------------------------------------------------------
    # GENERIC RESULT DISPLAY
    # ------------------------------------------------------------------

    def _display_result(self, result):
        """
        Display a non-SELECT QueryExecutor result.
        """
        if result is None:
            return

        if isinstance(result, list):
            if not result:
                self._print(
                    "(0 rows)"
                )
                return

            for row in result:
                self._print(
                    str(row)
                )

            return

        self._print(
            str(result)
        )

    # ------------------------------------------------------------------
    # WRITE / TRANSACTION FEEDBACK
    # ------------------------------------------------------------------

    def _display_query_success(
        self,
        query,
        result
    ):
        """
        Display a user-friendly message after a successful
        non-SELECT operation.

        The database engine continues returning its existing
        Python values. Only the CLI presentation changes.
        """

        # ---------------------------------
        # INSERT
        # ---------------------------------

        if isinstance(
            query,
            InsertQuery
        ):
            self._print(
                "1 row inserted."
            )
            return

        # ---------------------------------
        # UPDATE
        # ---------------------------------

        if isinstance(
            query,
            UpdateQuery
        ):
            count = result

            self._print(
                f"{count} row"
                f"{'' if count == 1 else 's'} "
                f"updated."
            )
            return

        # ---------------------------------
        # DELETE
        # ---------------------------------

        if isinstance(
            query,
            DeleteQuery
        ):
            count = result

            self._print(
                f"{count} row"
                f"{'' if count == 1 else 's'} "
                f"deleted."
            )
            return

        # ---------------------------------
        # CREATE TABLE
        # ---------------------------------

        if isinstance(
            query,
            CreateTableQuery
        ):
            self._print(
                f"Table '{query.table_name}' created."
            )
            return

        # ---------------------------------
        # DROP TABLE
        # ---------------------------------

        if isinstance(
            query,
            DropTableQuery
        ):
            self._print(
                f"Table '{query.table_name}' dropped."
            )
            return

        # ---------------------------------
        # BEGIN
        # ---------------------------------

        if isinstance(
            query,
            BeginQuery
        ):
            self._print(
                "Transaction started."
            )
            return

        # ---------------------------------
        # COMMIT
        # ---------------------------------

        if isinstance(
            query,
            CommitQuery
        ):
            self._print(
                "Transaction committed."
            )
            return

        # ---------------------------------
        # ROLLBACK
        # ---------------------------------

        if isinstance(
            query,
            RollbackQuery
        ):
            self._print(
                "Transaction rolled back."
            )
            return

        # ---------------------------------
        # SHOW TABLES
        # ---------------------------------

        if isinstance(
            query,
            ShowTablesQuery
        ):
            self._display_result(
                result
            )
            return

        # ---------------------------------
        # DESCRIBE
        # ---------------------------------

        if isinstance(
            query,
            DescribeTableQuery
        ):
            self._display_result(
                result
            )
            return

        # ---------------------------------
        # FALLBACK
        # ---------------------------------

        self._display_result(
            result
        )

    # ------------------------------------------------------------------
    # EXPLAIN
    # ------------------------------------------------------------------

    def _show_explain(self, sql):
        """
        Parse a SELECT statement and display the access path
        selected by the table planner.

        .explain is a CLI diagnostic command.
        It is not part of the SQL grammar.
        """
        query = self.database.parser.parse(
            sql
        )

        if not isinstance(
            query,
            SelectQuery
        ):
            raise ValueError(
                ".explain only supports SELECT statements"
            )

        table = self.database.get_table(
            query.table_name
        )

        plan = table.explain_select(
            query.condition
        )

        rows = [
            [
                "access_path",
                plan["type"]
            ]
        ]

        if "column" in plan:
            rows.append(
                [
                    "column",
                    plan["column"]
                ]
            )

        if "operator" in plan:
            rows.append(
                [
                    "operator",
                    plan["operator"]
                ]
            )

        rows.append(
            [
                "reason",
                plan["reason"]
            ]
        )

        self._print(
            self._format_table(
                ["property", "value"],
                rows
            )
        )

    # ------------------------------------------------------------------
    # EXECUTION STATISTICS
    # ------------------------------------------------------------------

    def _show_stats(self, sql):
        """
        Execute a normal SELECT through Table.select_with_stats()
        and display the resulting execution statistics.

        Statistics currently cover normal SELECT queries.

        GROUP BY and aggregate SELECT queries are rejected because
        their execution path is handled separately by QueryExecutor.
        """
        query = self.database.parser.parse(
            sql
        )

        if not isinstance(
            query,
            SelectQuery
        ):
            raise ValueError(
                ".stats only supports SELECT statements"
            )

        if query.group_by:
            raise ValueError(
                ".stats does not yet support GROUP BY queries"
            )

        if self._contains_aggregate(
            query.columns
        ):
            raise ValueError(
                ".stats does not yet support aggregate queries"
            )

        table = self.database.get_table(
            query.table_name
        )

        result, stats = table.select_with_stats(
            columns=query.columns,
            condition=query.condition,
            order_by=query.order_by,
            descending=query.descending,
            limit=query.limit
        )

        # Display the query result first.
        self._display_select_result(
            query,
            result
        )

        self._print()

        rows = [
            [
                "access_path",
                stats["access_path"]
            ],
            [
                "table_rows",
                stats["table_rows"]
            ],
            [
                "table_rows_visited",
                stats["table_rows_visited"]
            ],
            [
                "index_candidates",
                (
                    stats["index_candidates"]
                    if stats["index_candidates"] is not None
                    else "None"
                )
            ],
            [
                "condition_evaluations",
                stats["condition_evaluations"]
            ],
            [
                "rows_matched",
                stats["rows_matched"]
            ]
        ]

        self._print(
            self._format_table(
                ["metric", "value"],
                rows
            )
        )

    def _contains_aggregate(self, columns):
        """
        Return True when a SELECT column list contains an
        aggregate expression.
        """
        if columns is None:
            return False

        return any(
            isinstance(
                column,
                AggregateExpression
            )
            for column in columns
        )

    # ------------------------------------------------------------------
    # META COMMAND DISPATCH
    # ------------------------------------------------------------------

    def _execute_meta_command(self, command):
        """
        Execute a CLI meta-command.

        Returns True when the command was recognized.

        Returns False when the command is unknown.
        """
        stripped = command.strip()

        if not stripped:
            return True

        parts = stripped.split(
            maxsplit=1
        )

        command_name = parts[0].lower()

        argument = ""

        if len(parts) == 2:
            argument = parts[1].strip()

        # ---------------------------------
        # EXIT / QUIT
        # ---------------------------------

        if command_name in (
            ".exit",
            ".quit"
        ):
            if argument:
                raise ValueError(
                    f"{command_name} does not accept arguments"
                )

            # Do not allow the CLI to silently save an active
            # transaction.
            if self.database._snapshot is not None:
                raise RuntimeError(
                    "Active transaction. "
                    "Use COMMIT or ROLLBACK before exiting."
                )

            self._shutdown()

            return True

        # ---------------------------------
        # HELP
        # ---------------------------------

        if command_name == ".help":
            if argument:
                raise ValueError(
                    ".help does not accept arguments"
                )

            self._show_help()
            return True

        # ---------------------------------
        # TABLES
        # ---------------------------------

        if command_name == ".tables":
            if argument:
                raise ValueError(
                    ".tables does not accept arguments"
                )

            self._show_tables()
            return True

        # ---------------------------------
        # SCHEMA
        # ---------------------------------

        if command_name == ".schema":
            if not argument:
                raise ValueError(
                    "Usage: .schema <table>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .schema <table>"
                )

            self._show_schema(
                argument
            )

            return True

        # ---------------------------------
        # INDEXES
        # ---------------------------------

        if command_name == ".indexes":
            if not argument:
                raise ValueError(
                    "Usage: .indexes <table>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .indexes <table>"
                )

            self._show_indexes(
                argument
            )

            return True

        # ---------------------------------
        # EXPLAIN
        # ---------------------------------

        if command_name == ".explain":
            if not argument:
                raise ValueError(
                    "Usage: .explain <SELECT>"
                )

            self._show_explain(
                argument
            )

            return True

        # ---------------------------------
        # STATS
        # ---------------------------------

        if command_name == ".stats":
            if not argument:
                raise ValueError(
                    "Usage: .stats <SELECT>"
                )

            self._show_stats(
                argument
            )

            return True

        return False

    # ------------------------------------------------------------------
    # SQL EXECUTION
    # ------------------------------------------------------------------

    def _execute_sql(self, sql):
        """
        Execute a complete SQL statement through the existing
        Parser and QueryExecutor.

        The parsed Query Object is retained so that:

            - SELECT can be formatted correctly
            - write operations can receive CLI feedback
        """
        query = self.database.parser.parse(
            sql
        )

        result = self.database.executor.execute(
            query
        )

        if isinstance(
            query,
            SelectQuery
        ):
            self._display_select_result(
                query,
                result
            )
            return

        self._display_query_success(
            query,
            result
        )

    # ------------------------------------------------------------------
    # CLEAN SHUTDOWN
    # ------------------------------------------------------------------

    def _shutdown(self):
        """
        Shut down the CLI cleanly.

        Changes made outside a transaction are automatically
        persisted so that a normal user does not lose work
        simply by exiting the shell.

        Active transactions are blocked earlier by the exit
        command and therefore never reach this method.
        """
        if self.database.dirty:
            self.database.save()

            self._print(
                "Changes saved."
            )

        self.running = False

        self._sql_buffer.clear()

        self._print(
            "Goodbye."
        )

    # ------------------------------------------------------------------
    # INPUT HANDLING
    # ------------------------------------------------------------------

    def _handle_input(self, line):
        """
        Process one line entered by the user.

        Returns True when the current input completes a SQL
        statement.

        Returns False when more SQL lines are required.
        """
        stripped = line.strip()

        # Ignore empty input when no SQL is being accumulated.
        if (
            not stripped
            and not self._sql_buffer
        ):
            return True

        # ---------------------------------
        # META COMMAND
        # ---------------------------------

        if (
            not self._sql_buffer
            and stripped.startswith(".")
        ):
            try:
                recognized = self._execute_meta_command(
                    stripped
                )

                if not recognized:
                    self._print(
                        f"Unknown command: {stripped}"
                    )

            except Exception as exc:
                self._print(
                    f"ERROR: {exc}"
                )

            return True

        # ---------------------------------
        # ACCUMULATE SQL
        # ---------------------------------

        self._sql_buffer.append(
            line
        )

        sql = "\n".join(
            self._sql_buffer
        )

        # A semicolon marks the end of a SQL statement.
        if not sql.rstrip().endswith(";"):
            return False

        # ---------------------------------
        # EXECUTE COMPLETE SQL
        # ---------------------------------

        self._sql_buffer.clear()

        try:
            self._execute_sql(
                sql
            )

        except Exception as exc:
            self._print(
                f"ERROR: {exc}"
            )

        return True

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------

    def run(self):
        """
        Start the interactive PyDB shell.

        The loop continues until:

            - .exit
            - .quit
            - EOF
            - KeyboardInterrupt
        """
        self._print(
            "PyDB v1.0"
        )

        self._print(
            "Type .help for commands."
        )

        while self.running:

            prompt = (
                self.CONTINUATION_PROMPT
                if self._sql_buffer
                else self.PROMPT
            )

            try:
                line = self.input_fn(
                    prompt
                )

            except EOFError:
                self._print()

                # EOF behaves like a normal clean exit.
                if self.database._snapshot is not None:
                    self._print(
                        "ERROR: Active transaction. "
                        "Use COMMIT or ROLLBACK before exiting."
                    )
                    continue

                self._shutdown()
                break

            except KeyboardInterrupt:
                self._print()

                # Cancel unfinished SQL input without shutting
                # down the whole database shell.
                if self._sql_buffer:
                    self._sql_buffer.clear()

                    self._print(
                        "Input cancelled."
                    )

                    continue

                self._print(
                    "Use .exit to quit PyDB."
                )

                continue

            self._handle_input(
                line
            )

        return self.database


def main():
    """
    Start the PyDB CLI using the default database file.
    """
    cli = PyDBCLI()
    cli.run()


if __name__ == "__main__":
    main()