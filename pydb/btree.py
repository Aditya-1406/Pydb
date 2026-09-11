class BTreeNode:
    """
    Represents one node inside a B-Tree.

    A node stores sorted keys and, for internal nodes,
    references to child nodes.
    """

    def __init__(self, leaf=False):
        """
        Create a B-Tree node.

        Args:
            leaf: True when this node does not have children.
        """
        self.leaf = leaf
        self.keys = []
        self.children = []


class BTree:
    """
    A simple B-Tree implementation.

    The tree is intentionally standalone for now.

    It stores keys only. Record IDs and PyDB integration
    will be introduced after the tree itself is proven correct.
    """

    def __init__(self, minimum_degree=2):
        """
        Create an empty B-Tree.

        Args:
            minimum_degree:
                Controls how many keys a node can contain.

                Maximum keys = 2 * t - 1
                Maximum children = 2 * t
        """
        if minimum_degree < 2:
            raise ValueError(
                "B-Tree minimum degree must be at least 2"
            )

        self.minimum_degree = minimum_degree

        # An empty B-Tree starts with one empty leaf root.
        self.root = BTreeNode(leaf=True)

    def search(self, key):
        """
        Search the B-Tree for a key.

        Returns:
            True if the key exists.
            False otherwise.
        """
        return self._search(self.root, key)

    def _search(self, node, key):
        """
        Recursively search a particular node.

        The keys are sorted, so we first locate the position
        where the key should exist.
        """
        index = 0

        while (
            index < len(node.keys)
            and key > node.keys[index]
        ):
            index += 1

        # The key exists in this node.
        if (
            index < len(node.keys)
            and key == node.keys[index]
        ):
            return True

        # A leaf has nowhere else to search.
        if node.leaf:
            return False

        # Continue into the appropriate child.
        return self._search(
            node.children[index],
            key
        )

    def insert(self, key):
        """
        Insert a key into the B-Tree.

        Duplicate keys are ignored for this initial
        learning implementation.
        """
        if self.search(key):
            return

        root = self.root

        # If the root is full, the tree needs a new root.
        if len(root.keys) == (
            2 * self.minimum_degree - 1
        ):
            new_root = BTreeNode(leaf=False)

            new_root.children.append(root)

            self.root = new_root

            self._split_child(
                new_root,
                0
            )

            self._insert_non_full(
                new_root,
                key
            )

        else:
            self._insert_non_full(
                root,
                key
            )

    def _insert_non_full(self, node, key):
        """
        Insert a key into a node that is guaranteed
        not to be full.
        """
        index = len(node.keys) - 1

        if node.leaf:
            # Make space for the new key.
            node.keys.append(None)

            while (
                index >= 0
                and key < node.keys[index]
            ):
                node.keys[index + 1] = node.keys[index]
                index -= 1

            node.keys[index + 1] = key

            return

        # Find the child that should contain the key.
        while (
            index >= 0
            and key < node.keys[index]
        ):
            index -= 1

        child_index = index + 1

        child = node.children[child_index]

        # If the child is full, split it first.
        if len(child.keys) == (
            2 * self.minimum_degree - 1
        ):
            self._split_child(
                node,
                child_index
            )

            # After splitting, determine which side
            # should receive the new key.
            if key > node.keys[child_index]:
                child_index += 1

        self._insert_non_full(
            node.children[child_index],
            key
        )

    def _split_child(self, parent, child_index):
        """
        Split a full child of a parent node.

        The middle key moves into the parent.

        Example for minimum degree 2:

            [10 | 20 | 30]

        becomes:

              [20]
             /    \
          [10]   [30]
        """
        degree = self.minimum_degree

        full_child = parent.children[child_index]

        new_child = BTreeNode(
            leaf=full_child.leaf
        )

        middle_key = full_child.keys[
            degree - 1
        ]

        # Keys after the middle key move
        # into the new right-hand child.
        new_child.keys = full_child.keys[
            degree:
        ]

        # The left child keeps keys before
        # the middle key.
        full_child.keys = full_child.keys[
            :degree - 1
        ]

        # Internal nodes also need to move
        # the corresponding children.
        if not full_child.leaf:
            new_child.children = full_child.children[
                degree:
            ]

            full_child.children = full_child.children[
                :degree
            ]

        # Insert the new child beside the old child.
        parent.children.insert(
            child_index + 1,
            new_child
        )

        # Promote the middle key into the parent.
        parent.keys.insert(
            child_index,
            middle_key
        )

    def traverse(self):
        """
        Return all keys in sorted order.

        This performs an in-order traversal of the tree.
        """
        result = []

        self._traverse(
            self.root,
            result
        )

        return result

    def _traverse(self, node, result):
        """
        Recursively collect keys in sorted order.
        """
        for index, key in enumerate(node.keys):

            if not node.leaf:
                self._traverse(
                    node.children[index],
                    result
                )

            result.append(key)

        if not node.leaf:
            self._traverse(
                node.children[-1],
                result
            )