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
            "  .help                  Show this help message\n"
            "  .tables                List all tables\n"
            "  .schema <table>        Show table schema\n"
            "  .indexes <table>       Show table indexes\n"
            "  .history               Show database version history\n"
            "  .checkout <version>    Restore a historical version\n"
            "  .branches              Show database branches\n"
            "  .create_branch <name>  Create a branch at current version\n"
            "  .use <branch>          Switch to a branch\n"
            "  .merge <branch>        Merge a branch into current branch\n"
            "  .diff <v1> <v2>        Compare two database versions\n"
            "  .replay <version>      Replay a historical mutation\n"
            "  .compare <v1> <v2> <SELECT>\n"
            "                         Compare a SELECT across versions\n"
            "  .whatif <CREATE INDEX>; <SELECT>\n"
            "                         Analyze a hypothetical index\n"
            "  .explain <SELECT>      Show SELECT access path\n"
            "  .stats <SELECT>        Show SELECT execution statistics\n"
            "  .exit                  Exit PyDB\n"
            "  .quit                  Exit PyDB\n"
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
    # HISTORY
    # ------------------------------------------------------------------

    def _show_history(self):
        """
        Display the committed database version history.

        History is managed by the Database's HistoryManager.

        Each version contains:

            - version ID
            - parent version ID
            - branch name
            - operation
        """
        history_manager = getattr(
            self.database,
            "history",
            None
        )

        if history_manager is None:
            raise RuntimeError(
                "Database history is not available"
            )

        versions = history_manager.get_history()

        if not versions:
            self._print("No history.")
            return

        rows = []

        for version in versions:
            parent_version = (
                "-"
                if version.parent_version_id is None
                else version.parent_version_id
            )

            rows.append(
                [
                    version.version_id,
                    parent_version,
                    version.branch_name,
                    version.operation
                ]
            )

        self._print(
            self._format_table(
                [
                    "version",
                    "parent",
                    "branch",
                    "operation"
                ],
                rows
            )
        )

    # ------------------------------------------------------------------
    # CHECKOUT
    # ------------------------------------------------------------------

    def _checkout_version(self, version_id):
        """
        Restore the active database state to a historical version.

        Checkout does not create a new version. It only changes the
        current historical position.
        """
        version = self.database.checkout(
            version_id
        )

        self._print(
            f"Checked out version {version.version_id}."
        )

    # ------------------------------------------------------------------
    # BRANCHES
    # ------------------------------------------------------------------

    def _show_branches(self):
        """
        Display all branches and their current head versions.

        The currently active branch is marked with an asterisk.
        """
        branches = self.database.get_branches()

        if not branches:
            self._print("No branches.")
            return

        current_branch = (
            self.database.get_current_branch()
        )

        rows = []

        for branch_name, head_version in branches.items():
            rows.append(
                [
                    "*" if branch_name == current_branch else "",
                    branch_name,
                    head_version
                ]
            )

        self._print(
            self._format_table(
                [
                    "",
                    "branch",
                    "head"
                ],
                rows
            )
        )

    def _create_branch(self, branch_name):
        """
        Create a new branch from the current historical version.

        Creating a branch does not switch to it automatically.
        """
        self.database.create_branch(
            branch_name
        )

        current_version = (
            self.database.get_current_version()
        )

        version_id = (
            current_version.version_id
            if current_version is not None
            else "-"
        )

        self._print(
            f"Branch '{branch_name}' created "
            f"at version {version_id}."
        )

    def _use_branch(self, branch_name):
        """
        Switch to an existing branch.

        The branch's head version becomes the active database
        state.
        """
        version = self.database.switch_branch(
            branch_name
        )

        self._print(
            f"Switched to branch '{branch_name}' "
            f"at version {version.version_id}."
        )

    # ------------------------------------------------------------------
    # MERGE
    # ------------------------------------------------------------------

    def _show_merge(self, source_branch):
        """
        Merge a source branch into the currently active branch.

        The underlying Database.merge_branch() method performs
        the actual three-way merge.

        This method is responsible only for CLI presentation.
        """
        result = self.database.merge_branch(
            source_branch
        )

        self._print(
            "MERGE"
        )

        self._print(
            "--------------------------------"
        )

        self._print(
            f"Target branch : "
            f"{result['target_branch']}"
        )

        self._print(
            f"Source branch : "
            f"{result['source_branch']}"
        )

        self._print(
            f"Ancestor      : "
            f"{result['ancestor_version']}"
        )

        self._print()

        # --------------------------------------------------
        # Successful merge
        # --------------------------------------------------

        if result["status"] == "MERGED":
            self._print(
                "Status: MERGED"
            )

            self._print(
                f"Merge version : "
                f"{result['merged_version']}"
            )

            self._print(
                f"Target parent : "
                f"{result['target_version']}"
            )

            self._print(
                f"Source parent : "
                f"{result['source_version']}"
            )

            return

        # --------------------------------------------------
        # Nothing to merge
        # --------------------------------------------------

        if result["status"] == "UP_TO_DATE":
            self._print(
                "Status: UP TO DATE"
            )

            self._print(
                f"Current version: "
                f"{result['merged_version']}"
            )

            return

        # --------------------------------------------------
        # Merge conflicts
        # --------------------------------------------------

        if result["status"] == "CONFLICT":
            self._print(
                "Status: CONFLICT"
            )

            self._print()

            conflicts = result.get(
                "conflicts",
                []
            )

            self._print(
                f"{len(conflicts)} conflict"
                f"{'' if len(conflicts) == 1 else 's'} detected."
            )

            self._print()

            for index, conflict in enumerate(
                conflicts,
                start=1
            ):
                self._print(
                    f"Conflict {index}"
                )

                conflict_type = conflict.get(
                    "type",
                    "unknown"
                )

                self._print(
                    f"  Type: "
                    f"{conflict_type}"
                )

                if "table" in conflict:
                    self._print(
                        f"  Table: "
                        f"{conflict['table']}"
                    )

                if "record_id" in conflict:
                    self._print(
                        f"  Record ID: "
                        f"{conflict['record_id']}"
                    )

                if "property" in conflict:
                    self._print(
                        f"  Property: "
                        f"{conflict['property']}"
                    )

                if "base" in conflict:
                    self._print(
                        f"  Base: "
                        f"{conflict['base']}"
                    )

                if "target" in conflict:
                    self._print(
                        f"  Target: "
                        f"{conflict['target']}"
                    )

                if "source" in conflict:
                    self._print(
                        f"  Source: "
                        f"{conflict['source']}"
                    )

                if "reason" in conflict:
                    self._print(
                        f"  Reason: "
                        f"{conflict['reason']}"
                    )

                self._print()

            return

        # --------------------------------------------------
        # Defensive fallback.
        # --------------------------------------------------

        self._print(
            f"Status: {result['status']}"
        )

    # ------------------------------------------------------------------
    # VERSION DIFF
    # ------------------------------------------------------------------

    def _show_diff(
        self,
        before_version,
        after_version
    ):
        """
        Display a logical comparison between two database versions.

        The diff shows:

            - tables added
            - tables removed
            - schema changes
            - index changes
            - rows added
            - rows removed
            - rows updated
        """
        diff = self.database.diff_versions(
            before_version,
            after_version
        )

        self._print(
            f"DIFF: version "
            f"{diff['before_version']} "
            f"-> "
            f"{diff['after_version']}"
        )

        self._print()

        # ---------------------------------
        # Tables added
        # ---------------------------------

        if diff["tables_added"]:
            self._print(
                "Tables added:"
            )

            for table_name in diff["tables_added"]:
                self._print(
                    f"  + {table_name}"
                )

            self._print()

        # ---------------------------------
        # Tables removed
        # ---------------------------------

        if diff["tables_removed"]:
            self._print(
                "Tables removed:"
            )

            for table_name in diff["tables_removed"]:
                self._print(
                    f"  - {table_name}"
                )

            self._print()

        # ---------------------------------
        # Changed tables
        # ---------------------------------

        for table_name, table_diff in (
            diff["tables_changed"].items()
        ):
            self._print(
                f"Table: {table_name}"
            )

            changed_anything = False

            # Schema.
            if table_diff["schema_changed"]:
                self._print(
                    "  ~ schema changed"
                )
                changed_anything = True

            # Index definitions.
            if table_diff["indexes_changed"]:
                self._print(
                    "  ~ indexes changed"
                )
                changed_anything = True

            # Added rows.
            for entry in table_diff[
                "rows_added"
            ]:
                self._print(
                    f"  + Record "
                    f"{entry['record_id']}: "
                    f"{entry['row']}"
                )
                changed_anything = True

            # Removed rows.
            for entry in table_diff[
                "rows_removed"
            ]:
                self._print(
                    f"  - Record "
                    f"{entry['record_id']}: "
                    f"{entry['row']}"
                )
                changed_anything = True

            # Updated rows.
            for entry in table_diff[
                "rows_updated"
            ]:
                self._print(
                    f"  ~ Record "
                    f"{entry['record_id']}:"
                )

                self._print(
                    f"      before: "
                    f"{entry['before']}"
                )

                self._print(
                    f"      after:  "
                    f"{entry['after']}"
                )

                changed_anything = True

            if not changed_anything:
                self._print(
                    "  ~ changed"
                )

            self._print()

        # ---------------------------------
        # No changes
        # ---------------------------------

        if (
            not diff["tables_added"]
            and not diff["tables_removed"]
            and not diff["tables_changed"]
        ):
            self._print(
                "No changes."
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

        if isinstance(
            query,
            InsertQuery
        ):
            self._print(
                "1 row inserted."
            )
            return

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

        if isinstance(
            query,
            CreateTableQuery
        ):
            self._print(
                f"Table '{query.table_name}' created."
            )
            return

        if isinstance(
            query,
            DropTableQuery
        ):
            self._print(
                f"Table '{query.table_name}' dropped."
            )
            return

        if isinstance(
            query,
            BeginQuery
        ):
            self._print(
                "Transaction started."
            )
            return

        if isinstance(
            query,
            CommitQuery
        ):
            self._print(
                "Transaction committed."
            )
            return

        if isinstance(
            query,
            RollbackQuery
        ):
            self._print(
                "Transaction rolled back."
            )
            return

        if isinstance(
            query,
            ShowTablesQuery
        ):
            self._display_result(
                result
            )
            return

        if isinstance(
            query,
            DescribeTableQuery
        ):
            self._display_result(
                result
            )
            return

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
        # HISTORY
        # ---------------------------------

        if command_name == ".history":
            if argument:
                raise ValueError(
                    ".history does not accept arguments"
                )

            self._show_history()

            return True

        # ---------------------------------
        # WHAT-IF
        # ---------------------------------

        if command_name == ".whatif":
            if not argument:
                raise ValueError(
                    "Usage: .whatif <CREATE INDEX>; <SELECT>"
                )

            parts = argument.split(
                ";",
                maxsplit=1
            )

            if len(parts) != 2:
                raise ValueError(
                    "Usage: .whatif <CREATE INDEX>; <SELECT>"
                )

            create_index_sql = parts[0].strip()
            select_sql = parts[1].strip()

            if not create_index_sql:
                raise ValueError(
                    "CREATE INDEX query cannot be empty"
                )

            if not select_sql:
                raise ValueError(
                    "SELECT query cannot be empty"
                )

            self._show_whatif(
                create_index_sql,
                select_sql
            )

            return True

        # ---------------------------------
        # CHECKOUT
        # ---------------------------------

        if command_name == ".checkout":
            if not argument:
                raise ValueError(
                    "Usage: .checkout <version>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .checkout <version>"
                )

            self._checkout_version(
                argument
            )

            return True

        # ---------------------------------
        # COMPARE
        # ---------------------------------

        if command_name == ".compare":
            parts = argument.split(
                maxsplit=2
            )

            if len(parts) != 3:
                raise ValueError(
                    "Usage: .compare <version1> <version2> <SELECT>"
                )

            self._show_compare(
                parts[0],
                parts[1],
                parts[2]
            )

            return True

        # ---------------------------------
        # REPLAY
        # ---------------------------------

        if command_name == ".replay":
            if not argument:
                raise ValueError(
                    "Usage: .replay <version>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .replay <version>"
                )

            self._replay_version(
                argument
            )

            return True

        # ---------------------------------
        # BRANCHES
        # ---------------------------------

        if command_name == ".branches":
            if argument:
                raise ValueError(
                    ".branches does not accept arguments"
                )

            self._show_branches()

            return True

        # ---------------------------------
        # CREATE BRANCH
        # ---------------------------------

        if command_name == ".create_branch":
            if not argument:
                raise ValueError(
                    "Usage: .create_branch <name>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .create_branch <name>"
                )

            self._create_branch(
                argument
            )

            return True

        # ---------------------------------
        # USE BRANCH
        # ---------------------------------

        if command_name == ".use":
            if not argument:
                raise ValueError(
                    "Usage: .use <branch>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .use <branch>"
                )

            self._use_branch(
                argument
            )

            return True

        # ---------------------------------
        # MERGE
        # ---------------------------------

        if command_name == ".merge":
            if not argument:
                raise ValueError(
                    "Usage: .merge <branch>"
                )

            if len(
                argument.split()
            ) != 1:
                raise ValueError(
                    "Usage: .merge <branch>"
                )

            self._show_merge(
                argument
            )

            return True

        # ---------------------------------
        # DIFF
        # ---------------------------------

        if command_name == ".diff":
            if not argument:
                raise ValueError(
                    "Usage: .diff <version1> <version2>"
                )

            diff_arguments = argument.split()

            if len(
                diff_arguments
            ) != 2:
                raise ValueError(
                    "Usage: .diff <version1> <version2>"
                )

            self._show_diff(
                diff_arguments[0],
                diff_arguments[1]
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
        Execute a complete SQL statement through Database.execute().

        Database.execute() is intentionally used instead of calling
        QueryExecutor directly because Database.execute() owns the
        V2 versioning and transaction lifecycle.

        The parsed Query Object is retained so the CLI can present
        SELECT results and write-operation feedback correctly.
        """
        query = self.database.parser.parse(
            sql
        )

        # IMPORTANT:
        #
        # Always execute through Database.execute().
        #
        # This ensures:
        #
        #     normal mutation
        #         -> new history version
        #
        #     transaction mutation
        #         -> version deferred until COMMIT
        #
        #     BEGIN / COMMIT / ROLLBACK
        #         -> correct transaction handling
        #
        result = self.database.execute(
            sql
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

        if not sql.rstrip().endswith(";"):
            return False

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

    def _show_compare(
        self,
        before_version,
        after_version,
        sql
    ):
        """
        Compare one SELECT query against two historical versions.

        Historical states are evaluated independently, so the active
        database state is never changed.
        """
        comparison = self.database.compare_versions(
            before_version,
            after_version,
            sql
        )

        self._print(
            "QUERY COMPARISON"
        )

        self._print(
            "--------------------------------"
        )

        self._print(
            "Query:"
        )

        self._print(
            comparison["query"]
        )

        self._print()

        # ---------------------------------
        # First version
        # ---------------------------------

        before = comparison["before"]

        self._print(
            f"Version {comparison['before_version']}"
        )

        self._print(
            f"  Access path: "
            f"{before['stats']['access_path']}"
        )

        self._print(
            f"  Rows returned: "
            f"{len(before['result'])}"
        )

        self._print(
            f"  Condition evaluations: "
            f"{before['stats']['condition_evaluations']}"
        )

        self._print()

        # ---------------------------------
        # Second version
        # ---------------------------------

        after = comparison["after"]

        self._print(
            f"Version {comparison['after_version']}"
        )

        self._print(
            f"  Access path: "
            f"{after['stats']['access_path']}"
        )

        self._print(
            f"  Rows returned: "
            f"{len(after['result'])}"
        )

        self._print(
            f"  Condition evaluations: "
            f"{after['stats']['condition_evaluations']}"
        )

        self._print()

        # ---------------------------------
        # Result comparison
        # ---------------------------------

        if comparison["result_changed"]:
            self._print(
                "Result: DIFFERENT"
            )
        else:
            self._print(
                "Result: IDENTICAL"
            )

        # ---------------------------------
        # Access-path comparison
        # ---------------------------------

        if comparison["access_path_changed"]:
            self._print(
                "Access path: CHANGED"
            )
        else:
            self._print(
                "Access path: UNCHANGED"
            )

    def _replay_version(self, version_id):
        """
        Replay the SQL stored in a historical version.

        The SQL is executed against the current active database state
        and branch. A successful replay therefore creates a new normal
        database version.
        """
        replay_result = self.database.replay(
            version_id
        )

        self._print(
            f"Replayed version "
            f"{replay_result['source_version_id']} "
            f"as version "
            f"{replay_result['new_version_id']}."
        )

    def _show_whatif(
        self,
        create_index_sql,
        select_sql
    ):
        """
        Display a what-if planner analysis.

        The underlying Database method operates exclusively on
        temporary table copies, so the real database is untouched.
        """
        analysis = self.database.what_if_index(
            create_index_sql,
            select_sql
        )

        self._print(
            "WHAT-IF ANALYSIS"
        )

        self._print(
            "--------------------------------"
        )

        self._print(
            "Query:"
        )

        self._print(
            analysis["select_sql"]
        )

        self._print()

        # ---------------------------------
        # Hypothetical index
        # ---------------------------------

        index = analysis["index"]

        self._print(
            "Hypothetical index:"
        )

        self._print(
            f"  Name: {index['name']}"
        )

        self._print(
            f"  Type: {index['type']}"
        )

        self._print(
            f"  Table: {index['table']}"
        )

        self._print(
            f"  Column: {index['column']}"
        )

        self._print()

        # ---------------------------------
        # Existing plan
        # ---------------------------------

        without_index = (
            analysis["without_index"]
        )

        self._print(
            "WITHOUT INDEX"
        )

        self._print(
            f"  Access path: "
            f"{without_index['stats']['access_path']}"
        )

        self._print(
            f"  Rows returned: "
            f"{len(without_index['result'])}"
        )

        self._print(
            f"  Condition evaluations: "
            f"{without_index['stats']['condition_evaluations']}"
        )

        self._print()

        # ---------------------------------
        # Hypothetical plan
        # ---------------------------------

        with_index = (
            analysis["with_index"]
        )

        self._print(
            "WITH HYPOTHETICAL INDEX"
        )

        self._print(
            f"  Access path: "
            f"{with_index['stats']['access_path']}"
        )

        self._print(
            f"  Rows returned: "
            f"{len(with_index['result'])}"
        )

        self._print(
            f"  Condition evaluations: "
            f"{with_index['stats']['condition_evaluations']}"
        )

        self._print()

        # ---------------------------------
        # Comparison
        # ---------------------------------

        self._print(
            "Result changed: "
            + (
                "YES"
                if analysis["result_changed"]
                else "NO"
            )
        )

        self._print(
            "Access path changed: "
            + (
                "YES"
                if analysis["access_path_changed"]
                else "NO"
            )
        )

        self._print(
            "Condition evaluations changed: "
            + (
                "YES"
                if analysis[
                    "condition_evaluations_changed"
                ]
                else "NO"
            )
        )

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
            "PyDB v2.0"
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