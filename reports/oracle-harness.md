# NL2SQL evaluation: oracle:golden/chinook_golden.json

> Harness check, not a model result: the reference SQL of each golden case was replayed as if a model had written it, on CPU, at revision 09195c3, with: nl2sql eval --db data/chinook.sqlite --llm oracle:golden/chinook_golden.json --golden golden/chinook_golden.json --examples examples/chinook_examples.json --report reports/oracle-harness.md. It shows that the harness, guard, executor and result matcher agree on every reference query; it says nothing about any language model.

Run started 2026-09-16 23:29:39, 30 cases, 0.1 s wall clock.

| Metric | Value |
|---|---|
| Execution success | 100% |
| Result match (deterministic) | 100% |
| Judge-rescued cases | 0 |
| Accepted (match or judged equivalent) | 100% |
| Repairs used (count by n) | {0: 30} |
| Median latency per question | 1 ms |

| # | Question | Status | Exec | Match | Judge | Repairs | ms |
|---|---|---|---|---|---|---|---|
| g01 | How many customers are there? | ok | ✓ | ✓ |  | 0 | 6 |
| g02 | List the names of all genres in alphabetical order. | ok | ✓ | ✓ |  | 0 | 0 |
| g03 | Which country has the most customers? Show the country and the number of customers. | ok | ✓ | ✓ |  | 0 | 1 |
| g04 | What is the total revenue across all invoices? | ok | ✓ | ✓ |  | 0 | 0 |
| g05 | Which artists have more than 10 albums? Show the artist name and the album count. | ok | ✓ | ✓ |  | 0 | 1 |
| g06 | How many tracks are in the Rock genre? | ok | ✓ | ✓ |  | 0 | 1 |
| g07 | Which customers are from Brazil? Show first name, last name and email. | ok | ✓ | ✓ |  | 0 | 1 |
| g08 | How many invoices were issued in 2023? | ok | ✓ | ✓ |  | 0 | 1 |
| g09 | What is the total invoice revenue per year? Show the year and the revenue. | ok | ✓ | ✓ |  | 0 | 1 |
| g10 | Which customer has spent the most in total? Show their first name, last name and total spent. | ok | ✓ | ✓ |  | 0 | 1 |
| g11 | How many tracks are longer than 5 minutes? | ok | ✓ | ✓ |  | 0 | 1 |
| g12 | Which media type has the most tracks? Show the media type name and the track count. | ok | ✓ | ✓ |  | 0 | 1 |
| g13 | How many albums does Iron Maiden have? | ok | ✓ | ✓ |  | 0 | 1 |
| g14 | How many tracks are on the playlist called 'Brazilian Music'? | ok | ✓ | ✓ |  | 0 | 0 |
| g15 | Which employee supports the most customers? Show the employee's first name, last name and the number of customers. | ok | ✓ | ✓ |  | 0 | 1 |
| g16 | For every employee who has a manager, show the employee's first name, last name and the manager's last name. | ok | ✓ | ✓ |  | 0 | 0 |
| g17 | How many distinct billing countries appear on invoices? | ok | ✓ | ✓ |  | 0 | 1 |
| g18 | What is the average invoice total for invoices billed to Germany, rounded to two decimals? | ok | ✓ | ✓ |  | 0 | 0 |
| g19 | Which genre has the longest average track length? Show the genre name and the average length in milliseconds. | ok | ✓ | ✓ |  | 0 | 1 |
| g20 | How many tracks does the artist AC/DC have? | ok | ✓ | ✓ |  | 0 | 1 |
| g21 | What is the total number of tracks sold, meaning the sum of quantities across all invoice lines? | ok | ✓ | ✓ |  | 0 | 0 |
| g22 | Which sales support agent generated the most invoice revenue? Show first name, last name and total revenue. | ok | ✓ | ✓ |  | 0 | 1 |
| g23 | Which cities have more than one customer? Show the city and the country. | ok | ✓ | ✓ |  | 0 | 1 |
| g24 | How many tracks have no composer listed? | ok | ✓ | ✓ |  | 0 | 1 |
| g25 | What is the name of the longest track and how long is it in milliseconds? | ok | ✓ | ✓ |  | 0 | 1 |
| g26 | How many customers does each country have? Show the country and the count. | ok | ✓ | ✓ |  | 0 | 0 |
| g27 | What is the total amount invoiced to the customer with the email luisg@embraer.com.br? | ok | ✓ | ✓ |  | 0 | 0 |
| g28 | How many albums are in the database? | ok | ✓ | ✓ |  | 0 | 0 |
| g29 | Which genres have more than 300 tracks? Show the genre name and the track count. | ok | ✓ | ✓ |  | 0 | 1 |
| g30 | How many distinct tracks appear on more than one playlist? | ok | ✓ | ✓ |  | 0 | 1 |