from pydb.btree import BTree


def test_empty_btree():
    """
    Verify that a newly created B-Tree is empty.
    """
    tree = BTree()

    assert tree.traverse() == []


def test_insert_and_search():
    """
    Verify that inserted keys can be found.
    """
    tree = BTree()

    tree.insert(10)
    tree.insert(20)
    tree.insert(5)

    assert tree.search(10) is True
    assert tree.search(20) is True
    assert tree.search(5) is True


def test_search_missing_key():
    """
    Verify that searching for a missing key returns False.
    """
    tree = BTree()

    tree.insert(10)
    tree.insert(20)

    assert tree.search(15) is False


def test_traversal_is_sorted():
    """
    Verify that B-Tree traversal returns keys in sorted order.
    """
    tree = BTree()

    for key in [30, 10, 40, 20, 5, 25, 35]:
        tree.insert(key)

    assert tree.traverse() == [
        5,
        10,
        20,
        25,
        30,
        35,
        40,
    ]


def test_duplicate_keys_are_ignored():
    """
    Verify that inserting the same key multiple times
    does not create duplicate keys.
    """
    tree = BTree()

    tree.insert(10)
    tree.insert(10)
    tree.insert(10)

    assert tree.traverse() == [10]


def test_root_split():
    """
    Verify that inserting enough keys causes the root
    to split while preserving sorted traversal.
    """
    tree = BTree(minimum_degree=2)

    for key in [10, 20, 30, 40]:
        tree.insert(key)

    assert tree.traverse() == [
        10,
        20,
        30,
        40,
    ]

    # The root should no longer be a leaf after splitting.
    assert tree.root.leaf is False

    # The root should contain the promoted middle key.
    assert tree.root.keys == [20]


def test_multiple_splits():
    """
    Verify that the tree remains correct after enough
    insertions to create multiple levels.
    """
    tree = BTree(minimum_degree=2)

    values = [
        50,
        20,
        70,
        10,
        30,
        60,
        80,
        5,
        15,
        25,
        35,
        55,
        65,
        75,
        85,
    ]

    for value in values:
        tree.insert(value)

    assert tree.traverse() == sorted(values)

    for value in values:
        assert tree.search(value) is True

def test_btree_node_key_limits():
    """
    Verify that every node respects the B-Tree maximum
    key limit after many insertions.
    """
    tree = BTree(minimum_degree=2)

    for value in range(100):
        tree.insert(value)

    def check_node(node):
        # A B-Tree node with minimum degree t can contain
        # at most 2t - 1 keys.
        assert len(node.keys) <= 3

        # Keys inside every node must remain sorted.
        assert node.keys == sorted(node.keys)

        if node.leaf:
            # Leaf nodes must not have children.
            assert node.children == []

            return

        # An internal node must have one more child
        # than the number of keys.
        assert len(node.children) == len(node.keys) + 1

        for child in node.children:
            check_node(child)

    check_node(tree.root)


def test_btree_search_after_many_insertions():
    """
    Verify that every inserted key remains searchable
    after the tree grows through multiple splits.
    """
    tree = BTree(minimum_degree=2)

    values = list(range(200))

    for value in values:
        tree.insert(value)

    for value in values:
        assert tree.search(value) is True

    assert tree.search(-1) is False
    assert tree.search(200) is False


def test_btree_leaves_have_same_depth():
    """
    Verify the fundamental B-Tree property that all leaves
    exist at the same depth.
    """
    tree = BTree(minimum_degree=2)

    for value in range(100):
        tree.insert(value)

    leaf_depths = []

    def collect_leaf_depths(node, depth):
        if node.leaf:
            leaf_depths.append(depth)
            return

        for child in node.children:
            collect_leaf_depths(child, depth + 1)

    collect_leaf_depths(tree.root, 0)

    # Every leaf must be at exactly the same depth.
    assert len(set(leaf_depths)) == 1


def test_btree_internal_keys_partition_children():
    """
    Verify that the keys in internal nodes correctly divide
    the key ranges represented by their children.
    """
    tree = BTree(minimum_degree=2)

    for value in range(100):
        tree.insert(value)

    def check_node(node):
        if node.leaf:
            return

        assert len(node.children) == len(node.keys) + 1

        for index, child in enumerate(node.children):
            child_values = child.keys

            if not child_values:
                continue

            # Left child must contain values smaller than
            # the separator key.
            if index < len(node.keys):
                assert max(child_values) < node.keys[index]

            # Right child must contain values greater than
            # the separator key.
            if index > 0:
                assert min(child_values) > node.keys[index - 1]

            check_node(child)

    check_node(tree.root)