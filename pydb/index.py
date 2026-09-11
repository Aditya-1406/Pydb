class Index:
    """
    A standalone in-memory index that maps column values
    to sets of internal Record IDs.
    """

    def __init__(self, column_name):
        """
        Initialize an empty index for a specific column.

        Args:
            column_name: Name of the table column this index belongs to.
        """
        self.column_name = column_name
        self.entries = {}

    def insert(self, record_id, value):
        """
        Add a Record ID under the supplied indexed value.

        Multiple Record IDs can have the same value, so each
        value maps to a set of Record IDs.
        """
        if value not in self.entries:
            self.entries[value] = set()

        self.entries[value].add(record_id)

    def lookup(self, value):
        """
        Return the Record IDs associated with a value.

        A copy of the set is returned so callers cannot
        accidentally modify the index's internal state.
        """
        return self.entries.get(value, set()).copy()

    def delete(self, record_id, value):
        """
        Remove a Record ID from the supplied value bucket.

        If the value or Record ID does not exist, nothing happens.

        If the Record ID was the last entry for that value,
        the value itself is removed from the index.
        """
        record_ids = self.entries.get(value)

        if record_ids is None:
            return

        record_ids.discard(record_id)

        if not record_ids:
            del self.entries[value]

    def update(self, record_id, old_value, new_value):
        """
        Move a Record ID from an old indexed value to a new value.

        For example:

            22 -> {1, 2}
            25 -> {3}

        Updating Record ID 1 from 22 to 25 results in:

            22 -> {2}
            25 -> {1, 3}
        """
        if old_value == new_value:
            self.insert(record_id, new_value)
            return

        self.delete(record_id, old_value)
        self.insert(record_id, new_value)