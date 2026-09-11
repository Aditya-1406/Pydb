class Token:
    """
    Represents one token produced by the SQL lexer.
    """

    def __init__(self, token_type, value):
        """
        Store the token's type and its actual value.
        """
        self.token_type = token_type
        self.value = value

    def __repr__(self):
        """
        Return a readable representation of the token.
        """
        return f"Token({self.token_type!r}, {self.value!r})"


class Lexer:
    """
    Converts a SQL query string into a sequence of tokens.
    """

    KEYWORDS = {
        "SELECT",
        "FROM",
        "WHERE",
        "INSERT",
        "INTO",
        "VALUES",
        "UPDATE",
        "SET",
        "DELETE",
        "CREATE",
        "TABLE",
        "TABLES",
        "INDEX",
        "ON",
        "USING",
        "HASH",
        "BTREE",
        "DROP",
        "SHOW",
        "DESCRIBE",
        "NULL",
        "NOT",
        "UNIQUE",
        "DEFAULT",
        "PRIMARY",
        "KEY",
        "ORDER",
        "BY",
        "LIMIT",
        "AND",
        "OR",
        "BETWEEN",
        "LIKE",
        "IN",
        "ASC",
        "DESC",
        "GROUP",
        "HAVING",
        "AS",
        "TRUE",
        "FALSE",

        # Transaction statements
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
    }

    OPERATORS = {
        "=",
        "!=",
        ">",
        "<",
        ">=",
        "<=",
    }

    def tokenize(self, sql):
        """
        Convert SQL text into a list of Token objects.
        """
        tokens = []
        position = 0

        while position < len(sql):
            character = sql[position]

            # ---------------------------------
            # Whitespace
            # ---------------------------------

            if character.isspace():
                position += 1
                continue

            # ---------------------------------
            # Symbols
            # ---------------------------------

            if character in ",;()*":
                tokens.append(
                    Token("SYMBOL", character)
                )

                position += 1
                continue

            # ---------------------------------
            # Strings
            # ---------------------------------

            if character in "'\"":
                quote = character
                position += 1

                start = position

                while position < len(sql):
                    if sql[position] == quote:
                        break

                    position += 1

                if position >= len(sql):
                    raise ValueError(
                        "Unterminated string"
                    )

                value = sql[start:position]

                tokens.append(
                    Token("STRING", value)
                )

                position += 1
                continue

            # ---------------------------------
            # Numbers
            # ---------------------------------

            if character.isdigit():
                start = position

                while position < len(sql) and (
                    sql[position].isdigit()
                    or sql[position] == "."
                ):
                    position += 1

                value = sql[start:position]

                if "." in value:
                    value = float(value)
                else:
                    value = int(value)

                tokens.append(
                    Token("NUMBER", value)
                )

                continue

            # ---------------------------------
            # Operators
            # ---------------------------------

            if character in "<>!=":
                operator = character

                if (
                    position + 1 < len(sql)
                    and sql[position + 1] == "="
                ):
                    operator += "="
                    position += 1

                if operator not in self.OPERATORS:
                    raise ValueError(
                        f"Unsupported operator: {operator}"
                    )

                tokens.append(
                    Token("OPERATOR", operator)
                )

                position += 1
                continue

            # ---------------------------------
            # Identifiers / Keywords
            # ---------------------------------

            if character.isalpha() or character == "_":
                start = position

                while position < len(sql) and (
                    sql[position].isalnum()
                    or sql[position] == "_"
                ):
                    position += 1

                value = sql[start:position]

                upper_value = value.upper()

                if upper_value in self.KEYWORDS:
                    tokens.append(
                        Token("KEYWORD", upper_value)
                    )

                else:
                    tokens.append(
                        Token("IDENTIFIER", value)
                    )

                continue

            # ---------------------------------
            # Unsupported character
            # ---------------------------------

            raise ValueError(
                f"Unexpected character: {character}"
            )

        return tokens