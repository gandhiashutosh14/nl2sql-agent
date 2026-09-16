# NL2SQL evaluation: hf:Qwen/Qwen2.5-Coder-1.5B-Instruct

> Provenance note, added 2026-09-16 after the run: this report was produced on an RTX 4050 laptop
> GPU by the evaluation run *before* the join-hint restriction and the prompt rules described in the
> README were added, so it does not describe the committed prompt exactly. At the time of the run
> golden case g08 asked about 2013 (a year with no invoices in this database build); the committed
> golden set asks about 2023. A re-run with the committed code was started and stopped before it
> finished because of GPU load, so no numbers for the committed prompt are claimed. The table and
> mismatch analysis below are unchanged from the run.

Run started 2026-09-16 18:53:57, 30 cases, 127.5 s wall clock.

| Metric | Value |
|---|---|
| Execution success | 97% |
| Result match (deterministic) | 80% |
| Judge-rescued cases | 0 |
| Accepted (match or judged equivalent) | 80% |
| Repairs used (count by n) | {0: 24, 1: 5, 2: 1} |
| Median latency per question | 2106 ms |

| # | Question | Status | Exec | Match | Judge | Repairs | ms |
|---|---|---|---|---|---|---|---|
| g01 | How many customers are there? | ok | ✓ | ✗ |  | 1 | 15766 |
| g02 | List the names of all genres in alphabetical order. | ok | ✓ | ✓ |  | 0 | 644 |
| g03 | Which country has the most customers? Show the country and the number of customers. | ok | ✓ | ✓ |  | 0 | 11225 |
| g04 | What is the total revenue across all invoices? | ok | ✓ | ✓ |  | 0 | 877 |
| g05 | Which artists have more than 10 albums? Show the artist name and the album count. | ok | ✓ | ✓ |  | 0 | 2342 |
| g06 | How many tracks are in the Rock genre? | ok | ✓ | ✓ |  | 0 | 2096 |
| g07 | Which customers are from Brazil? Show first name, last name and email. | ok | ✓ | ✓ |  | 0 | 1151 |
| g08 | How many invoices were issued in 2013? | ok | ✓ | ✓ |  | 0 | 1142 |
| g09 | What is the total invoice revenue per year? Show the year and the revenue. | ok | ✓ | ✓ |  | 0 | 1527 |
| g10 | Which customer has spent the most in total? Show their first name, last name and total spent. | ok | ✓ | ✓ |  | 0 | 3154 |
| g11 | How many tracks are longer than 5 minutes? | ok | ✓ | ✗ |  | 0 | 1254 |
| g12 | Which media type has the most tracks? Show the media type name and the track count. | ok | ✓ | ✓ |  | 0 | 1854 |
| g13 | How many albums does Iron Maiden have? | ok | ✓ | ✓ |  | 0 | 1930 |
| g14 | How many tracks are on the playlist called 'Brazilian Music'? | ok | ✓ | ✓ |  | 0 | 2118 |
| g15 | Which employee supports the most customers? Show the employee's first name, last name and the number of customers. | ok | ✓ | ✓ |  | 0 | 2486 |
| g16 | For every employee who has a manager, show the employee's first name, last name and the manager's last name. | ok | ✓ | ✓ |  | 0 | 1394 |
| g17 | How many distinct billing countries appear on invoices? | ok | ✓ | ✓ |  | 0 | 789 |
| g18 | What is the average invoice total for invoices billed to Germany, rounded to two decimals? | ok | ✓ | ✓ |  | 0 | 2073 |
| g19 | Which genre has the longest average track length? Show the genre name and the average length in milliseconds. | ok | ✓ | ✓ |  | 0 | 2117 |
| g20 | How many tracks does the artist AC/DC have? | ok | ✓ | ✓ |  | 1 | 5843 |
| g21 | What is the total number of tracks sold, meaning the sum of quantities across all invoice lines? | ok | ✓ | ✓ |  | 0 | 965 |
| g22 | Which sales support agent generated the most invoice revenue? Show first name, last name and total revenue. | failed | ✗ | ✗ |  | 2 | 14463 |
| g23 | Which cities have more than one customer? Show the city and the country. | ok | ✓ | ✓ |  | 1 | 18731 |
| g24 | How many tracks have no composer listed? | ok | ✓ | ✓ |  | 1 | 4924 |
| g25 | What is the name of the longest track and how long is it in milliseconds? | ok | ✓ | ✗ |  | 0 | 2271 |
| g26 | How many customers does each country have? Show the country and the count. | ok | ✓ | ✗ |  | 1 | 16552 |
| g27 | What is the total amount invoiced to the customer with the email luisg@embraer.com.br? | ok | ✓ | ✓ |  | 0 | 1929 |
| g28 | How many albums are in the database? | ok | ✓ | ✓ |  | 0 | 608 |
| g29 | Which genres have more than 300 tracks? Show the genre name and the track count. | ok | ✓ | ✓ |  | 0 | 2443 |
| g30 | How many distinct tracks appear on more than one playlist? | ok | ✓ | ✗ |  | 0 | 2723 |

