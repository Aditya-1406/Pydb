PyDB

A mini relational database engine built from scratch in core Python to understand how a database works internally.

PyDB is not intended to compete with PostgreSQL, MySQL, or SQLite. The goal is to explore the internal building blocks of a database system — from parsing SQL to executing queries, maintaining indexes, persisting data, and handling transactions.

Project Goal

The main purpose of PyDB is learning database internals by building them from scratch.

Instead of treating a database as a black box, PyDB breaks the system into understandable layers:

SQL
 ↓
Lexer
 ↓
Parser
 ↓
Query Objects
 ↓
Query Executor
 ↓
Table
 ↓
Indexes / Storage

This project demonstrates how a database can transform a SQL statement into actual operations on stored data.

Features
SQL Engine

PyDB supports:

CREATE TABLE
DROP TABLE
INSERT
SELECT
UPDATE
DELETE
Data Types

Currently supported:

INT
TEXT
FLOAT
BOOL
NULL

Boolean literals are supported through:

TRUE
FALSE
Constraints

PyDB supports:

PRIMARY KEY
NOT NULL
UNIQUE
DEFAULT

Example:

CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT,
    city TEXT DEFAULT 'Delhi',
    salary FLOAT,
    active BOOL DEFAULT TRUE
);
INSERT

Standard inserts:

INSERT INTO users
VALUES (1, 'Aditya', 22, 'Delhi', 75000.50, TRUE);

Column-list inserts:

INSERT INTO users (id, name, age)
VALUES (2, 'Rahul', 25);

Supports:

NULL
DEFAULT
Query Conditions

Supported:

=
!=
<
>
<=
>=
AND
OR
BETWEEN
LIKE
IN

Examples:

SELECT *
FROM users
WHERE age > 25;
SELECT *
FROM users
WHERE age BETWEEN 20 AND 30;
SELECT *
FROM users
WHERE city IN ('Delhi', 'Mumbai');
SELECT *
FROM users
WHERE name LIKE 'A%';
Ordering and Limiting
SELECT *
FROM users
ORDER BY salary DESC
LIMIT 5;

Supports:

ORDER BY
ASC
DESC
LIMIT
Aliases
SELECT
    name AS employee_name,
    salary AS income
FROM users
ORDER BY income DESC;

Aliases are also supported with aggregate expressions.

Aggregations

Supported:

COUNT
SUM
AVG
MIN
MAX

Example:

SELECT
    COUNT(*) AS total_users,
    AVG(age) AS average_age,
    MAX(salary) AS highest_salary
FROM users;
GROUP BY / HAVING
SELECT city, COUNT(*) AS total
FROM users
GROUP BY city
HAVING COUNT(*) > 1;
NULL Handling

PyDB explicitly handles SQL NULL.

Internally:

SQL NULL → Python None

Examples:

INSERT INTO users
VALUES (3, 'Priya', NULL, NULL, 60000, TRUE);

NULL values are also handled during:

comparisons
aggregation
ordering
persistence
updates
indexes

For example, COUNT(column) ignores NULL, while COUNT(*) counts the row.

Indexes

PyDB implements multiple index structures to explore how databases speed up query execution.

Hash Index

Hash indexes map values to internal Record IDs:

22 → {1, 4, 8}
25 → {2, 7}
30 → {3}

They are useful for equality lookups.

Create one using SQL:

CREATE INDEX age_idx
ON users(age);
B+Tree Index

PyDB also contains a B+Tree implementation with:

sorted keys
leaf nodes
linked leaves
insertion
node splitting
range search
duplicate-key support
tree invariant checks

Create one using SQL:

CREATE INDEX salary_idx
ON users(salary)
USING BTREE;

This enables range-oriented access such as:

SELECT *
FROM users
WHERE salary > 70000;
Index Management

Indexes can be created and removed through SQL:

CREATE INDEX age_idx
ON users(age);
CREATE INDEX salary_idx
ON users(salary)
USING BTREE;
DROP INDEX age_idx;

The CLI also provides:

.indexes users

to inspect indexes.

Query Planning

PyDB contains a lightweight query-planning layer.

For supported conditions, the planner can choose between:

FULL_SCAN
HASH INDEX
B+TREE INDEX

For example:

.explain SELECT * FROM users WHERE age = 25;

Execution statistics are also available:

.stats SELECT * FROM users WHERE age = 25;

Statistics include information such as:

access_path
table_rows
table_rows_visited
index_candidates
condition_evaluations
rows_matched

The purpose is educational: to make the difference between a full scan and indexed execution visible.

Stable Record IDs

Every row receives an internal Record ID.

Example:

Record ID 1 → Aditya
Record ID 2 → Rahul
Record ID 3 → Priya

Record IDs are separate from SQL table columns.

Important properties:

IDs are persisted.
Deleted IDs are not reused.
Indexes reference Record IDs rather than storing complete rows.

This mirrors an important database concept: separating the identity of a stored record from its user-visible data.

Transactions

PyDB supports basic transactions:

BEGIN;
COMMIT;
ROLLBACK;

Example:

BEGIN;

UPDATE users
SET salary = 999999
WHERE id = 1;

ROLLBACK;

The original state is restored.

Transactions currently cover changes to:

rows
tables
indexes
Record IDs
dirty-state information

The transaction implementation uses database snapshots to provide rollback behavior.

Persistence

PyDB persists its state to a JSON-based storage file.

Example:

pydb.json

The database stores:

