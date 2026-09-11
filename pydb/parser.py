from pydb.lexer import Lexer

from pydb.condition import (
    Condition,
    BetweenCondition,
    LikeCondition,
    InCondition,
    AndCondition,
    OrCondition
)

from pydb.query import (
    SelectQuery,
    InsertQuery,
    UpdateQuery,
    DeleteQuery,
    CreateTableQuery,
    CreateIndexQuery,
    DropIndexQuery,
    DropTableQuery,
    ShowTablesQuery,
    DescribeTableQuery,
    AggregateExpression,
    HavingCondition,
    HavingAndCondition,
    HavingOrCondition,
    BeginQuery,
    CommitQuery,
    RollbackQuery
)


class Parser:
    """
    Converts SQL text into Query Objects.
    """

    NO_DEFAULT = object()

    def __init__(self):
        """
        Create a lexer that will convert SQL text into tokens.
        """
        self.lexer = Lexer()

    def _parse_value(
        self,
        token,
        allow_default=False
    ):
        """
        Convert a value token into the corresponding Python value.

        SQL NULL is represented internally by Python None.

        SQL DEFAULT is represented by InsertQuery.DEFAULT
        when allow_default=True.
        """
        if token.token_type == "NUMBER":
            return token.value

        if token.token_type == "STRING":
            return token.value

        if (
            token.token_type == "KEYWORD"
            and token.value == "NULL"
        ):
            return None

        if (
            allow_default
            and token.token_type == "KEYWORD"
            and token.value == "DEFAULT"
        ):
            return InsertQuery.DEFAULT
        
        if (
            token.token_type == "KEYWORD"
            and token.value == "TRUE"
        ):
            return True

        if (
            token.token_type == "KEYWORD"
            and token.value == "FALSE"
        ):
            return False

        raise ValueError(
            "Expected a valid value"
        )

    def parse(self, sql):
        """
        Tokenize SQL and parse it into a Query Object.
        """
        tokens = self.lexer.tokenize(sql)

        if not tokens:
            raise ValueError(
                "SQL query cannot be empty"
            )

        if tokens[0].token_type != "KEYWORD":
            raise ValueError(
                "Query must start with a SQL keyword"
            )

        if tokens[0].value == "SELECT":
            return self._parse_select(tokens)

        if tokens[0].value == "INSERT":
            return self._parse_insert(tokens)

        if tokens[0].value == "UPDATE":
            return self._parse_update(tokens)

        if tokens[0].value == "DELETE":
            return self._parse_delete(tokens)

        if tokens[0].value == "CREATE":
            return self._parse_create(tokens)

        if tokens[0].value == "DROP":
            return self._parse_drop(tokens)

        if tokens[0].value == "SHOW":
            return self._parse_show_tables(tokens)

        if tokens[0].value == "DESCRIBE":
            return self._parse_describe_table(tokens)

        if tokens[0].value == "BEGIN":
            return self._parse_begin(tokens)

        if tokens[0].value == "COMMIT":
            return self._parse_commit(tokens)

        if tokens[0].value == "ROLLBACK":
            return self._parse_rollback(tokens)

        raise ValueError(
            f"Unsupported SQL command: {tokens[0].value}"
        )

    # ------------------------------------------------------------------
    # CREATE DISPATCH
    # ------------------------------------------------------------------

    def _parse_create(self, tokens):
        """
        Dispatch a CREATE statement.

        Supported:

            CREATE TABLE ...
            CREATE INDEX ...
        """
        if len(tokens) < 2:
            raise ValueError(
                "CREATE requires TABLE or INDEX"
            )

        token = tokens[1]

        if token.token_type != "KEYWORD":
            raise ValueError(
                "Expected TABLE or INDEX after CREATE"
            )

        if token.value == "TABLE":
            return self._parse_create_table(
                tokens
            )

        if token.value == "INDEX":
            return self._parse_create_index(
                tokens
            )

        raise ValueError(
            f"Unsupported CREATE operation: {token.value}"
        )

    # ------------------------------------------------------------------
    # CREATE INDEX
    # ------------------------------------------------------------------

    def _parse_create_index(self, tokens):
        """
        Parse CREATE INDEX.

        Supported syntax:

            CREATE INDEX age_idx ON users(age);

            CREATE INDEX age_idx ON users(age)
            USING HASH;

            CREATE INDEX age_idx ON users(age)
            USING BTREE;

        HASH is used by default when USING is omitted.
        """
        position = 2

        # ---------------------------------
        # Index name
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires an index name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected index name after CREATE INDEX"
            )

        index_name = token.value
        position += 1

        # ---------------------------------
        # ON
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires ON"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "ON"
        ):
            raise ValueError(
                "Expected ON after index name"
            )

        position += 1

        # ---------------------------------
        # Table name
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after ON"
            )

        table_name = token.value
        position += 1

        # ---------------------------------
        # Opening parenthesis
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires a column"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            raise ValueError(
                "Expected '(' before indexed column"
            )

        position += 1

        # ---------------------------------
        # Column name
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires a column name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected column name inside index definition"
            )

        column_name = token.value
        position += 1

        # ---------------------------------
        # Closing parenthesis
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "CREATE INDEX requires ')'"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == ")"
        ):
            raise ValueError(
                "Expected ')' after indexed column"
            )

        position += 1

        # ---------------------------------
        # Optional USING
        # ---------------------------------

        index_type = "HASH"

        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "KEYWORD"
                and token.value == "USING"
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "USING requires HASH or BTREE"
                    )

                token = tokens[position]

                if (
                    token.token_type != "KEYWORD"
                    or token.value not in (
                        "HASH",
                        "BTREE"
                    )
                ):
                    raise ValueError(
                        "USING requires HASH or BTREE"
                    )

                index_type = token.value
                position += 1

        # ---------------------------------
        # Semicolon
        # ---------------------------------

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "CREATE INDEX"
        )

        return CreateIndexQuery(
            index_name=index_name,
            table_name=table_name,
            column_name=column_name,
            index_type=index_type
        )

    # ------------------------------------------------------------------
    # DROP DISPATCH
    # ------------------------------------------------------------------

    def _parse_drop(self, tokens):
        """
        Dispatch a DROP statement.

        Supported:

            DROP TABLE ...
            DROP INDEX ...
        """
        if len(tokens) < 2:
            raise ValueError(
                "DROP requires TABLE or INDEX"
            )

        token = tokens[1]

        if token.token_type != "KEYWORD":
            raise ValueError(
                "Expected TABLE or INDEX after DROP"
            )

        if token.value == "TABLE":
            return self._parse_drop_table(
                tokens
            )

        if token.value == "INDEX":
            return self._parse_drop_index(
                tokens
            )

        raise ValueError(
            f"Unsupported DROP operation: {token.value}"
        )

    # ------------------------------------------------------------------
    # DROP INDEX
    # ------------------------------------------------------------------

    def _parse_drop_index(self, tokens):
        """
        Parse DROP INDEX.

        Supported syntax:

            DROP INDEX age_idx;
        """
        position = 2

        if position >= len(tokens):
            raise ValueError(
                "DROP INDEX requires an index name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected index name after DROP INDEX"
            )

        index_name = token.value
        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DROP INDEX"
        )

        return DropIndexQuery(
            index_name=index_name
        )

    # ------------------------------------------------------------------
    # DROP TABLE
    # ------------------------------------------------------------------

    def _parse_drop_table(self, tokens):
        """
        Parse DROP TABLE.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DROP requires TABLE"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLE"
        ):
            raise ValueError(
                "Expected TABLE after DROP"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "DROP TABLE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after TABLE"
            )

        table_name = token.value
        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DROP TABLE"
        )

        return DropTableQuery(
            table_name=table_name
        )

    # ------------------------------------------------------------------
    # DESCRIBE
    # ------------------------------------------------------------------

    def _parse_describe_table(self, tokens):
        """
        Parse DESCRIBE table_name.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DESCRIBE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after DESCRIBE"
            )

        table_name = token.value
        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DESCRIBE"
        )

        return DescribeTableQuery(
            table_name=table_name
        )

    # ------------------------------------------------------------------
    # SHOW TABLES
    # ------------------------------------------------------------------

    def _parse_show_tables(self, tokens):
        """
        Parse SHOW TABLES.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "SHOW requires TABLES"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLES"
        ):
            raise ValueError(
                "Expected TABLES after SHOW"
            )

        position += 1

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "SHOW TABLES"
        )

        return ShowTablesQuery()

    # ------------------------------------------------------------------
    # WHERE CONDITION
    # ------------------------------------------------------------------

    def _parse_condition(self, tokens, position):
        """
        Parse a single WHERE condition.
        """
        if position >= len(tokens):
            raise ValueError(
                "Expected column name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected column name in condition"
            )

        column_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "Expected operator after column name"
            )

        token = tokens[position]

        # ---------------------------------
        # BETWEEN
        # ---------------------------------

        if (
            token.token_type == "KEYWORD"
            and token.value == "BETWEEN"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires a lower value"
                )

            lower_token = tokens[position]

            if lower_token.token_type not in (
                "NUMBER",
                "STRING"
            ):
                raise ValueError(
                    "BETWEEN requires a valid lower value"
                )

            lower_value = lower_token.value
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires AND"
                )

            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value != "AND"
            ):
                raise ValueError(
                    "BETWEEN requires AND"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "BETWEEN requires an upper value"
                )

            upper_token = tokens[position]

            if upper_token.token_type not in (
                "NUMBER",
                "STRING"
            ):
                raise ValueError(
                    "BETWEEN requires a valid upper value"
                )

            upper_value = upper_token.value
            position += 1

            return (
                BetweenCondition(
                    column_name,
                    lower_value,
                    upper_value
                ),
                position
            )

        # ---------------------------------
        # LIKE
        # ---------------------------------

        if (
            token.token_type == "KEYWORD"
            and token.value == "LIKE"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "LIKE requires a pattern"
                )

            pattern_token = tokens[position]

            if pattern_token.token_type != "STRING":
                raise ValueError(
                    "LIKE requires a string pattern"
                )

            position += 1

            return (
                LikeCondition(
                    column_name,
                    pattern_token.value
                ),
                position
            )

        # ---------------------------------
        # IN
        # ---------------------------------

        if (
            token.token_type == "KEYWORD"
            and token.value == "IN"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "IN requires parentheses"
                )

            token = tokens[position]

            if not (
                token.token_type == "SYMBOL"
                and token.value == "("
            ):
                raise ValueError(
                    "Expected '(' after IN"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "IN requires at least one value"
                )

            if (
                tokens[position].token_type == "SYMBOL"
                and tokens[position].value == ")"
            ):
                raise ValueError(
                    "IN requires at least one value"
                )

            values = []

            while position < len(tokens):
                token = tokens[position]

                if token.token_type not in (
                    "NUMBER",
                    "STRING"
                ):
                    raise ValueError(
                        "IN requires valid values"
                    )

                values.append(token.value)
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "IN requires closing parenthesis"
                    )

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "Expected value after comma in IN"
                        )

                    if (
                        tokens[position].token_type == "SYMBOL"
                        and tokens[position].value == ")"
                    ):
                        raise ValueError(
                            "Expected value after comma in IN"
                        )

                    continue

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ")"
                ):
                    position += 1
                    break

                raise ValueError(
                    "Expected ',' or ')' in IN list"
                )

            return (
                InCondition(
                    column_name,
                    values
                ),
                position
            )

        # ---------------------------------
        # Basic comparison
        # ---------------------------------

        if token.token_type != "OPERATOR":
            raise ValueError(
                "Expected operator after column name"
            )

        operator = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "Expected value after operator"
            )

        token = tokens[position]

        if token.token_type not in (
            "NUMBER",
            "STRING"
        ):
            raise ValueError(
                "Expected value after operator"
            )

        value = token.value
        position += 1

        return (
            Condition(
                column_name,
                operator,
                value
            ),
            position
        )

    # ------------------------------------------------------------------
    # LOGICAL CONDITIONS
    # ------------------------------------------------------------------

    def _parse_logical_conditions(
        self,
        tokens,
        position
    ):
        """
        Parse a condition followed by optional AND/OR conditions.
        """
        condition, position = self._parse_condition(
            tokens,
            position
        )

        while position < len(tokens):
            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value not in (
                    "AND",
                    "OR"
                )
            ):
                break

            logical_operator = token.value
            position += 1

            right_condition, position = (
                self._parse_condition(
                    tokens,
                    position
                )
            )

            if logical_operator == "AND":
                condition = AndCondition(
                    condition,
                    right_condition
                )

            else:
                condition = OrCondition(
                    condition,
                    right_condition
                )

        return condition, position

    # ------------------------------------------------------------------
    # SELECT EXPRESSION
    # ------------------------------------------------------------------

    def _parse_select_expression(
        self,
        tokens,
        position
    ):
        """
        Parse one SELECT expression.

        Supported expressions:

            column
            COUNT(*)
            COUNT(column)
            SUM(column)
            AVG(column)
            MIN(column)
            MAX(column)

        Aliases are parsed separately by
        _parse_select_alias().
        """
        if position >= len(tokens):
            raise ValueError(
                "Expected a SELECT expression"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected a column name or aggregate function"
            )

        name = token.value
        position += 1

        if position >= len(tokens):
            return name, position

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            return name, position

        function_name = name.upper()

        if function_name not in (
            AggregateExpression.SUPPORTED_FUNCTIONS
        ):
            raise ValueError(
                f"Unsupported aggregate function: {name}"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                f"{function_name} requires an argument"
            )

        token = tokens[position]

        # ---------------------------------
        # COUNT(*)
        # ---------------------------------

        if (
            token.token_type == "SYMBOL"
            and token.value == "*"
        ):
            if function_name != "COUNT":
                raise ValueError(
                    f"{function_name}(*) is not supported"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    f"{function_name}(*) requires closing parenthesis"
                )

            token = tokens[position]

            if not (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                raise ValueError(
                    f"{function_name}(*) requires closing parenthesis"
                )

            position += 1

            return (
                AggregateExpression(
                    "COUNT",
                    None
                ),
                position
            )

        # ---------------------------------
        # Aggregate(column)
        # ---------------------------------

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                f"{function_name} requires a column name"
            )

        column_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                f"{function_name} requires closing parenthesis"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == ")"
        ):
            raise ValueError(
                f"{function_name} requires closing parenthesis"
            )

        position += 1

        return (
            AggregateExpression(
                function_name,
                column_name
            ),
            position
        )

    # ------------------------------------------------------------------
    # SELECT ALIAS
    # ------------------------------------------------------------------

    def _parse_select_alias(
        self,
        tokens,
        position
    ):
        """
        Parse an optional SELECT expression alias.

        Supported form:

            expression AS alias
        """
        if position >= len(tokens):
            return None, position

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "AS"
        ):
            return None, position

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "AS requires an alias"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected identifier after AS"
            )

        alias = token.value
        position += 1

        return alias, position

    # ------------------------------------------------------------------
    # HAVING
    # ------------------------------------------------------------------

    def _parse_having_condition(
        self,
        tokens,
        position
    ):
        """
        Parse one HAVING comparison.
        """
        if position >= len(tokens):
            raise ValueError(
                "HAVING requires a condition"
            )

        token = tokens[position]

        # Aggregate expression.
        if (
            token.token_type == "IDENTIFIER"
            and position + 1 < len(tokens)
            and tokens[position + 1].token_type == "SYMBOL"
            and tokens[position + 1].value == "("
        ):
            expression, position = (
                self._parse_select_expression(
                    tokens,
                    position
                )
            )

            if not isinstance(
                expression,
                AggregateExpression
            ):
                raise ValueError(
                    "HAVING expression must be an aggregate "
                    "or GROUP BY column"
                )

        # Normal column.
        else:
            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected aggregate or column in HAVING"
                )

            expression = token.value
            position += 1

        if position >= len(tokens):
            raise ValueError(
                "HAVING requires an operator"
            )

        token = tokens[position]

        if token.token_type != "OPERATOR":
            raise ValueError(
                "Expected operator in HAVING"
            )

        operator = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "HAVING requires a comparison value"
            )

        token = tokens[position]

        if token.token_type not in (
            "NUMBER",
            "STRING",
            "KEYWORD"
        ):
            raise ValueError(
                "Expected a valid HAVING value"
            )

        value = self._parse_value(token)
        position += 1

        return (
            HavingCondition(
                expression,
                operator,
                value
            ),
            position
        )

    # ------------------------------------------------------------------
    # GROUP BY
    # ------------------------------------------------------------------

    def _parse_group_by(
        self,
        tokens,
        position
    ):
        """
        Parse a GROUP BY column list.
        """
        if position >= len(tokens):
            raise ValueError(
                "GROUP BY requires at least one column"
            )

        columns = []

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name after GROUP BY"
                )

            columns.append(token.value)
            position += 1

            if position >= len(tokens):
                break

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "Expected column after GROUP BY comma"
                    )

                continue

            break

        return columns, position

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------

    def _parse_select(self, tokens):
        """
        Parse a SELECT statement and create a SelectQuery object.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "SELECT requires columns"
            )

        aliases = []

        if (
            tokens[position].token_type == "SYMBOL"
            and tokens[position].value == "*"
        ):
            columns = None
            position += 1

            alias, new_position = (
                self._parse_select_alias(
                    tokens,
                    position
                )
            )

            if alias is not None:
                raise ValueError(
                    "SELECT * cannot have an alias"
                )

        else:
            columns = []

            while position < len(tokens):

                expression, position = (
                    self._parse_select_expression(
                        tokens,
                        position
                    )
                )

                alias, position = (
                    self._parse_select_alias(
                        tokens,
                        position
                    )
                )

                columns.append(expression)
                aliases.append(alias)

                if position >= len(tokens):
                    break

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "Expected column after comma"
                        )

                    continue

                break

        # ---------------------------------
        # Alias validation
        # ---------------------------------

        seen_aliases = set()

        for alias in aliases:
            if alias is None:
                continue

            if alias in seen_aliases:
                raise ValueError(
                    f"Duplicate SELECT alias '{alias}'"
                )

            seen_aliases.add(alias)

        # ---------------------------------
        # FROM
        # ---------------------------------

        if position >= len(tokens):
            raise ValueError(
                "SELECT requires FROM"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "FROM"
        ):
            raise ValueError(
                "Expected FROM after column list"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "FROM requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after FROM"
            )

        table_name = token.value
        position += 1

        # ---------------------------------
        # WHERE
        # ---------------------------------

        condition = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "WHERE"
        ):
            position += 1

            condition, position = (
                self._parse_logical_conditions(
                    tokens,
                    position
                )
            )

        # ---------------------------------
        # GROUP BY
        # ---------------------------------

        group_by = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "GROUP"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "GROUP requires BY"
                )

            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value != "BY"
            ):
                raise ValueError(
                    "Expected BY after GROUP"
                )

            position += 1

            group_by, position = self._parse_group_by(
                tokens,
                position
            )

        # ---------------------------------
        # HAVING
        # ---------------------------------

        having = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "HAVING"
        ):
            position += 1

            having, position = (
                self._parse_having_condition(
                    tokens,
                    position
                )
            )

            while position < len(tokens):
                token = tokens[position]

                if (
                    token.token_type != "KEYWORD"
                    or token.value not in (
                        "AND",
                        "OR"
                    )
                ):
                    break

                logical_operator = token.value
                position += 1

                right_condition, position = (
                    self._parse_having_condition(
                        tokens,
                        position
                    )
                )

                if logical_operator == "AND":
                    having = HavingAndCondition(
                        having,
                        right_condition
                    )

                else:
                    having = HavingOrCondition(
                        having,
                        right_condition
                    )

        # ---------------------------------
        # ORDER BY
        # ---------------------------------

        order_by = None
        descending = False

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "ORDER"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "ORDER requires BY"
                )

            token = tokens[position]

            if (
                token.token_type != "KEYWORD"
                or token.value != "BY"
            ):
                raise ValueError(
                    "Expected BY after ORDER"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "ORDER BY requires a column or alias"
                )

            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column or alias after ORDER BY"
                )

            order_by = token.value
            position += 1

            if position < len(tokens):
                token = tokens[position]

                if (
                    token.token_type == "KEYWORD"
                    and token.value in (
                        "ASC",
                        "DESC"
                    )
                ):
                    descending = (
                        token.value == "DESC"
                    )

                    position += 1

        # ---------------------------------
        # LIMIT
        # ---------------------------------

        limit = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "LIMIT"
        ):
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "LIMIT requires a number"
                )

            token = tokens[position]

            if (
                token.token_type != "NUMBER"
                or not isinstance(token.value, int)
            ):
                raise ValueError(
                    "LIMIT requires an integer"
                )

            if token.value < 0:
                raise ValueError(
                    "LIMIT cannot be negative"
                )

            limit = token.value
            position += 1

        # ---------------------------------
        # Semicolon
        # ---------------------------------

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "SELECT"
        )

        # ---------------------------------
        # SELECT / GROUP BY validation
        # ---------------------------------

        self._validate_select_grouping(
            columns,
            group_by
        )

        has_aggregate = (
            columns is not None
            and any(
                isinstance(
                    column,
                    AggregateExpression
                )
                for column in columns
            )
        )

        if having is not None and (
            group_by is None
            and not has_aggregate
        ):
            raise ValueError(
                "HAVING requires GROUP BY or an aggregate query"
            )

        return SelectQuery(
            table_name=table_name,
            columns=columns,
            condition=condition,
            order_by=order_by,
            descending=descending,
            limit=limit,
            group_by=group_by,
            having=having,
            aliases=aliases
        )

    # ------------------------------------------------------------------
    # SELECT / GROUPING VALIDATION
    # ------------------------------------------------------------------

    def _validate_select_grouping(
        self,
        columns,
        group_by
    ):
        """
        Validate combinations of normal columns, aggregates,
        and GROUP BY.
        """
        if columns is None:
            if group_by:
                raise ValueError(
                    "GROUP BY cannot be used with SELECT *"
                )

            return

        has_aggregate = any(
            isinstance(
                column,
                AggregateExpression
            )
            for column in columns
        )

        has_normal_column = any(
            isinstance(
                column,
                str
            )
            for column in columns
        )

        if not group_by:
            if has_aggregate and has_normal_column:
                raise ValueError(
                    "Cannot mix aggregate and normal columns "
                    "without GROUP BY"
                )

            return

        for column in columns:
            if isinstance(column, str):
                if column not in group_by:
                    raise ValueError(
                        f"Column '{column}' must appear "
                        f"in GROUP BY"
                    )

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------

    def _parse_insert(self, tokens):
        """
        Parse an INSERT statement.

        Supported forms:

            INSERT INTO users VALUES (1, 'Aditya');

            INSERT INTO users (id, name)
            VALUES (1, 'Aditya');
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "INSERT requires INTO"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "INTO"
        ):
            raise ValueError(
                "Expected INTO after INSERT"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "INSERT INTO requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after INTO"
            )

        table_name = token.value
        position += 1

        column_names = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "SYMBOL"
            and tokens[position].value == "("
        ):
            position += 1

            column_names = []
            seen_columns = set()

            if position >= len(tokens):
                raise ValueError(
                    "INSERT column list cannot be empty"
                )

            while position < len(tokens):
                token = tokens[position]

                if token.token_type != "IDENTIFIER":
                    raise ValueError(
                        "Expected column name in INSERT column list"
                    )

                column_name = token.value

                if column_name in seen_columns:
                    raise ValueError(
                        f"Duplicate column '{column_name}' "
                        f"in INSERT column list"
                    )

                seen_columns.add(column_name)
                column_names.append(column_name)

                position += 1

                if position >= len(tokens):
                    raise ValueError(
                        "Expected ')' after INSERT column list"
                    )

                token = tokens[position]

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ","
                ):
                    position += 1
                    continue

                if (
                    token.token_type == "SYMBOL"
                    and token.value == ")"
                ):
                    position += 1
                    break

                raise ValueError(
                    "Expected ',' or ')' after INSERT column name"
                )

        if position >= len(tokens):
            raise ValueError(
                "INSERT requires VALUES"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "VALUES"
        ):
            raise ValueError(
                "Expected VALUES after table name or column list"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "VALUES requires parentheses"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            raise ValueError(
                "Expected '(' after VALUES"
            )

        position += 1

        row = []

        if position >= len(tokens):
            raise ValueError(
                "VALUES requires at least one value"
            )

        while position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                raise ValueError(
                    "VALUES requires at least one value"
                )

            row.append(
                self._parse_value(
                    token,
                    allow_default=True
                )
            )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "VALUES requires closing parenthesis"
                )

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                position += 1
                break

            raise ValueError(
                "Expected ',' or ')' after value"
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "INSERT"
        )

        if (
            column_names is not None
            and len(column_names) != len(row)
        ):
            raise ValueError(
                "Number of columns must match number of values"
            )

        return InsertQuery(
            table_name=table_name,
            row=row,
            column_names=column_names
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def _parse_update(self, tokens):
        """
        Parse an UPDATE statement.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "UPDATE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after UPDATE"
            )

        table_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "UPDATE requires SET"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "SET"
        ):
            raise ValueError(
                "Expected SET after table name"
            )

        position += 1

        updates = {}

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name after SET"
                )

            column_name = token.value
            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected '=' after column name"
                )

            token = tokens[position]

            if not (
                token.token_type == "OPERATOR"
                and token.value == "="
            ):
                raise ValueError(
                    "Expected '=' after column name"
                )

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected value after '='"
                )

            updates[column_name] = self._parse_value(
                tokens[position]
            )

            position += 1

            if position >= len(tokens):
                break

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "KEYWORD"
                and token.value == "WHERE"
            ):
                break

            if (
                token.token_type == "SYMBOL"
                and token.value == ";"
            ):
                break

            raise ValueError(
                "Expected ',' or WHERE after update value"
            )

        condition = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "WHERE"
        ):
            position += 1

            condition, position = (
                self._parse_logical_conditions(
                    tokens,
                    position
                )
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "UPDATE"
        )

        return UpdateQuery(
            table_name=table_name,
            updates=updates,
            condition=condition
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def _parse_delete(self, tokens):
        """
        Parse a DELETE statement.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "DELETE requires FROM"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "FROM"
        ):
            raise ValueError(
                "Expected FROM after DELETE"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "DELETE FROM requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after FROM"
            )

        table_name = token.value
        position += 1

        condition = None

        if (
            position < len(tokens)
            and tokens[position].token_type == "KEYWORD"
            and tokens[position].value == "WHERE"
        ):
            position += 1

            condition, position = (
                self._parse_logical_conditions(
                    tokens,
                    position
                )
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "DELETE"
        )

        return DeleteQuery(
            table_name=table_name,
            condition=condition
        )

    # ------------------------------------------------------------------
    # CREATE TABLE
    # ------------------------------------------------------------------

    def _parse_create_table(self, tokens):
        """
        Parse CREATE TABLE with NOT NULL, UNIQUE,
        PRIMARY KEY and DEFAULT constraints.
        """
        position = 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE requires TABLE"
            )

        token = tokens[position]

        if (
            token.token_type != "KEYWORD"
            or token.value != "TABLE"
        ):
            raise ValueError(
                "Expected TABLE after CREATE"
            )

        position += 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE TABLE requires a table name"
            )

        token = tokens[position]

        if token.token_type != "IDENTIFIER":
            raise ValueError(
                "Expected table name after TABLE"
            )

        table_name = token.value
        position += 1

        if position >= len(tokens):
            raise ValueError(
                "CREATE TABLE requires column definitions"
            )

        token = tokens[position]

        if not (
            token.token_type == "SYMBOL"
            and token.value == "("
        ):
            raise ValueError(
                "Expected '(' after table name"
            )

        position += 1

        columns = []
        primary_key = None
        seen_columns = set()

        while position < len(tokens):
            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected column name"
                )

            column_name = token.value

            if column_name in seen_columns:
                raise ValueError(
                    f"Duplicate column '{column_name}' "
                    f"in CREATE TABLE"
                )

            seen_columns.add(column_name)

            position += 1

            if position >= len(tokens):
                raise ValueError(
                    "Expected data type after column name"
                )

            token = tokens[position]

            if token.token_type != "IDENTIFIER":
                raise ValueError(
                    "Expected data type after column name"
                )

            data_type = token.value.upper()
            position += 1

            nullable = True
            unique = False
            is_primary_key = False
            default = self.NO_DEFAULT

            while position < len(tokens):
                token = tokens[position]

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "NOT"
                ):
                    if position + 1 >= len(tokens):
                        raise ValueError(
                            "Expected NULL after NOT"
                        )

                    next_token = tokens[position + 1]

                    if (
                        next_token.token_type != "KEYWORD"
                        or next_token.value != "NULL"
                    ):
                        raise ValueError(
                            "Expected NULL after NOT"
                        )

                    nullable = False
                    position += 2
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "UNIQUE"
                ):
                    unique = True
                    position += 1
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "PRIMARY"
                ):
                    if position + 1 >= len(tokens):
                        raise ValueError(
                            "Expected KEY after PRIMARY"
                        )

                    next_token = tokens[position + 1]

                    if (
                        next_token.token_type != "KEYWORD"
                        or next_token.value != "KEY"
                    ):
                        raise ValueError(
                            "Expected KEY after PRIMARY"
                        )

                    is_primary_key = True
                    position += 2
                    continue

                if (
                    token.token_type == "KEYWORD"
                    and token.value == "DEFAULT"
                ):
                    if default is not self.NO_DEFAULT:
                        raise ValueError(
                            "Duplicate DEFAULT constraint"
                        )

                    position += 1

                    if position >= len(tokens):
                        raise ValueError(
                            "DEFAULT requires a value"
                        )

                    default = self._parse_value(
                        tokens[position]
                    )

                    position += 1
                    continue

                break

            if is_primary_key:
                if primary_key is not None:
                    raise ValueError(
                        "Multiple primary keys are not supported"
                    )

                primary_key = column_name

            if default is not self.NO_DEFAULT:
                columns.append(
                    (
                        column_name,
                        data_type,
                        nullable,
                        unique,
                        default
                    )
                )

            elif unique:
                columns.append(
                    (
                        column_name,
                        data_type,
                        nullable,
                        True
                    )
                )

            elif nullable:
                columns.append(
                    (
                        column_name,
                        data_type
                    )
                )

            else:
                columns.append(
                    (
                        column_name,
                        data_type,
                        False
                    )
                )

            if position >= len(tokens):
                raise ValueError(
                    "Expected ',' or ')' after column definition"
                )

            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ","
            ):
                position += 1
                continue

            if (
                token.token_type == "SYMBOL"
                and token.value == ")"
            ):
                position += 1
                break

            raise ValueError(
                "Expected ',' or ')' after column definition"
            )

        position = self._consume_semicolon(
            tokens,
            position
        )

        self._ensure_end(
            tokens,
            position,
            "CREATE TABLE"
        )

        return CreateTableQuery(
            table_name=table_name,
            columns=columns,
            primary_key=primary_key
        )

    # ------------------------------------------------------------------
    # TRANSACTIONS
    # ------------------------------------------------------------------

    def _parse_begin(self, tokens):
        """
        Parse a BEGIN transaction statement.

        Supported syntax:

            BEGIN
            BEGIN;
        """
        position = self._consume_semicolon(
            tokens,
            1
        )

        self._ensure_end(
            tokens,
            position,
            "BEGIN"
        )

        return BeginQuery()

    def _parse_commit(self, tokens):
        """
        Parse a COMMIT transaction statement.

        Supported syntax:

            COMMIT
            COMMIT;
        """
        position = self._consume_semicolon(
            tokens,
            1
        )

        self._ensure_end(
            tokens,
            position,
            "COMMIT"
        )

        return CommitQuery()

    def _parse_rollback(self, tokens):
        """
        Parse a ROLLBACK transaction statement.

        Supported syntax:

            ROLLBACK
            ROLLBACK;
        """
        position = self._consume_semicolon(
            tokens,
            1
        )

        self._ensure_end(
            tokens,
            position,
            "ROLLBACK"
        )

        return RollbackQuery()

    # ------------------------------------------------------------------
    # PARSER HELPERS
    # ------------------------------------------------------------------

    def _consume_semicolon(
        self,
        tokens,
        position
    ):
        """
        Consume an optional semicolon.
        """
        if position < len(tokens):
            token = tokens[position]

            if (
                token.token_type == "SYMBOL"
                and token.value == ";"
            ):
                position += 1

        return position

    def _ensure_end(
        self,
        tokens,
        position,
        statement_name
    ):
        """
        Ensure that no unexpected tokens remain.
        """
        if position < len(tokens):
            raise ValueError(
                f"Unexpected token after "
                f"{statement_name} statement"
            )