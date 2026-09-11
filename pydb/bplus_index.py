from pydb.bplus_tree import BPlusTree


class BPlusTreeIndex:
    """
    A database-style index backed by a B+Tree.

    The underlying B+Tree stores:

        indexed_value -> set of Record IDs

    Example:

        20 -> {1, 4}
        22 -> {2, 7, 9}
        30 -> {3}

    Unlike the basic hash Index, the B+Tree keeps indexed
    values ordered, which makes range lookups possible.

    NULL values are intentionally not stored in the B+Tree.

    This is because:

        - B+Tree keys must be orderable
        - SQL NULL does not participate in normal equality
          or range comparisons in the current PyDB semantics
    """

    def __init__(self, column_name, minimum_degree=2):
        """
        Create a B+Tree index for a table column.

        Args:
            column_name:
                Name of the indexed table column.

            minimum_degree:
                Minimum degree used by the underlying B+Tree.
        """
        self.column_name = column_name

        self.tree = BPlusTree(
            minimum_degree=minimum_degree
        )

    def insert(self, record_id, value):
        """
        Add a Record ID to the bucket belonging to an indexed value.

        Multiple rows may contain the same value.

        NULL values are ignored because the B+Tree is an ordered
        structure and the current PyDB SQL semantics do not use
        indexes for NULL comparisons.
        """
        if value is None:
            return

        record_ids = self.tree.search(value)

        if record_ids is None:
            record_ids = set()
        else:
            # Make a copy so the value stored inside the tree
            # is not accidentally mutated through an external
            # reference.
            record_ids = set(record_ids)

        record_ids.add(record_id)

        # BPlusTree.insert() replaces the value when the key
        # already exists.
        self.tree.insert(
            value,
            record_ids
        )

    def lookup(self, value):
        """
        Return the Record IDs associated with an exact value.

        NULL lookup intentionally returns no results.
        """
        if value is None:
            return set()

        record_ids = self.tree.search(value)

        if record_ids is None:
            return set()

        return set(record_ids)

    def delete(self, record_id, value):
        """
        Remove a Record ID from an indexed value bucket.

        If the bucket becomes empty, the B+Tree key itself is
        currently retained with an empty set.

        Physical B+Tree deletion is intentionally deferred to
        a separate learning milestone.
        """
        if value is None:
            return

        record_ids = self.tree.search(value)

        if record_ids is None:
            return

        record_ids = set(record_ids)

        record_ids.discard(record_id)

        if not record_ids:
            # The standalone B+Tree does not yet support
            # physical key deletion.
            #
            # Keep an empty bucket for now.
            self.tree.insert(
                value,
                set()
            )
            return

        self.tree.insert(
            value,
            record_ids
        )

    def update(
        self,
        record_id,
        old_value,
        new_value
    ):
        """
        Move a Record ID from an old indexed value to a new value.

        NULL values are handled safely because insert/delete
        ignore NULL values.
        """
        if old_value == new_value:
            return

        self.delete(
            record_id,
            old_value
        )

        self.insert(
            record_id,
            new_value
        )

    def range_lookup(
        self,
        lower=None,
        upper=None
    ):
        """
        Return Record IDs whose indexed values fall within
        an inclusive range.

        Examples:

            range_lookup(20, 30)
            range_lookup(lower=20)
            range_lookup(upper=30)

        The underlying B+Tree performs the ordered range scan.
        """
        entries = self.tree.range_search(
            lower,
            upper
        )

        result = set()

        for _, record_ids in entries:
            result.update(record_ids)

        return result

    def items(self):
        """
        Return all indexed values and their Record IDs
        in sorted value order.

        Empty buckets may appear because physical B+Tree
        key deletion has not been implemented yet.
        """
        return [
            (
                value,
                set(record_ids)
            )
            for value, record_ids in self.tree.items()
        ]