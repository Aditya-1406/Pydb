from pydb.bplus_tree import BPlusTree


def test_empty_bplus_tree():
    """
    Verify that a newly created B+Tree is empty.
    """
    tree = BPlusTree()

    assert tree.items() == []


def test_insert_and_search():
    """
    Verify that inserted key/value pairs can be found.
    """
    tree = BPlusTree()

    tree.insert(10, "ten")
    tree.insert(20, "twenty")
    tree.insert(5, "five")

    assert tree.search(10) == "ten"
    assert tree.search(20) == "twenty"
    assert tree.search(5) == "five"


def test_missing_key_returns_none():
    """
    Verify that searching for a missing key returns None.
    """
    tree = BPlusTree()

    tree.insert(10, "ten")

    assert tree.search(99) is None


def test_items_are_sorted():
    """
    Verify that items are returned in sorted key order.
    """
    tree = BPlusTree()

    values = {
        30: "thirty",
        10: "ten",
        50: "fifty",
        20: "twenty",
        40: "forty",
    }

    for key, value in values.items():
        tree.insert(key, value)

    assert tree.items() == [
        (10, "ten"),
        (20, "twenty"),
        (30, "thirty"),
        (40, "forty"),
        (50, "fifty"),
    ]


def test_existing_key_is_updated():
    """
    Verify that inserting an existing key replaces
    its associated value.
    """
    tree = BPlusTree()

    tree.insert(10, "old")
    tree.insert(10, "new")

    assert tree.search(10) == "new"

    assert tree.items() == [
        (10, "new")
    ]


def test_leaf_split():
    """
    Verify that inserting enough keys causes a leaf
    node to split.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in [10, 20, 30, 40]:
        tree.insert(key, str(key))

    assert tree.root.leaf is False

    assert tree.items() == [
        (10, "10"),
        (20, "20"),
        (30, "30"),
        (40, "40"),
    ]


def test_range_search():
    """
    Verify that the B+Tree can efficiently traverse
    the linked leaves for a range query.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(1, 11):
        tree.insert(key, str(key))

    assert tree.range_search(
        3,
        7
    ) == [
        (3, "3"),
        (4, "4"),
        (5, "5"),
        (6, "6"),
        (7, "7"),
    ]


def test_open_ended_range_search():
    """
    Verify ranges with only one boundary.
    """
    tree = BPlusTree()

    for key in range(1, 11):
        tree.insert(key, str(key))

    assert tree.range_search(
        lower=8
    ) == [
        (8, "8"),
        (9, "9"),
        (10, "10"),
    ]

    assert tree.range_search(
        upper=3
    ) == [
        (1, "1"),
        (2, "2"),
        (3, "3"),
    ]


def test_invalid_range_returns_empty():
    """
    Verify that a range whose lower bound is greater
    than its upper bound returns no results.
    """
    tree = BPlusTree()

    for key in range(1, 6):
        tree.insert(key, str(key))

    assert tree.range_search(
        5,
        2
    ) == []


def test_leaf_nodes_are_linked():
    """
    Verify that leaf nodes form a linked list from
    left to right.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(1, 11):
        tree.insert(key, str(key))

    leaf = tree.root

    while not leaf.leaf:
        leaf = leaf.children[0]

    collected_keys = []

    while leaf is not None:
        collected_keys.extend(leaf.keys)
        leaf = leaf.next_leaf

    assert collected_keys == list(range(1, 11))


def test_search_after_multiple_splits():
    """
    Verify that searching remains correct after
    the tree grows through multiple leaf and
    internal-node splits.
    """
    tree = BPlusTree(minimum_degree=2)

    values = list(range(100))

    for value in values:
        tree.insert(
            value,
            str(value)
        )

    for value in values:
        assert tree.search(value) == str(value)

    assert tree.search(1000) is None

def _collect_leaves(tree):
    """
    Return all leaf nodes from left to right.

    Uses the B+Tree's linked-leaf structure.
    """
    node = tree.root

    while not node.leaf:
        node = node.children[0]

    leaves = []

    while node is not None:
        leaves.append(node)
        node = node.next_leaf

    return leaves


def _get_leaf_depths(node, depth=0):
    """
    Recursively collect the depth of every leaf node.
    """
    if node.leaf:
        return [depth]

    depths = []

    for child in node.children:
        depths.extend(
            _get_leaf_depths(
                child,
                depth + 1
            )
        )

    return depths


def test_bplus_tree_node_key_limits():
    """
    Verify that no node contains more keys than
    the B+Tree maximum.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(100):
        tree.insert(key, str(key))

    maximum_keys = (
        2 * tree.minimum_degree - 1
    )

    def check_node(node):
        assert len(node.keys) <= maximum_keys

        if not node.leaf:
            for child in node.children:
                check_node(child)

    check_node(tree.root)


