
# PyDB — Time Machine

> **A database that lets you experiment with its history, branches, and query behavior.**

PyDB is a SQL-like relational database engine built from scratch in Python.

The project started as a learning-focused implementation of database internals and evolved into **PyDB Time Machine**, a version-controlled database system where database mutations create immutable historical versions that can be explored, compared, replayed, branched, and merged.

The goal is not to replace PostgreSQL, MySQL, or SQLite.

The goal is to understand how a database actually works — and then explore what happens when **database history itself becomes a first-class concept**.

---

# 📌 Table of Contents

- [What is PyDB?](#-what-is-pydb)
- [Why I Built It](#-why-i-built-it)
- [Core Idea](#-core-idea)
- [Project Evolution](#-project-evolution)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Running PyDB](#-running-pydb)
- [SQL Support](#-sql-support)
- [Transactions](#-transactions)
- [Indexes](#-indexes)
- [Query Planning](#-query-planning)
- [Persistence](#-persistence)
- [Time Machine](#-time-machine)
- [Version History](#-version-history)
- [Branches](#-branches)
- [Checkout](#-checkout)
- [Diff](#-diff)
- [Replay](#-replay)
- [Compare](#-compare)
- [What-If Analysis](#-what-if-analysis)
- [Merge](#-merge)
- [Conflict Detection](#-conflict-detection)
- [History Model](#-history-model)
- [Design Decisions](#-design-decisions)
- [Testing](#-testing)
- [Known Limitations](#-known-limitations)
- [Future Direction](#-future-direction)
- [What I Learned](#-what-i-learned)
- [Interview Explanation](#-interview-explanation)
- [Example Session](#-example-session)
- [Author](#-author)

---

# 🗄️ What is PyDB?

PyDB is a lightweight relational database engine written in Python.

Instead of using an existing database engine internally, PyDB implements its own components for:

- SQL lexical analysis
- SQL parsing
- query representation
- query execution
- tables
- records
- constraints
- indexes
- persistence
- transactions
- query planning
- version history
- branching
- historical comparison
- replay
- merge and conflict detection

The project is designed to make database internals understandable by building the system from the ground up.

---

# 🎯 Why I Built It

Most applications use databases as a black box.

You write:

```sql
SELECT * FROM users WHERE age > 20;

and the database gives you a result.

But what actually happens internally?

How is the SQL understood?

How is the query represented?

How does the engine decide whether to scan every row or use an index?

How are rows stored?

How are constraints enforced?

How are changes persisted?

How do transactions work?

What happens when the database state changes over time?

PyDB was created to answer those questions through implementation instead of only theory.

🧠 Core Idea

The project has two major phases.

V1 — Understand how a database works

The first version focused on building a small relational database engine.

SQL
 ↓
Lexer
 ↓
Parser
 ↓
Query Object
 ↓
QueryExecutor
 ↓
Table / Database
 ↓
StorageEngine

This phase focuses on the internal mechanics of database systems.

V2 — Understand how a database evolves

The second version introduced the Time Machine concept.

Instead of only storing the current state:

Database
   ↓
Current State

PyDB stores historical states:

Version 0
   ↓
Version 1
   ↓
Version 2
   ↓
Version 3

And branches allow different database histories to evolve independently:

                 Version 2
                    │
             ┌──────┴──────┐
             ↓             ↓
        Version 3       Version 4
        experiment         main
             │             │
             └──────┬──────┘
                    ↓
                 Version 5
                  MERGE

This turns PyDB into something closer to a combination of:

Database Engine
       +
Version Control Concepts
       +
Query Analysis
🚀 Project Evolution
PyDB V1

The initial system implemented a SQL-like relational database.

It started with basic functionality and gradually gained:

CREATE TABLE
DROP TABLE
INSERT
SELECT
UPDATE
DELETE
WHERE conditions
AND / OR
BETWEEN
IN
LIKE
ORDER BY
LIMIT
GROUP BY
HAVING
aggregate functions
aliases
NULL
DEFAULT
PRIMARY KEY
UNIQUE
NOT NULL
persistence
indexes
transactions
query planning
CLI commands
PyDB V2 — Time Machine

The project was extended with historical database state management.

New capabilities include:

immutable versions
version history
branches
checkout
diff
replay
historical query comparison
hypothetical index analysis
three-way merge
merge conflict detection
DAG-based version history
merge persistence
branch persistence
✨ Features
SQL Engine

PyDB supports a practical SQL-like syntax including:

CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT,
    salary FLOAT,
    active BOOL DEFAULT TRUE
);

Insert data:

INSERT INTO users VALUES
(1, 'Aditya', 22, 70000.0, TRUE);

Column-list inserts:

INSERT INTO users (name, age)
VALUES ('Rahul', 24);

Select:

SELECT * FROM users;

Conditional queries:

SELECT * FROM users
WHERE age > 20;

Multiple conditions:

SELECT * FROM users
WHERE age > 20 AND salary > 50000;

Update:

UPDATE users
SET salary = 80000
WHERE id = 1;

Delete:

DELETE FROM users
WHERE id = 1;
🔍 Query Features

PyDB supports:

Comparison Operators
=
!=
<
>
<=
>=
Logical Operators
AND
OR
Range Conditions
SELECT * FROM users
WHERE age BETWEEN 20 AND 30;
IN
SELECT * FROM users
WHERE age IN (20, 21, 22, 23);
LIKE
SELECT * FROM users
WHERE name LIKE 'Adi%';
ORDER BY
SELECT * FROM users
ORDER BY salary DESC;
LIMIT
SELECT * FROM users
LIMIT 10;
GROUP BY
SELECT age, COUNT(*)
FROM users
GROUP BY age;
HAVING
SELECT age, COUNT(*)
FROM users
GROUP BY age
HAVING COUNT(*) > 1;
📊 Aggregate Functions

Supported aggregate functions include:

COUNT
SUM
AVG
MIN
MAX

Example:

SELECT COUNT(*)
FROM users;

Another example:

SELECT age, COUNT(*)
FROM users
GROUP BY age;
🧩 NULL Support

PyDB supports SQL-style NULL values.

Example:

INSERT INTO users VALUES
(1, 'Aditya', NULL, 70000.0, TRUE);

NULL can be used with supported table operations while constraints such as NOT NULL and PRIMARY KEY enforce their respective rules.

🔐 Constraints

PyDB supports:

PRIMARY KEY
UNIQUE
NOT NULL
DEFAULT

Example:

CREATE TABLE users (
    id INT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    active BOOL DEFAULT TRUE
);

Primary key rules include:

duplicate primary keys are rejected
NULL primary keys are rejected
primary key metadata is persisted
💾 Persistence

PyDB persists its database state to disk.

The persisted state includes information such as:

tables
schema
rows
record IDs
next record ID
indexes
index definitions
version history
branches
current branch
version relationships

The database can therefore be closed and restarted without losing its persisted state.

🔁 Transactions

PyDB supports:

BEGIN;

Perform multiple operations:

INSERT INTO users VALUES (1, 'Aditya', 22);

UPDATE users
SET age = 23
WHERE id = 1;

Commit:

COMMIT;

Or rollback:

ROLLBACK;

Transactions are atomic from the database state perspective.

A transaction does not create a separate historical version for every individual statement.

Instead, the successful transaction is represented as a single:

TRANSACTION COMMIT

version.

🌳 Indexes

PyDB supports multiple index concepts.

Hash Index

Hash indexes are useful for equality lookups.

Example:

CREATE INDEX user_id_idx
ON users(id)
USING HASH;

The underlying structure maps:

value → set(record_ids)

For example:

22 → {1, 4, 8}
23 → {2, 5}

This allows equality lookups without scanning the complete table.

🌲 B+Tree Index

PyDB also supports B+Tree based indexing.

Example:

CREATE INDEX salary_idx
ON users(salary)
USING BTREE;

B+Tree indexing is useful for:

equality queries
range queries
ordered access

For example:

SELECT *
FROM users
WHERE salary > 50000;

can potentially use a B+Tree range lookup rather than scanning every row.

🧠 Query Planning

PyDB contains basic access-path planning.

Possible access paths include:

HASH_INDEX
BTREE_INDEX
BTREE_RANGE
FULL_SCAN

For example:

SELECT *
FROM users
WHERE id = 10;

may be executed using:

HASH_INDEX

while:

SELECT *
FROM users
WHERE salary > 50000;

may use:

BTREE_RANGE

when a suitable B+Tree index exists.

The purpose is to demonstrate the relationship between:

Query
 ↓
Condition
 ↓
Available Index
 ↓
Access Path
 ↓
Execution
📈 EXPLAIN

PyDB provides query-plan inspection.

Example:

.explain SELECT * FROM users WHERE salary > 50000;

The planner can report information such as:

Access path
Estimated/actual rows
Condition evaluations
Index usage
📊 STATS

PyDB also supports query statistics.

Example:

.stats SELECT * FROM users WHERE salary > 50000;

This allows query behavior to be inspected rather than only observing the final output.

⏳ Time Machine

The defining V2 feature is the Time Machine.

A normal database mainly exposes:

Current State

PyDB additionally exposes:

Historical State

This makes database evolution inspectable.

The CLI provides commands such as:

.history
.branches
.checkout <version>
.diff <v1> <v2>
.replay <version>
.compare <v1> <v2> <SELECT>
.whatif <CREATE INDEX>; <SELECT>
.create_branch <name>
.use <branch>
.merge <branch>
🕒 Version History

Every normal database mutation executed through the database SQL path creates a new version.

For example:

CREATE TABLE users (...);

creates a version.

Then:

INSERT INTO users VALUES (...);

creates another version.

The history might look like:

+---------+--------+--------+--------------------------+
| version | parent | branch | operation                |
+---------+--------+--------+--------------------------+
| 0       | -      | main   | INITIAL                  |
| 1       | 0      | main   | CREATE TABLE users       |
| 2       | 1      | main   | INSERT INTO users        |
| 3       | 2      | main   | UPDATE users             |
+---------+--------+--------+--------------------------+

Each version contains the historical database state associated with that point in time.

🧬 Immutable Historical State

Historical versions are treated as immutable.

When a version is created, its database state is deep-copied.

This is important because otherwise a future mutation could accidentally modify the state of an old version.

Conceptually:

Version 1
   ↓
Immutable Snapshot

Version 2
   ↓
Immutable Snapshot

Version 3
   ↓
Immutable Snapshot

Later changes therefore do not rewrite history.

🌿 Branches

Branches allow independent database histories.

Create a branch:

.create_branch experiment

List branches:

.branches

Example:

* main
  experiment
  conflict

The * indicates the current branch.

Switch branches:

.use experiment

The database state changes to the head state of the selected branch.

🌱 Creating a Branch

Suppose the main branch has:

Version 0
   ↓
Version 1
   ↓
Version 2

Create an experiment branch from Version 2:

main
 |
 V2
 ├───────────────┐
 ↓               ↓
V3              E3
main         experiment

Now each branch can evolve independently.

🔀 Checkout

Checkout allows moving the active database state to a historical version.

Example:

.checkout 2

This restores the database state stored at Version 2.

Checkout does not rewrite history.

It simply changes which historical state is currently active.

📝 Diff

PyDB can compare two historical versions.

Example:

.diff 2 5

The diff engine can detect:

tables added
tables removed
schema changes
index changes
rows added
rows removed
rows updated
🧠 Logical Row Identity

A major design challenge in branching and merging is understanding what a row actually represents.

PyDB assigns stable internal Record IDs.

These IDs are not exposed as ordinary user-visible SQL columns.

They are used internally to identify logical rows across historical states.

For example:

Record ID 1

might correspond to:

[1, 'Aditya', 22]

If that row changes later:

[1, 'Aditya', 23]

the internal identity can still be preserved.

This becomes important when comparing branches.

🔁 Replay

Replay re-executes the SQL operation associated with a historical version.

Example:

.replay 4

If Version 4 represents:

INSERT INTO users VALUES (3, 'Neha', 21);

the operation can be executed again against the current state.

Replay creates a new version because the SQL is executed again normally.

Replay is therefore not the same thing as restoring a version.

Restore
.checkout 4

means:

Restore the historical state that already existed.

Replay
.replay 4

means:

Execute the historical SQL operation again.

This distinction is intentional.

⚖️ Compare Historical Query Behavior

A database can have the same query but a completely different state at different points in history.

PyDB therefore supports:

.compare <version1> <version2> <SELECT>

Example:

.compare 2 5 SELECT * FROM users WHERE salary > 50000;

The query is executed against two historical database states.

The comparison can show:

QUERY COMPARISON
--------------------------------

Query:
SELECT * FROM users WHERE salary > 50000;

Version 2
  Access path: FULL_SCAN
  Rows returned: 2
  Condition evaluations: 10

Version 5
  Access path: BTREE_RANGE
  Rows returned: 2
  Condition evaluations: 2

Result: IDENTICAL
Access path: CHANGED

This demonstrates that the result can remain the same while the execution strategy changes.

🧪 What-If Analysis

PyDB provides hypothetical query analysis.

Example:

.whatif CREATE INDEX salary_idx ON users(salary) USING BTREE; SELECT * FROM users WHERE salary > 50000;

Conceptually:

Current database
      |
      +----------------------+
      |                      |
Current state        Hypothetical state
                     + index
      |                      |
      ↓                      ↓
Execute query          Execute query
      |                      |
      ↓                      ↓
Compare behavior

The hypothetical index is applied only to a temporary copy of the table.

The real database is not changed.

The real history is not changed.

No permanent index is created.

This allows questions such as:

“What would happen to this query if I created an index?”

without actually modifying the database.

🔀 Merge

PyDB supports merging one branch into another.

Example:

.merge experiment

The current branch acts as the target branch.

The source branch is:

experiment

The merge operation performs a three-way merge using:

Common Ancestor
      / \
     /   \
 Target  Source

The resulting state is then constructed from those three states.

🧬 Three-Way Merge

Suppose the history is:

            Base
             |
        +----+----+
        |         |
     Target      Source

The merge process asks:

What existed in the common ancestor?
What changed in the target branch?
What changed in the source branch?
Can those changes be combined safely?

This avoids treating two independently evolved branches as simple snapshots.

⚔️ Merge Conflicts

A merge can detect conflicts such as:

row_conflict
schema_conflict
index_conflict
table_add_conflict
table_delete_conflict
constraint_conflict

For example:

Base:
[1, 'Aditya']

Target:
[1, 'Main']

Source:
[1, 'Experiment']

Both branches changed the same logical row differently.

The merge cannot automatically choose between:

Main

and:

Experiment

so the result is reported as a conflict.

🧱 Merge Atomicity

Merge operations are designed to be atomic.

If a conflict occurs:

Database state
      ↓
unchanged

History
      ↓
unchanged

Branch heads
      ↓
unchanged

Current version
      ↓
unchanged

No partial merge is applied.

This is important because a failed merge should not corrupt either branch.

🧬 Merge Commits

A successful merge produces a version with two parents.

For example:

        Version 2
        /      \
       /        \
     V3          V4
      \          /
       \        /
        \      /
        Version 5
          MERGE

Version 5 contains:

parent_version_id = Version 3
merge_parent_version_id = Version 4

This means the history is no longer just a simple linear chain.

🌐 Version History as a DAG

Because merge commits have multiple parents, PyDB represents version history as a Directed Acyclic Graph.

Example:

             V0
              |
             V1
              |
             V2
            /  \
           /    \
         V3      V4
          \      /
           \    /
            V5
           MERGE

This model allows the history manager to answer questions such as:

What is the ancestor of a version?
Are two versions related?
What is their common ancestor?
Is one branch already merged?
What changes happened independently on each branch?
🔍 Common Ancestor Detection

During merge and diff operations, PyDB determines a common ancestor between two versions.

The ancestry traversal considers both:

parent_version_id

and:

merge_parent_version_id

This allows ancestry traversal to work correctly even after multiple merges.

💡 Important Design Distinction

PyDB versions database mutations, not SELECT queries.

For example:

INSERT INTO users VALUES (...);

can create a historical version.

But:

SELECT * FROM users;

does not create a version.

This keeps the version history focused on state-changing operations.

Queries can instead be evaluated against historical versions using:

.compare

or:

.whatif
🖥️ CLI

PyDB provides an interactive command-line interface.

Start it with:

python3 -m pydb.cli

The CLI supports normal SQL and meta commands.

🧰 CLI Commands
Help
.help
List tables
.tables
Show schema
.schema
Show indexes
.indexes
Show history
.history
Show branches
.branches
Create branch
.create_branch experiment
Switch branch
.use experiment
Checkout version
.checkout 5
Diff versions
.diff 2 5
Replay version
.replay 4
Compare historical query behavior
.compare 2 5 SELECT * FROM users WHERE salary > 50000;
What-if analysis
.whatif CREATE INDEX salary_idx ON users(salary) USING BTREE; SELECT * FROM users WHERE salary > 50000;
Explain query
.explain SELECT * FROM users WHERE id = 1;
Query statistics
.stats SELECT * FROM users WHERE id = 1;
Exit
.exit

or:

.quit
🏗️ Architecture

The high-level architecture is:

                SQL
                 │
                 ▼
              Lexer
                 │
                 ▼
              Parser
                 │
                 ▼
           Query Objects
                 │
                 ▼
          Query Executor
                 │
          ┌──────┴──────┐
          │             │
          ▼             ▼
        Table        Database
          │             │
          │             ▼
          │       History Manager
          │             │
          ▼             ▼
       Indexes       Versions
          │             │
          │             ▼
          │          Branches
          │             │
          │             ▼
          │            DAG
          │
          ▼
    Storage / Persistence
🧩 Component Responsibilities
Lexer

Converts SQL text into tokens.

For example:

SELECT * FROM users WHERE age > 20;

becomes a token stream representing:

SELECT
*
FROM
users
WHERE
age
>
20
Parser

Converts tokens into structured query objects.

For example:

SELECT * FROM users WHERE age > 20;

may become an internal representation similar to:

SelectQuery(
    table='users',
    columns=['*'],
    condition=...
)
Query Objects

Query objects provide a structured representation independent of raw SQL text.

This separates:

SQL syntax

from:

Execution logic
Query Executor

Executes parsed query objects against:

tables
indexes
conditions
grouping
ordering
limits
constraints
Table

The table manages:

rows
record IDs
columns
constraints
indexes
index synchronization
serialization
Database

The database manages:

tables
SQL execution
transactions
persistence
query planning
Time Machine history
branch management
checkout
diff
replay
compare
what-if analysis
merge
History Manager

The History Manager manages:

versions
version relationships
branch heads
current branch
current version
historical state persistence
📁 Project Structure

The architecture is intentionally kept modular.

A simplified representation is:

PyDB/
│
├── pydb/
│   ├── cli.py
│   ├── database.py
│   ├── table.py
│   ├── column.py
│   ├── condition.py
│   ├── lexer.py
│   ├── parser.py
│   ├── executor.py
│   ├── query.py
│   ├── storage.py
│   ├── index.py
│   ├── btree.py
│   ├── bplus_tree.py
│   ├── version.py
│   └── ...
│
├── tests/
│   ├── test_column.py
│   ├── test_condition.py
│   ├── test_database.py
│   ├── test_executor.py
│   ├── test_table.py
│   ├── test_history_immutability.py
│   ├── test_database_merge.py
│   ├── test_merge_edge_cases.py
│   ├── test_version_dag.py
│   ├── test_branch_immutability.py
│   ├── test_dag_persistence.py
│   ├── test_merge_idempotency.py
│   ├── test_merge_conflicts.py
│   ├── test_merge_transactions.py
│   ├── test_merge_atomicity.py
│   └── ...
│
├── pydb.json
├── README.md
└── ...
⚙️ Installation

Clone the repository:

git clone <your-repository-url>

Move into the project:

cd PyDB

Create a virtual environment:

python3 -m venv .venv

Activate it:

macOS / Linux
source .venv/bin/activate

Install test dependencies:

pip install pytest
▶️ Running PyDB

Start the CLI:

python3 -m pydb.cli

You should get an interactive shell where you can run SQL.

Example:

PyDB> CREATE TABLE users (
... id INT PRIMARY KEY,
... name TEXT,
... age INT
... );

PyDB> INSERT INTO users VALUES (1, 'Aditya', 22);

PyDB> SELECT * FROM users;
🧪 Testing

PyDB has an extensive automated test suite built with pytest.

Run the complete suite:

pytest

Run a specific test:

pytest tests/test_database.py

Run a focused test file:

pytest tests/test_database_merge.py

Run with more detailed output:

pytest -v

The test suite covers areas including:

Columns
Conditions
Tables
Database operations
SQL parsing
Lexer behavior
Query execution
Constraints
NULL
Persistence
Indexes
B+Trees
Transactions
Query planning
History
Branches
Checkout
Diff
Replay
Compare
What-if analysis
Merge
Merge conflicts
DAG ancestry
Persistence after merge
Historical immutability
Atomicity
🧪 Why Testing Matters Here

A database engine is heavily stateful.

A change in one area can affect many other areas.

For example:

INSERT
  ↓
Table state changes
  ↓
Index changes
  ↓
Persistence changes
  ↓
History changes
  ↓
Branch state changes
  ↓
Future merge behavior changes

Therefore, the test suite is designed to verify both:

individual components

and:

system-level interactions
🧠 Design Decisions
Why Python?

Python was chosen because it makes rapid implementation and experimentation easy.

The objective was to spend more time understanding:

parsing
data structures
indexing
transactions
persistence
historical state
merge algorithms

rather than spending excessive time fighting language complexity.

🔢 Why Stable Internal Record IDs?

Physical list positions are not reliable identities.

For example:

Row 0
Row 1
Row 2

can change after deletions or reordering.

A stable internal Record ID gives the system a logical identity:

Record 1
Record 2
Record 3

This becomes particularly important for:

diff
branching
merge
historical comparison
🌲 Why Hash Index + B+Tree?

Different queries benefit from different data structures.

Hash index:

Equality lookup

B+Tree:

Equality
Range
Ordered traversal

This gives the query planner multiple access paths to choose from.

🧬 Why Full Historical Snapshots?

Snapshots make the Time Machine behavior easy to reason about.

Each version has a self-contained logical database state.

The trade-off is storage efficiency.

A production system would usually use more advanced mechanisms such as:

write-ahead logging
checkpoints
page-level storage
copy-on-write pages
MVCC
incremental snapshots

PyDB intentionally prioritizes understandable architecture over production-level storage optimization.

🔀 Why a DAG Instead of a Simple Tree?

Without merges, version history can look like a tree:

V0
 |
 V1
 |
 V2

But after branches and merges:

       V2
      /  \
    V3    V4
      \  /
       V5

Version 5 has two parents.

Therefore, a DAG is the natural representation.

🔒 Historical Immutability

A historical version must not change because of future database operations.

Therefore, PyDB creates deep copies of serialized state when storing historical versions.

This establishes the invariant:

Past versions do not mutate.

That invariant is critical for:

checkout correctness
diff correctness
merge correctness
replay correctness
historical query comparison
🧱 Atomic Merge Design

Merge is intentionally implemented as:

Read history
    ↓
Build proposed result
    ↓
Detect conflicts
    ↓
Validate constraints
    ↓
Apply only if successful
    ↓
Create merge version

Not:

Modify target
    ↓
Detect conflict halfway
    ↓
Leave database partially changed

This ensures merge failure does not corrupt state.

⚠️ Known Limitations

PyDB is a learning and systems-design project, not a production database.

It intentionally does not attempt to provide everything that a mature database engine provides.

Current limitations include:

no WAL-based crash recovery
no buffer pool
no page-oriented disk storage engine
no MVCC
no row-level locking
no sophisticated concurrent transaction system
no distributed replication
no sharding
no production-grade cost-based optimizer
limited SQL compatibility
limited SQL type system
no production-grade query planner
B+Tree deletion is not fully optimized
historical snapshots consume more storage than an incremental system
SELECT comparison currently has restrictions around aggregates and GROUP BY
transaction commit history stores the commit as one historical event rather than replayable per-statement history

These limitations are intentional boundaries of the project.

🛣️ Future Direction

Potential future directions include:

Storage Engine Improvements
Page-based storage
Buffer pool
WAL
Crash recovery
Copy-on-write snapshots
Query Engine Improvements
Cost-based optimizer
More indexes
Better statistics
Join algorithms
Subqueries
More SQL compatibility
Concurrency
Lock manager
MVCC
Concurrent transactions
Isolation levels
Time Machine Improvements
Storage-efficient snapshots
Fine-grained history
Better historical query visualization
Interactive conflict resolution
More powerful replay
Branch-aware query experimentation
🌟 Why the Time Machine Is Interesting

The project is not claiming to invent versioned databases.

The interesting part of PyDB is the way database internals and version-control concepts are combined into one small system.

Traditional database thinking often looks like:

Query
 ↓
Execution
 ↓
Result

PyDB V2 adds another dimension:

Query
 ↓
Execution
 ↓
Result
 ↓
Historical Context

This allows questions such as:

What did the database look like here?

How did this query behave before the index existed?

What happens if this branch is replayed?

What changes between these two versions?

What would happen if this index existed?

Can these two database histories be merged?

Where did the conflict come from?

The project therefore treats database evolution as something that can be inspected and experimented with.

🎓 What I Learned

Building PyDB required working across multiple layers of computer science.

Programming
Python architecture
Object-oriented design
Data structures
Serialization
Testing
Compiler Concepts
Lexing
Parsing
Abstract query representation
Database Concepts
Relations
Constraints
Transactions
Persistence
Indexes
Query planning
Data Structures
Hash tables
Trees
B+Trees
Sets
Graphs
Systems Design
State management
Immutability
Atomic operations
Persistence boundaries
Version Control Concepts
Branches
Ancestors
DAGs
Three-way merge
Conflict detection
💬 Interview Explanation

A concise way to explain PyDB in an interview:

PyDB is a SQL-like relational database engine I built from scratch in Python to understand database internals. V1 implements a lexer, parser, query objects, query execution, constraints, persistence, transactions, hash and B+Tree indexes, and basic query planning. In V2, I extended it into a version-controlled database called Time Machine, where every mutation creates an immutable historical state. I added branches, checkout, diff, replay, historical query comparison, hypothetical index analysis, and three-way merges with conflict detection. Because merge commits have two parents, the version history is represented as a DAG rather than a simple linear history.

🧠 How I Would Explain the Biggest Technical Challenge

One of the more interesting challenges was maintaining correct identity across historical states and branches.

A naive diff might compare:

row position 0

against:

row position 0

and assume they are the same logical row.

That fails after independent branch changes.

PyDB therefore uses stable internal Record IDs and combines that with common-ancestor analysis.

The merge process can then distinguish:

same logical row changed differently

from:

two unrelated rows created independently

This distinction is critical for correct branching and merging.

🧠 Could This Be Recreated From Scratch?

Yes.

The architecture is intentionally understandable.

A simplified recreation path would be:

1. Lexer
2. Parser
3. Query objects
4. Tables
5. Database
6. CRUD operations
7. Constraints
8. Persistence
9. Indexes
10. Transactions
11. Query planner
12. Version manager
13. Branches
14. Diff
15. Replay
16. Historical query comparison
17. What-if analysis
18. Three-way merge
19. Conflict detection
20. DAG persistence

The difficult part is not writing hundreds of lines of code blindly.

The difficult part is understanding the invariants between components.

For example:

Table
 ↕
Index
 ↕
Persistence
 ↕
History
 ↕
Branch
 ↕
Merge

A change in one layer must preserve the assumptions made by the others.

🧭 Learning Philosophy

PyDB was built around a simple idea:

Don't just use the abstraction. Build a smaller version of it.

Instead of only learning:

SQL

the project explores:

How SQL becomes executable operations.

Instead of only learning:

Indexes

the project explores:

How different data structures affect access paths.

Instead of only learning:

Transactions

the project explores:

How state transitions are controlled.

Instead of only learning:

Git branches

the project explores:

What branching and merging would look like when the thing being versioned is database state.
🧪 Example Session

A basic session could look like:

PyDB> CREATE TABLE users (
... id INT PRIMARY KEY,
... name TEXT,
... age INT,
... salary FLOAT
... );

Table 'users' created.

PyDB> INSERT INTO users VALUES
... (1, 'Aditya', 22, 70000),
... (2, 'Rahul', 24, 60000),
... (3, 'Neha', 21, 80000);

3 rows inserted.

PyDB> CREATE INDEX salary_idx
... ON users(salary)
... USING BTREE;

Index 'salary_idx' created.

PyDB> SELECT * FROM users
... WHERE salary > 65000;

+----+--------+-----+--------+
| id | name   | age | salary |
+----+--------+-----+--------+
| 1  | Aditya | 22  | 70000  |
| 3  | Neha   | 21  | 80000  |
+----+--------+-----+--------+

PyDB> .history

+---------+--------+--------+------------------------+
| version | parent | branch | operation              |
+---------+--------+--------+------------------------+
| 0       | -      | main   | INITIAL                |
| 1       | 0      | main   | CREATE TABLE users     |
| 2       | 1      | main   | INSERT INTO users      |
| 3       | 2      | main   | CREATE INDEX salary_idx|
+---------+--------+--------+------------------------+

PyDB> .create_branch experiment

Branch 'experiment' created.

PyDB> .use experiment

Switched to branch 'experiment'.

PyDB> UPDATE users
... SET salary = 90000
... WHERE id = 1;

1 row updated.

PyDB> .history

PyDB> .use main

Switched to branch 'main'.

PyDB> .diff 3 4

Database differences found.

PyDB> .merge experiment

MERGE

Target branch : main
Source branch : experiment

Status: MERGED
🔬 Example of Historical Query Analysis

Suppose Version 2 did not have an index:

Version 2
Access path:
FULL_SCAN

Later Version 3 creates a B+Tree index:

Version 3
Access path:
BTREE_RANGE

The query:

SELECT *
FROM users
WHERE salary > 50000;

can then be compared:

.compare 2 3 SELECT * FROM users WHERE salary > 50000;

Possible result:

QUERY COMPARISON
--------------------------------

Version 2
  Access path: FULL_SCAN
  Rows returned: 3
  Condition evaluations: 100

Version 3
  Access path: BTREE_RANGE
  Rows returned: 3
  Condition evaluations: 20

Result: IDENTICAL
Access path: CHANGED

The data result is unchanged.

The execution strategy is different.

This is one of the ideas that makes the Time Machine layer useful beyond simple undo/redo functionality.

🧠 PyDB in One Sentence

PyDB is a from-scratch Python database engine extended with Git-like historical branching, query experimentation, and three-way merging of database state.

📌 Project Positioning

PyDB should be presented as:

A serious systems-learning project

rather than:

A production database replacement

The strongest part of the project is not SQL syntax alone.

It is the combination of:

Database Internals
        +
Indexes
        +
Transactions
        +
Query Planning
        +
Immutable History
        +
Branches
        +
Historical Query Analysis
        +
What-If Experiments
        +
Three-Way Merge
        +
Conflict Detection
        +
DAG Version History
🏆 What Makes It Different

The project began as:

"Let's build a small database."

but evolved into:

"Let's build a database whose evolution can itself be explored."

The Time Machine layer allows the user to treat database history as an experimental environment.

Instead of only asking:

What is the database now?

PyDB allows questions like:

What was the database then?

What changed?

Which branch introduced this state?

What would happen if an index existed?

How did query execution change?

Can two database histories be merged?

Why did the merge conflict?
📦 Current Scope
Database Engine
✅ SQL lexer
✅ SQL parser
✅ Query objects
✅ Query executor
✅ CREATE TABLE
✅ DROP TABLE
✅ INSERT
✅ SELECT
✅ UPDATE
✅ DELETE
✅ WHERE
✅ AND / OR
✅ BETWEEN
✅ IN
✅ LIKE
✅ ORDER BY
✅ LIMIT
✅ GROUP BY
✅ HAVING
✅ Aggregates
✅ Aliases
✅ NULL
✅ DEFAULT
✅ PRIMARY KEY
✅ UNIQUE
✅ NOT NULL
Storage & Performance
✅ JSON persistence
✅ Stable record IDs
✅ Hash indexes
✅ B+Tree indexes
✅ Index persistence
✅ Query planning
✅ EXPLAIN
✅ Query statistics
Transactions
✅ BEGIN
✅ COMMIT
✅ ROLLBACK
Time Machine
✅ Immutable versions
✅ Version history
✅ Branches
✅ Checkout
✅ Diff
✅ Replay
✅ Historical query comparison
✅ What-if index analysis
✅ Three-way merge
✅ Merge conflicts
✅ Merge DAG
✅ Merge persistence
✅ Branch persistence
✅ Merge atomicity
📈 Project Philosophy

The project follows this progression:

V1

Understand how a database works.

then:

V2

Understand how a database evolves.

And the broader idea is:

Don't just store data.

Understand the state of the system,
the history of the system,
and the consequences of changing the system.
👨‍💻 Author

Aditya Garg

Computer Science Engineering

Chitkara University

Python • Backend Development • Databases • Testing • Systems

📜 License


⭐ Final Note

PyDB is primarily a learning-driven systems project.

It is an attempt to move from:

using software

to:

understanding software

and eventually to:

designing software.

The project intentionally favors understandable implementations over production-level complexity, while still exploring real concepts such as parsing, indexing, transactions, persistence, query planning, immutable state, DAGs, branching, and three-way merging.

PyDB Time Machine — understand not only what the database is, but how it became what it is.