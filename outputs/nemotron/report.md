# Nemotron Parse 2.0: extraction report

Each memo is scored against its `.truth.json` and `.reference.md`. The README explains what each metric catches and misses.

## Run

- **digital**: model_revision: b6742064f4a8cf22a10383ece5e7fbead355ac04, batch_size: 4, load_seconds: 3.115, pages_per_second: 0.803, generated_tokens: 3290
- **scanned**: model_revision: b6742064f4a8cf22a10383ece5e7fbead355ac04, batch_size: 4, load_seconds: 3.115, pages_per_second: 0.803, generated_tokens: 3290

## digital

| Memo | Headings (as heading / right level) | Table header | Rows | Cells in tables | Text similarity | Bullets | Chart labels | Chart values | Furniture kept | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| cedar-pine.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.903 | 3/3 | 1/3 | 0/3 | 2/2 | 2.582 |
| lakefront.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.899 | 3/3 | 2/3 | 0/3 | 2/2 | 2.582 |
| northwind-harbor.pdf | 4/5 · 3/5 | 1/1 | 5/5 | 20/20 | 0.886 | 3/3 | 0/4 | 0/4 | 2/2 | 2.446 |

<details><summary>cedar-pine.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Materials
- chart label missing: Cash
- chart value missing: 35
- chart value missing: 18
- chart value missing: 12

</details>

<details><summary>lakefront.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Transportation
- chart value missing: 28
- chart value missing: 19
- chart value missing: 15

</details>

<details><summary>northwind-harbor.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Industrials
- chart label missing: Real Estate
- chart label missing: Healthcare
- chart label missing: Utilities
- chart value missing: 32
- chart value missing: 21
- chart value missing: 14
- chart value missing: 11

</details>

## scanned

| Memo | Headings (as heading / right level) | Table header | Rows | Cells in tables | Text similarity | Bullets | Chart labels | Chart values | Furniture kept | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| cedar-pine.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.903 | 3/3 | 1/3 | 0/3 | 2/2 | 2.446 |
| lakefront.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.899 | 3/3 | 2/3 | 0/3 | 2/2 | 2.444 |
| northwind-harbor.pdf | 4/5 · 3/5 | 1/1 | 5/5 | 20/20 | 0.886 | 3/3 | 0/4 | 0/4 | 2/2 | 2.444 |

<details><summary>cedar-pine.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Materials
- chart label missing: Cash
- chart value missing: 35
- chart value missing: 18
- chart value missing: 12

</details>

<details><summary>lakefront.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Transportation
- chart value missing: 28
- chart value missing: 19
- chart value missing: 15

</details>

<details><summary>northwind-harbor.pdf: misses and notes</summary>

- heading missing: Portfolio Holdings
- heading level: Sector Weights (h1, expected h2)
- chart label missing: Industrials
- chart label missing: Real Estate
- chart label missing: Healthcare
- chart label missing: Utilities
- chart value missing: 32
- chart value missing: 21
- chart value missing: 14
- chart value missing: 11

</details>
