# Docling: extraction report

Each memo is scored against its `.truth.json` and `.reference.md`. The README explains what each metric catches and misses.

## Run

- **digital**: force_ocr: False, load_seconds: 1.717, note: The first document's seconds include Docling's lazy model loading.
- **scanned**: force_ocr: False, load_seconds: 1.767, note: The first document's seconds include Docling's lazy model loading.

## digital

| Memo | Headings (as heading / right level) | Table header | Rows | Cells in tables | Text similarity | Bullets | Chart labels | Chart values | Furniture kept | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| cedar-pine.pdf | 5/5 · 4/5 | 1/1 | 4/4 | 16/16 | 0.863 | 3/3 | 1/3 | 0/3 | 0/2 | 7.602 |
| lakefront.pdf | 5/5 · 4/5 | 1/1 | 4/4 | 16/16 | 0.943 | 3/3 | 2/3 | 0/3 | 0/2 | 4.64 |
| northwind-harbor.pdf | 5/5 · 4/5 | 1/1 | 5/5 | 20/20 | 0.952 | 3/3 | 0/4 | 0/4 | 0/2 | 6.0 |

<details><summary>cedar-pine.pdf: misses and notes</summary>

- heading level: Cedar and Pine Allocation Memorandum (h2, expected h1)
- chart label missing: Materials
- chart label missing: Cash
- chart value missing: 35
- chart value missing: 18
- chart value missing: 12
- furniture dropped: Cedar and Pine Partners  |  Private Memorandum
- furniture dropped: Illustrative only: Cedar and Pine Partners is fictional and this memorandum is not an offer to sell securities.

</details>

<details><summary>lakefront.pdf: misses and notes</summary>

- heading level: Lakefront Municipal Credit Memorandum (h2, expected h1)
- chart label missing: Transportation
- chart value missing: 28
- chart value missing: 19
- chart value missing: 15
- furniture dropped: Lakefront Allocation Group  |  Private Memorandum
- furniture dropped: Illustrative only: Lakefront Allocation Group is fictional and this memorandum is not an offer to sell securities.

</details>

<details><summary>northwind-harbor.pdf: misses and notes</summary>

- heading level: Northwind Harbor Confidential Memorandum (h2, expected h1)
- chart label missing: Industrials
- chart label missing: Real Estate
- chart label missing: Healthcare
- chart label missing: Utilities
- chart value missing: 32
- chart value missing: 21
- chart value missing: 14
- chart value missing: 11
- furniture dropped: Northwind Harbor Capital  |  Private Memorandum
- furniture dropped: Illustrative only: Northwind Harbor Capital is fictional and this memorandum is not an offer to sell securities.

</details>

## scanned

| Memo | Headings (as heading / right level) | Table header | Rows | Cells in tables | Text similarity | Bullets | Chart labels | Chart values | Furniture kept | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| cedar-pine.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.871 | 3/3 | 1/3 | 0/3 | 0/2 | 10.119 |
| lakefront.pdf | 4/5 · 3/5 | 1/1 | 4/4 | 16/16 | 0.922 | 3/3 | 2/3 | 0/3 | 0/2 | 8.535 |
| northwind-harbor.pdf | 5/5 · 4/5 | 1/1 | 5/5 | 20/20 | 0.952 | 3/3 | 0/4 | 0/4 | 0/2 | 8.876 |

<details><summary>cedar-pine.pdf: misses and notes</summary>

- heading missing: Sector Weights
- heading level: Cedar and Pine Allocation Memorandum (h2, expected h1)
- chart label missing: Materials
- chart label missing: Cash
- chart value missing: 35
- chart value missing: 18
- chart value missing: 12
- furniture dropped: Cedar and Pine Partners  |  Private Memorandum
- furniture dropped: Illustrative only: Cedar and Pine Partners is fictional and this memorandum is not an offer to sell securities.

</details>

<details><summary>lakefront.pdf: misses and notes</summary>

- heading missing: Sector Weights
- heading level: Lakefront Municipal Credit Memorandum (h2, expected h1)
- chart label missing: Transportation
- chart value missing: 28
- chart value missing: 19
- chart value missing: 15
- furniture dropped: Lakefront Allocation Group  |  Private Memorandum
- furniture dropped: Illustrative only: Lakefront Allocation Group is fictional and this memorandum is not an offer to sell securities.

</details>

<details><summary>northwind-harbor.pdf: misses and notes</summary>

- heading level: Northwind Harbor Confidential Memorandum (h2, expected h1)
- chart label missing: Industrials
- chart label missing: Real Estate
- chart label missing: Healthcare
- chart label missing: Utilities
- chart value missing: 32
- chart value missing: 21
- chart value missing: 14
- chart value missing: 11
- furniture dropped: Northwind Harbor Capital  |  Private Memorandum
- furniture dropped: Illustrative only: Northwind Harbor Capital is fictional and this memorandum is not an offer to sell securities.

</details>
