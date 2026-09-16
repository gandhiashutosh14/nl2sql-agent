# Guard outcomes for fixed inputs

Generated 2026-09-16 17:59 UTC at revision 09195c3 with `python scripts/show_guard.py --db data/chinook.sqlite --out reports/guard-rejections.md`. The inputs are written in `scripts/show_guard.py`; no model produced them. `rejected` means the SQL never reaches the database; `errors` means it parsed and is read-only but names unknown identifiers, and the sentences shown are what the agent feeds back to the model for repair; `accepted` means the executor would run it read-only with a row cap and a timeout.

| Input | SQL | Outcome | Expected | Guard message |
|---|---|---|---|---|
| write: DELETE | `DELETE FROM Customer` | rejected | rejected | Only SELECT queries are allowed, got DELETE. |
| write: INSERT | `INSERT INTO Genre (Name) VALUES ('x')` | rejected | rejected | Only SELECT queries are allowed, got INSERT. |
| write: UPDATE | `UPDATE Track SET UnitPrice = 0` | rejected | rejected | Only SELECT queries are allowed, got UPDATE. |
| DDL: DROP | `DROP TABLE Invoice` | rejected | rejected | Only SELECT queries are allowed, got DROP. |
| two statements | `SELECT 1; SELECT 2` | rejected | rejected | Expected one statement, found 2. |
| select then DROP | `SELECT * FROM Customer; DROP TABLE Customer` | rejected | rejected | Expected one statement, found 2. |
| PRAGMA | `PRAGMA table_info(Customer)` | rejected | rejected | Only SELECT queries are allowed, got PRAGMA. |
| unterminated string | `SELECT Name FROM Genre WHERE Name = 'Rock` | rejected | rejected | SQL does not parse: Error tokenizing 'SELECT Name FROM Genre WHERE Name = 'Roc' |
| not SQL | `SELECT FROM WHERE` | rejected | rejected | SQL does not parse: Expected table name but got <Token token_type: TokenType.WHERE, text: WHERE, line: 1, col: 17, start: 12, end: 16, comments: []>. Line 1, Col: 17. |
| empty reply | `(empty)` | rejected | rejected | No SQL statement found. |
| unknown table | `SELECT Name FROM Genres` | errors | errors | Unknown table 'Genres'. Available tables: Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track. |
| unknown column | `SELECT c.FullName FROM Customer c` | errors | errors | Column 'FullName' does not exist in table Customer. Its columns are: CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId. |
| unknown column, unqualified | `SELECT Revenue FROM Invoice` | errors | errors | Column 'Revenue' does not exist in any referenced table (Invoice). |
| plain select | `SELECT Country, COUNT(*) AS customers FROM Customer GROUP BY Country` | accepted | accepted |  |
| select-list alias in ORDER BY | `SELECT Country, COUNT(*) AS n FROM Customer GROUP BY Country ORDER BY n DESC LIMIT 1` | accepted | accepted |  |
| join with aliases | `SELECT ar.Name, COUNT(*) AS albums FROM Artist ar JOIN Album al ON al.ArtistId = ar.ArtistId GROUP BY ar.ArtistId` | accepted | accepted |  |
| CTE | `WITH t AS (SELECT TrackId FROM PlaylistTrack GROUP BY TrackId HAVING COUNT(*) > 1) SELECT COUNT(*) FROM t` | accepted | accepted |  |

17 inputs, 0 unexpected outcomes.