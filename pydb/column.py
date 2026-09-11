class Column:
    """
    Represents a column in a database table.

    A column has a name, data type, nullable property,
    unique property, and optional default value.

    nullable=True means SQL NULL is allowed.

    nullable=False means the column behaves as NOT NULL
    and SQL NULL is rejected.

    unique=True means duplicate non-NULL values will be
    rejected by the Table layer.

    has_default=True means a DEFAULT clause was explicitly
    specified for the column.

    has_default=False means no DEFAULT clause was specified.

    A sentinel is used internally so that:

        no DEFAULT

    can be distinguished from:

        DEFAULT NULL
    """

    VALID_TYPES = {"INT", "TEXT", "FLOAT", "BOOL"}

    # Sentinel used to distinguish between:
    #
    #     no DEFAULT clause
    #
    # and:
    #
    #     DEFAULT NULL
    #
    # Python None represents SQL NULL, so None itself
    # cannot represent "no default specified".
    NO_DEFAULT = object()

    def __init__(
        self,
        name,
        data_type,
        nullable=True,
        unique=False,
        default=NO_DEFAULT
    ):
        """
        Create a column with the given metadata.

        default may be any value supported by the column's
        data type.

        DEFAULT NULL is represented by:

            default=None

        while the absence of DEFAULT is represented internally
        by the NO_DEFAULT sentinel.
        """
        if not name:
            raise ValueError("Column name cannot be empty")

        data_type = data_type.upper()

        if data_type not in self.VALID_TYPES:
            raise ValueError(
                f"Unsupported data type: {data_type}"
            )

        if not isinstance(nullable, bool):
            raise TypeError(
                "Column nullable property must be a boolean"
            )

        if not isinstance(unique, bool):
            raise TypeError(
                "Column unique property must be a boolean"
            )

        # Store the basic column metadata before validating
        # the default value.
        #
        # _is_valid_value() needs self.data_type to determine
        # whether the default has the correct type.
        self.name = name
        self.data_type = data_type
        self.nullable = nullable
        self.unique = unique

        # Determine whether DEFAULT was explicitly specified.
        self.has_default = default is not self.NO_DEFAULT

        # Store None when no DEFAULT was specified.
        #
        # has_default tells us whether that None means:
        #
        #     no DEFAULT
        #
        # or:
        #
        #     DEFAULT NULL
        self.default = (
            None
            if not self.has_default
            else default
        )

        # Validate the default only when a DEFAULT clause
        # was explicitly specified.
        if (
            self.has_default
            and not self._is_valid_value(self.default)
        ):
            raise ValueError(
                "Default value does not match column data type"
            )

    def _is_valid_value(self, value):
        """
        Check whether a value matches this column's data type.

        None represents SQL NULL.

        DEFAULT NULL is allowed here because the default value
        itself can be SQL NULL.

        NOT NULL enforcement remains the responsibility of
        validate() when a value is actually inserted or updated.
        """
        if value is None:
            return True

        if self.data_type == "INT":
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        if self.data_type == "TEXT":
            return isinstance(value, str)

        if self.data_type == "FLOAT":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        if self.data_type == "BOOL":
            return isinstance(value, bool)

        return False

    def validate(self, value):
        """
        Validate that a value matches the column's data type.

        None represents SQL NULL.

        NULL is allowed when the column is nullable.
        NULL is rejected when the column is NOT NULL.

        UNIQUE is not checked here because uniqueness depends
        on comparing the value with other rows in the table.
        """
        # SQL NULL is represented by Python None.
        if value is None:
            return self.nullable

        return self._is_valid_value(value)

    def __repr__(self):
        """
        Return a readable representation of the column.
        """
        return (
            f"Column("
            f"name='{self.name}', "
            f"type='{self.data_type}', "
            f"nullable={self.nullable}, "
            f"unique={self.unique}, "
            f"default={self.default!r}, "
            f"has_default={self.has_default}"
            f")"
        )