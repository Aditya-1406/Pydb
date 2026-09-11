from pydb.column import Column
import pytest


def test_create_column():
    column = Column("age", "INT")

    assert column.name == "age"
    assert column.data_type == "INT"
    assert column.nullable is True
    assert column.unique is False


def test_column_type_is_case_insensitive():
    column = Column("name", "text")

    assert column.data_type == "TEXT"


def test_valid_value():
    column = Column("age", "INT")

    assert column.validate(25)


def test_invalid_value():
    column = Column("age", "INT")

    assert not column.validate("25")


def test_invalid_data_type():
    with pytest.raises(ValueError):
        Column("age", "MONEY")


def test_nullable_column_allows_null():
    """
    A nullable column should accept SQL NULL,
    which is represented internally by Python None.
    """
    column = Column("age", "INT", nullable=True)

    assert column.nullable is True
    assert column.validate(None)


def test_not_null_column_rejects_null():
    """
    A NOT NULL column should reject SQL NULL.
    """
    column = Column("age", "INT", nullable=False)

    assert column.nullable is False
    assert not column.validate(None)


def test_not_null_column_still_accepts_valid_value():
    """
    NOT NULL only rejects NULL. It should not reject
    otherwise valid values of the correct data type.
    """
    column = Column("age", "INT", nullable=False)

    assert column.validate(25)


def test_nullable_column_rejects_invalid_non_null_value():
    """
    Nullable does not mean any value is accepted.
    Non-NULL values must still match the column's data type.
    """
    column = Column("age", "INT", nullable=True)

    assert not column.validate("25")


def test_unique_column_stores_unique_property():
    """
    A UNIQUE column should store its unique property as True.
    """
    column = Column("email", "TEXT", unique=True)

    assert column.unique is True


def test_column_is_not_unique_by_default():
    """
    Columns should not be UNIQUE unless explicitly requested.
    """
    column = Column("email", "TEXT")

    assert column.unique is False


def test_unique_column_still_validates_data_type():
    """
    UNIQUE should not change normal data-type validation.
    The value must still match the column's data type.
    """
    column = Column("email", "TEXT", unique=True)

    assert column.validate("user@example.com")
    assert not column.validate(123)


def test_unique_nullable_column_allows_null():
    """
    A UNIQUE nullable column should still allow SQL NULL.

    Uniqueness across multiple rows will be enforced later
    by the Table layer, not by Column.validate().
    """
    column = Column(
        "email",
        "TEXT",
        nullable=True,
        unique=True
    )

    assert column.unique is True
    assert column.nullable is True
    assert column.validate(None)

def test_column_without_default():
    """
    Verify that a column without DEFAULT has no default value.
    """
    column = Column("name", "TEXT")

    assert column.has_default is False


def test_column_with_text_default():
    """
    Verify that a TEXT column can have a TEXT default value.
    """
    column = Column(
        "name",
        "TEXT",
        default="Unknown"
    )

    assert column.has_default is True
    assert column.default == "Unknown"


def test_column_with_int_default():
    """
    Verify that an INT column can have an INT default value.
    """
    column = Column(
        "age",
        "INT",
        default=18
    )

    assert column.has_default is True
    assert column.default == 18


def test_column_with_float_default():
    """
    Verify that a FLOAT column can have a FLOAT default value.
    """
    column = Column(
        "price",
        "FLOAT",
        default=99.99
    )

    assert column.has_default is True
    assert column.default == 99.99


def test_column_with_bool_default():
    """
    Verify that a BOOL column can have a BOOL default value.
    """
    column = Column(
        "active",
        "BOOL",
        default=True
    )

    assert column.has_default is True
    assert column.default is True


def test_column_with_null_default():
    """
    Verify that DEFAULT NULL is distinguishable from no DEFAULT.
    """
    column = Column(
        "nickname",
        "TEXT",
        default=None
    )

    assert column.has_default is True
    assert column.default is None


def test_column_rejects_invalid_default_type():
    """
    Verify that a default value must match the column data type.
    """
    try:
        Column(
            "age",
            "INT",
            default="eighteen"
        )
        assert False
    except ValueError as error:
        assert str(error) == (
            "Default value does not match column data type"
        )


def test_column_default_with_not_null():
    """
    Verify that a NOT NULL column can have a valid default.
    """
    column = Column(
        "name",
        "TEXT",
        nullable=False,
        default="Unknown"
    )

    assert column.nullable is False
    assert column.has_default is True
    assert column.default == "Unknown"