def test_bplus_tree_internal_children_match_keys():
    """
    An internal B+Tree node with N separator keys
    must have N + 1 children.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(100):
        tree.insert(key, str(key))

    def check_node(node):
        if node.leaf:
            return

        assert len(node.children) == (
            len(node.keys) + 1
        )

        for child in node.children:
            check_node(child)

    check_node(tree.root)


def test_bplus_tree_keys_are_sorted():
    """
    Verify that keys inside every node remain sorted.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(100):
        tree.insert(key, str(key))

    def check_node(node):
        assert node.keys == sorted(node.keys)

        if not node.leaf:
            for child in node.children:
                check_node(child)

    check_node(tree.root)


def test_bplus_tree_leaves_have_same_depth():
    """
    Verify the fundamental B+Tree property that
    every leaf exists at the same depth.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(200):
        tree.insert(key, str(key))

    depths = _get_leaf_depths(tree.root)

    assert len(set(depths)) == 1


def test_bplus_tree_leaf_links_are_sorted():
    """
    Verify that following next_leaf pointers produces
    globally sorted keys.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(200):
        tree.insert(key, str(key))

    leaves = _collect_leaves(tree)

    all_keys = []

    for leaf in leaves:
        all_keys.extend(leaf.keys)

    assert all_keys == list(range(200))


def test_bplus_tree_leaf_values_match_keys():
    """
    Verify that every leaf key has exactly one
    corresponding value.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(100):
        tree.insert(key, f"value-{key}")

    leaves = _collect_leaves(tree)

    for leaf in leaves:
        assert len(leaf.keys) == len(
            leaf.values
        )


def test_bplus_tree_range_search_matches_full_scan():
    """
    Verify range_search against the complete ordered
    contents of the tree.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(100):
        tree.insert(key, str(key))

    expected = [
        (key, str(key))
        for key in range(25, 76)
    ]

    assert tree.range_search(
        25,
        75
    ) == expected

def test_bplus_tree_internal_nodes_are_routing_only():
    """
    Verify that internal B+Tree nodes do not contain values.

    Actual key/value entries live in the leaf nodes.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(20):
        tree.insert(key, f"value-{key}")

    def check_node(node):
        if node.leaf:
            assert len(node.keys) == len(node.values)
            return

        # Internal nodes have routing keys only.
        assert node.values == []

        for child in node.children:
            check_node(child)

    check_node(tree.root)


def test_bplus_tree_all_entries_are_in_leaves():
    """
    Verify that every inserted key/value pair exists
    in a leaf node.
    """
    tree = BPlusTree(minimum_degree=2)

    expected = {
        key: f"value-{key}"
        for key in range(50)
    }

    for key, value in expected.items():
        tree.insert(key, value)

    actual = dict(tree.items())

    assert actual == expected


def test_bplus_tree_leaf_chain_contains_every_entry():
    """
    Verify that walking only through next_leaf pointers
    reaches every stored entry exactly once.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in range(50):
        tree.insert(key, f"value-{key}")

    leaf = tree.root

    while not leaf.leaf:
        leaf = leaf.children[0]

    entries = []

    while leaf is not None:
        entries.extend(
            zip(
                leaf.keys,
                leaf.values
            )
        )
        leaf = leaf.next_leaf

    assert entries == [
        (key, f"value-{key}")
        for key in range(50)
    ]


def test_bplus_tree_range_search_uses_ordered_leaf_data():
    """
    Verify that range results are ordered because the
    leaves themselves are ordered.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in [
        50, 10, 80, 30, 20,
        70, 40, 60, 90
    ]:
        tree.insert(key, f"value-{key}")

    assert tree.range_search(
        20,
        70
    ) == [
        (20, "value-20"),
        (30, "value-30"),
        (40, "value-40"),
        (50, "value-50"),
        (60, "value-60"),
        (70, "value-70"),
    ]


def test_bplus_tree_separator_keys_exist_in_right_leaf():
    """
    Verify an important B+Tree property:

    A separator promoted from a leaf is copied into
    the parent, while the actual entry remains in
    the right-hand leaf.
    """
    tree = BPlusTree(minimum_degree=2)

    for key in [10, 20, 30, 40]:
        tree.insert(key, f"value-{key}")

    assert tree.root.leaf is False

    separator = tree.root.keys[0]

    right_leaf = tree.root.children[1]

    assert separator == right_leaf.keys[0]

    assert tree.search(separator) == (
        f"value-{separator}"
    )