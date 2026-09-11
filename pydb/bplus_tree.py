class BPlusTreeNode:
    """
    Represents one node in a B+Tree.

    Internal nodes contain routing keys and child references.

    Leaf nodes contain actual keys and values and are linked
    to the next leaf node.
    """

    def __init__(self, leaf=False):
        """
        Create a B+Tree node.

        Args:
            leaf: True when this node is a leaf node.
        """
        self.leaf = leaf

        # Keys stored in this node.
        self.keys = []

        # Child nodes used by internal nodes.
        self.children = []

        # Values are stored only in leaf nodes.
        self.values = []

        # Points to the next leaf node.
        #
        # This linked-list structure is what makes
        # efficient range scans possible.
        self.next_leaf = None


class BPlusTree:
    """
    A simple standalone B+Tree implementation.

    This implementation is intentionally focused on learning
    the internal structure of a B+Tree.

    It supports:

        - key lookup
        - insertion
        - leaf splitting
        - internal-node splitting
        - ordered traversal
        - range searches
    """

    def __init__(self, minimum_degree=2):
        """
        Create an empty B+Tree.

        Args:
            minimum_degree:
                Controls the maximum number of keys per node.

                Maximum keys = 2 * t - 1
        """
        if minimum_degree < 2:
            raise ValueError(
                "B+Tree minimum degree must be at least 2"
            )

        self.minimum_degree = minimum_degree

        # Start with one empty leaf.
        self.root = BPlusTreeNode(leaf=True)

    def search(self, key):
        """
        Search for a key and return its associated value.

        Returns:
            The stored value if the key exists.
            None otherwise.
        """
        leaf = self._find_leaf(key)

        for index, current_key in enumerate(leaf.keys):
            if current_key == key:
                return leaf.values[index]

        return None

    def _find_leaf(self, key):
        """
        Find the leaf node where a key belongs.
        """
        node = self.root

        while not node.leaf:
            index = 0

            # Internal keys act as separators.
            #
            # For a key equal to a separator, move to
            # the child on the right.
            while (
                index < len(node.keys)
                and key >= node.keys[index]
            ):
                index += 1

            node = node.children[index]

        return node

    def insert(self, key, value):
        """
        Insert a key/value pair.

        If the key already exists, its value is replaced.
        """
        leaf = self._find_leaf(key)

        # Update an existing key.
        for index, current_key in enumerate(leaf.keys):
            if current_key == key:
                leaf.values[index] = value
                return

        # Find the sorted insertion position.
        index = 0

        while (
            index < len(leaf.keys)
            and key > leaf.keys[index]
        ):
            index += 1

        leaf.keys.insert(index, key)
        leaf.values.insert(index, value)

        # Split if the leaf became too large.
        if len(leaf.keys) > (
            2 * self.minimum_degree - 1
        ):
            self._split_leaf(leaf)

    def _split_leaf(self, leaf):
        """
        Split a full leaf node.

        Unlike the B-Tree implementation, the promoted
        separator key remains in the leaf.

        Example:

            [10, 20, 30, 40]

        becomes:

            [10, 20] ↔ [30, 40]

        and 30 is copied into the parent as a separator.
        """
        degree = self.minimum_degree

        new_leaf = BPlusTreeNode(leaf=True)

        split_index = degree

        new_leaf.keys = leaf.keys[
            split_index:
        ]

        new_leaf.values = leaf.values[
            split_index:
        ]

        leaf.keys = leaf.keys[
            :split_index
        ]

        leaf.values = leaf.values[
            :split_index
        ]

        # Connect the new leaf into the linked list.
        new_leaf.next_leaf = leaf.next_leaf
        leaf.next_leaf = new_leaf

        promoted_key = new_leaf.keys[0]

        # Splitting the root requires creating
        # a new internal root.
        if leaf is self.root:
            new_root = BPlusTreeNode(leaf=False)

            new_root.keys = [promoted_key]

            new_root.children = [
                leaf,
                new_leaf
            ]

            self.root = new_root

            return

        parent = self._find_parent(
            self.root,
            leaf
        )

        self._insert_into_parent(
            parent,
            promoted_key,
            new_leaf
        )

    def _insert_into_parent(
        self,
        parent,
        key,
        child
    ):
        """
        Insert a separator key and child into
        an internal node.
        """
        index = 0

        while (
            index < len(parent.keys)
            and key > parent.keys[index]
        ):
            index += 1

        parent.keys.insert(index, key)

        parent.children.insert(
            index + 1,
            child
        )

        # Split an internal node when it becomes too large.
        if len(parent.keys) > (
            2 * self.minimum_degree - 1
        ):
            self._split_internal(parent)

    def _split_internal(self, node):
        """
        Split an internal node.

        Unlike a leaf split, the promoted separator key
        is removed from the internal node.
        """
        degree = self.minimum_degree

        middle_index = degree

        promoted_key = node.keys[
            middle_index
        ]

        new_internal = BPlusTreeNode(
            leaf=False
        )

        new_internal.keys = node.keys[
            middle_index + 1:
        ]

        new_internal.children = node.children[
            middle_index + 1:
        ]

        node.keys = node.keys[
            :middle_index
        ]

        node.children = node.children[
            :middle_index + 1
        ]

        # If the node is the root, create a new root.
        if node is self.root:
            new_root = BPlusTreeNode(
                leaf=False
            )

            new_root.keys = [
                promoted_key
            ]

            new_root.children = [
                node,
                new_internal
            ]

            self.root = new_root

            return

        parent = self._find_parent(
            self.root,
            node
        )

        self._insert_into_parent(
            parent,
            promoted_key,
            new_internal
        )

    def _find_parent(self, current, target):
        """
        Find the parent of a target node.

        Returns:
            The parent node.

        Raises:
            ValueError if the target is not found.
        """
        if current.leaf:
            return None

        for child in current.children:

            if child is target:
                return current

            parent = self._find_parent(
                child,
                target
            )

            if parent is not None:
                return parent

        return None

    def items(self):
        """
        Return all key/value pairs in sorted key order.

        The traversal starts at the leftmost leaf and then
        follows the linked leaf nodes.
        """
        result = []

        leaf = self.root

        while not leaf.leaf:
            leaf = leaf.children[0]

        while leaf is not None:

            for key, value in zip(
                leaf.keys,
                leaf.values
            ):
                result.append(
                    (key, value)
                )

            leaf = leaf.next_leaf

        return result

    def range_search(
        self,
        lower=None,
        upper=None
    ):
        """
        Return key/value pairs within an inclusive range.

        Examples:

            range_search(20, 40)
            range_search(lower=20)
            range_search(upper=40)
        """
        if (
            lower is not None
            and upper is not None
            and lower > upper
        ):
            return []

        if lower is None:
            leaf = self.root

            while not leaf.leaf:
                leaf = leaf.children[0]

        else:
            leaf = self._find_leaf(lower)

        result = []

        while leaf is not None:

            for key, value in zip(
                leaf.keys,
                leaf.values
            ):
                if (
                    lower is not None
                    and key < lower
                ):
                    continue

                if (
                    upper is not None
                    and key > upper
                ):
                    return result

                result.append(
                    (key, value)
                )

            leaf = leaf.next_leaf

        return result