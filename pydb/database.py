from pydb.table import Table
from pydb.storage import StorageEngine
from pydb.parser import Parser
from pydb.executor import QueryExecutor


class Database:
    """
    Represents the main database engine.

    The Database manages tables, persistence, and transactions.
    SQL parsing and query execution are delegated to the Parser
    and QueryExecutor respectively.
    """

    def __init__(self, file_path="pydb.json"):
        """
        Initialize the database, parser, and query executor.

        Existing database data is loaded from storage when the
        Database object is created.
        """
        self.tables = {}
        self.storage = StorageEngine(file_path)

        self.dirty = False

        # Stores the state captured when a transaction begins.
        #
        # The snapshot contains:
        #
        #     tables
        #     dirty state
        #
        # This allows ROLLBACK to restore both the database
        # contents and whether there were unsaved changes
        # before the transaction started.
        self._snapshot = None

        # Create the SQL parser.
        self.parser = Parser()

        # Create the query executor and give it this database.
        self.executor = QueryExecutor(self)

        self._load()

    def create_table(self, name, columns, primary_key=None):
        """
        Create a new table in the database.

        primary_key optionally specifies the name of the column
        that should act as the table's primary key.

        Creating a table changes the database state, so the
        database is marked as dirty.
        """
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")

        table = Table(
            name,
            columns,
            primary_key=primary_key
        )

        self.tables[name] = table

        # Schema changes must be persisted.
        self.mark_dirty()

        return table

    def get_table(self, name):
        """
        Return an existing table by name.
        """
        if name not in self.tables:
            raise ValueError(f"Table '{name}' does not exist")

        return self.tables[name]

    def list_tables(self):
        """
        Return a list containing all table names.
        """
        return list(self.tables.keys())

    def drop_table(self, name):
        """
        Remove an existing table from the database.

        Dropping a table changes the database state, so the
        database is marked as dirty.
        """
        if name not in self.tables:
            raise ValueError(f"Table '{name}' does not exist")

        del self.tables[name]

        # Schema changes must be persisted.
        self.mark_dirty()

    def execute(self, sql):
        """
        Execute a SQL statement.

        The SQL statement is first converted into a Query Object
        by the Parser. The resulting Query Object is then passed
        to the QueryExecutor for execution.
        """
        query = self.parser.parse(sql)

        return self.executor.execute(query)

    def save(self):
        """
        Persist the current database state to storage.

        After a successful save, the database no longer contains
        unsaved changes.
        """
        data = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            }
        }

        self.storage.save(data)
        self.dirty = False

    def _load(self):
        """
        Load previously stored tables from the storage engine.
        """
        data = self.storage.load()

        for name, table_data in data.get("tables", {}).items():
            self.tables[name] = Table.from_dict(table_data)

    def mark_dirty(self):
        """
        Mark the database as containing unsaved changes.
        """
        self.dirty = True

    def begin(self):
        """
        Start a new database transaction.

        The current database state is copied into an in-memory
        snapshot so that it can later be restored if rollback
        is requested.

        The current dirty state is also captured because the
        database may already contain unsaved changes before
        BEGIN is executed.
        """
        if self._snapshot is not None:
            raise RuntimeError("Transaction already active")

        self._snapshot = {
            "tables": {
                name: table.to_dict()
                for name, table in self.tables.items()
            },
            "dirty": self.dirty
        }

    def rollback(self):
        """
        Roll back the current transaction.

        The database is restored to the state captured when
        the transaction started.

        Both the table contents and the original dirty state
        are restored.
        """
        if self._snapshot is None:
            raise RuntimeError("No active transaction")

        self.tables = {
            name: Table.from_dict(table_data)
            for name, table_data in self._snapshot["tables"].items()
        }

        # Restore whether unsaved changes existed before BEGIN.
        self.dirty = self._snapshot["dirty"]

        # Clear the transaction snapshot so a new transaction
        # can be started.
        self._snapshot = None

    def commit(self):
        """
        Commit the current transaction.

        All current changes are persisted to storage and the
        transaction snapshot is removed.
        """
        if self._snapshot is None:
            raise RuntimeError("No active transaction")

        self.save()

        # Clear the transaction snapshot after the changes have
        # been successfully persisted.
        self._snapshot = None