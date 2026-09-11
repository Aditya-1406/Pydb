#storage.py

import json
from pathlib import Path


class StorageEngine:
    """
    Handles persistent storage of database data.

    A normal file path stores data on disk.

    The special path ':memory:' creates an in-memory storage
    engine that does not read from or write to a file.
    """

    def __init__(self, file_path="pydb.json"):
        """
        Initialize the storage engine.

        ':memory:' is treated as a special in-memory mode.
        """
        self.file_path = Path(file_path)
        self.in_memory = file_path == ":memory:"

    def save(self, data):
        """
        Save database data to disk.

        In-memory databases do not persist their data to disk.
        """
        if self.in_memory:
            return

        with self.file_path.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4
            )

    def load(self):
        """
        Load database data from disk.

        In-memory databases always start with an empty state.
        """
        if self.in_memory:
            return {}

        if not self.file_path.exists():
            return {}

        with self.file_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)