## Mismatches

### g01: How many customers are there?

Reference:
```sql
SELECT COUNT(*) AS customer_count FROM Customer
```
Candidate:
```sql
SELECT COUNT(*) FROM Customer AS T1 INNER JOIN Employee AS T2 ON T1.SupportRepId = T2.EmployeeId WHERE T1.Country = 'Canada'
```

### g11: How many tracks are longer than 5 minutes?

Reference:
```sql
SELECT COUNT(*) AS long_tracks FROM Track WHERE Milliseconds > 300000
```
Candidate:
```sql
SELECT COUNT(*) AS long_tracks FROM Track WHERE Milliseconds > 500000
```

### g22: Which sales support agent generated the most invoice revenue? Show first name, last name and total revenue.

Reference:
```sql
SELECT e.FirstName, e.LastName, SUM(i.Total) AS revenue FROM Employee e JOIN Customer c ON c.SupportRepId = e.EmployeeId JOIN Invoice i ON i.CustomerId = c.CustomerId GROUP BY e.EmployeeId ORDER BY revenue DESC LIMIT 1
```
Candidate:
```sql
SELECT e.FirstName, e.LastName, SUM(il.UnitPrice * il.Quantity) AS total_revenue 
FROM Employee e 
JOIN Customer c ON e.SupportRepId = c.SupportRepId 
JOIN Invoice i ON c.CustomerId = i.CustomerId 
JOIN InvoiceLine il ON i.InvoiceId = il.InvoiceId 
WHERE e.Title = 'Sales Support Agent' 
GROUP BY e.EmployeeId 
ORDER BY total_revenue DESC 
LIMIT 1
```
Error: `Column 'SupportRepId' does not exist in table Employee. Its columns are: EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email.`

### g25: What is the name of the longest track and how long is it in milliseconds?

Reference:
```sql
SELECT Name, Milliseconds FROM Track ORDER BY Milliseconds DESC LIMIT 1
```
Candidate:
```sql
SELECT T2.Name, T1.Milliseconds FROM Track AS T1 INNER JOIN Genre AS T2 ON T1.GenreId = T2.GenreId ORDER BY T1.Milliseconds DESC LIMIT 1
```

### g26: How many customers does each country have? Show the country and the count.

Reference:
```sql
SELECT Country, COUNT(*) AS customers FROM Customer GROUP BY Country
```
Candidate:
```sql
SELECT T1.Country, COUNT(*) AS customer_count FROM Customer AS T1 INNER JOIN Employee AS T2 ON T1.SupportRepId = T2.EmployeeId
```

### g30: How many distinct tracks appear on more than one playlist?

Reference:
```sql
SELECT COUNT(*) AS multi_playlist_tracks FROM (SELECT TrackId FROM PlaylistTrack GROUP BY TrackId HAVING COUNT(*) > 1)
```
Candidate:
```sql
SELECT COUNT(DISTINCT T1.TrackId) AS tracks FROM PlaylistTrack AS T1 JOIN PlaylistTrack AS T2 ON T1.TrackId = T2.TrackId GROUP BY T1.TrackId HAVING COUNT(T2.TrackId) > 1
```