tables
schema information
rows
constraints
Record IDs
index metadata
index-related state

When PyDB starts again, the stored database is reconstructed.

Command-Line Interface

PyDB includes an interactive CLI.

Start it with:

python3 -m pydb.cli

Example:

pydb> CREATE TABLE users (...);
Table 'users' created.

pydb> INSERT INTO users VALUES (...);
1 row inserted.

pydb> SELECT * FROM users;
+----+--------+-----+
| id | name   | age |
+----+--------+-----+
| 1  | Aditya | 22  |
+----+--------+-----+

CLI commands include:

.help
.tables
.schema users
.indexes users
.explain SELECT ...
.stats SELECT ...
.exit
.quit

The CLI also supports multiline SQL:

pydb> CREATE TABLE users (
...> id INT PRIMARY KEY,
...> name TEXT NOT NULL,
...> age INT
...> );
Project Structure
PyDB/
│
├── pydb/
│   ├── __init__.py
│   ├── lexer.py
│   ├── parser.py
│   ├── query.py
│   ├── condition.py
│   ├── column.py
│   ├── table.py
│   ├── database.py
│   ├── executor.py
│   ├── storage.py
│   ├── index.py
│   ├── btree.py
│   ├── bplus_tree.py
│   ├── bplus_index.py
│   └── cli.py
│
├── tests/
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_query.py
│   ├── test_condition.py
│   ├── test_column.py
│   ├── test_table.py
│   ├── test_database.py
│   ├── test_executor.py
│   ├── test_index.py
│   ├── test_btree.py
│   ├── test_bplus_tree.py
│   ├── test_bplus_index.py
│   ├── test_table_index.py
│   ├── test_indexed_select.py
│   ├── test_execution_stats.py
│   ├── test_transactions.py
│   ├── test_persistence.py
│   ├── test_indexes_sql.py
│   └── ...
│
├── pydb.json
└── README.md
Architecture

The core architecture is intentionally layered.

Lexer

Converts SQL text into tokens.

CREATE TABLE users ...
        ↓
KEYWORD / IDENTIFIER / SYMBOL / NUMBER / STRING
Parser

Converts tokens into structured Query Objects.

SQL
 ↓
Tokens
 ↓
Query Object

For example:

CREATE INDEX age_idx ON users(age)

becomes a CreateIndexQuery.

Query Objects

Represent operations without executing them.

Examples:

SelectQuery
InsertQuery
UpdateQuery
DeleteQuery
CreateTableQuery
CreateIndexQuery
DropIndexQuery
BeginQuery
CommitQuery
RollbackQuery
Query Executor

Takes Query Objects and performs the requested operations.

Query Object
     ↓
QueryExecutor
     ↓
Database / Table
Table

Responsible for:

schema
rows
constraints
Record IDs
indexes
query access
Storage Engine

Responsible for persisting database state.

Testing

PyDB has an extensive automated test suite covering:

lexer
parser
query objects
conditions
CRUD
constraints
NULL behavior
aggregates
GROUP BY / HAVING
aliases
ordering
indexes
B-Tree
B+Tree
query planning
execution statistics
Record IDs
persistence
transactions
CLI
SQL-level index management

Run the complete test suite:

python3 -m pytest -q

Current project status:

616 tests passing
0 failures
0 errors
Running PyDB

Clone the repository and enter the project:

cd PyDB

Create/activate a virtual environment:

python3 -m venv env
source env/bin/activate

Run tests:

python3 -m pytest -q

Start the database CLI:

python3 -m pydb.cli
Example Session
CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT,
    city TEXT DEFAULT 'Delhi',
    salary FLOAT,
    active BOOL DEFAULT TRUE
);

INSERT INTO users
VALUES (1, 'Aditya', 22, 'Delhi', 75000.50, TRUE);

INSERT INTO users
VALUES (2, 'Rahul', 25, 'Mumbai', 85000.00, FALSE);

INSERT INTO users
VALUES (3, 'Priya', 28, 'Delhi', 92000.75, TRUE);

CREATE INDEX age_idx
ON users(age);

CREATE INDEX salary_idx
ON users(salary)
USING BTREE;

SELECT name, salary
FROM users
WHERE age > 20
ORDER BY salary DESC
LIMIT 5;

SELECT city, COUNT(*) AS total
FROM users
GROUP BY city;

.explain SELECT *
FROM users
WHERE age = 25;

.stats SELECT *
FROM users
WHERE age = 25;

BEGIN;

UPDATE users
SET salary = 100000
WHERE id = 1;

ROLLBACK;
Learning Outcomes

Building PyDB provides hands-on understanding of several database internals:

SQL parsing
Query representation
Query execution
Table storage
Constraints
NULL semantics
Record identification
Hash indexing
B-Tree structures
B+Tree structures
Range searching
Query planning
Execution statistics
Persistence
Transactions
CLI design

The most important takeaway is that a database is not simply a collection of tables. It is a pipeline of components working together to transform a high-level query into controlled operations over stored data.

Future Exploration

Possible future learning areas include:

Query optimizer improvements
More advanced B+Tree deletion
Cost-based query planning
Joins
Composite indexes
Page-based storage
Buffer/cache management
Write-ahead logging
More complete transaction isolation
Concurrency
A more advanced SQL grammar

These are intentionally left as future experiments rather than requirements for the current project.

Philosophy

Build it to understand it.

PyDB is primarily a learning project focused on understanding what happens inside a database, rather than building a production-ready database system.

