# Document Extraction Findings

Run on DGX Spark, 2026-09-27. Three fictional investment memos, each as a digital PDF and an image-only scan. Nemotron Parse 2.0 and Docling are explored side by side, not ranked. A styled version of this page is in [`extraction-findings.html`](extraction-findings.html).

## Summary

Both tools extracted all body text, holdings tables and bullet points correctly, on digital and scanned copies alike. Nemotron Parse also converted every bar chart into a table with the exact values; Docling left charts as images. The main problems are heading structure for both tools, and one reading-order error for Docling.

On public benchmarks Nemotron Parse is mid-pack. MinerU2.5-Pro is the strongest candidate to test next at the same size.

## What each tool produced

3 memos × 2 versions (digital, scanned).

| Content | Nemotron Parse 2.0 | Docling |
| --- | --- | --- |
| Body text, holdings tables, bullets | Complete: every row and cell | Complete: every row and cell |
| Bar charts | Extracted as tables, exact values | Not extracted (image placeholder) |
| Headings | Partial: one read as a table caption; levels set per page | Partial: all flattened to one level |
| Reading order | Correct | 1 error: title placed after the table |
| Scanned copies | Same output, word for word as digital | Minor loss: a heading dropped in 2 of 3 |
| Page header and footer | Kept (tagged, easy to filter) | Dropped (default behaviour) |
| Speed | 0.80 pages/s (batch of 4, 3.1 s model load) | 2.3 to 3.8 s/page digital, 4.3 to 5.1 s/page scanned |

### Nemotron Parse 2.0

Vision-language model. Reads page pixels and returns text, layout blocks and reading order.

- **Charts are its standout.** It tagged each chart and rebuilt it as a table (for example Water 28, Power 19, Transportation 15).
- **Scan-robust at this level.** Scanned output was word for word the same as digital, even though the page layout shifted by up to 21 px with the skew.
- **Heading gaps:** "Portfolio Holdings" came out as a table caption in all three memos, and the first heading on page 2 became a top-level heading. Both can be fixed in our post-processing using the block types the model already returns.
- No truncated or failed pages.

### Docling

Layout and table pipeline. Uses the PDF text layer when present, OCR otherwise.

- **Reliable on text and tables** in both versions. Its OCR handled the scans without errors.
- **Charts are not extracted** by default. Version 2.130 has a chart extraction option that we have not tried yet.
- **Structure issues:** every heading, including the title, comes out at the same level. In one memo the title was placed after the holdings table.
- On scans, the "Sector Weights" heading was absorbed into the chart image in 2 of 3 memos.

> **Read the report scores with care.** Two scoring issues understate Nemotron Parse. The chart score ignores anything inside a table, so its chart tables scored 0. The text-similarity reference leaves the chart out, so extracting the chart data cost it about 0.05. Both are being fixed. The synthetic memos are also too easy to separate the tools. Real memos and a harsher scan setting are needed before drawing firm conclusions.

## Public benchmark context

ParseBench: about 2,000 real finance, insurance and government pages. Score out of 100.

| Model | Overall | Tables | Charts | Layout boxes |
| --- | ---: | ---: | ---: | ---: |
| rakedoc-nano | 77.2 | 86.4 | 64.9 | 74.3 |
| Infinity-Parser2-Pro | 74.3 | 86.4 | 61.3 | 74.9 |
| MinerU2.5-Pro (1.2B) | 72.8 | 77.6 | 61.6 | 79.3 |
| Chandra-ocr-2 | 70.1 | 89.2 | 65.1 | 51.2 |
| PaddleOCR-VL-1.6 | 67.4 | 67.8 | 54.2 | 77.8 |
| **Nemotron Parse 2.0** (reported by NVIDIA) | 63.9 | n/a | n/a | n/a |
| Docling (models) | 50.7 | 66.4 | 52.8 | 66.1 |

Nemotron Parse 2.0 is not on the official leaderboard; NVIDIA publishes only its overall score. On that figure it would place about 13th of 43 open-weight models. ParseBench is run by LlamaIndex, whose own product leads the commercial rankings.

## Models to try next

All open-weight and small enough to run on the Spark, so documents stay on premises.

| Model | Priority | Why try it | Watch for |
| --- | --- | --- | --- |
| **MinerU2.5-Pro** | First | About 9 points above Nemotron Parse at a similar size, with one of the best open-weight layout-box scores (79.3), which helps trace numbers back to the page. | Confirm its vLLM or Transformers path runs on aarch64 with CUDA 13. |
| **Infinity-Parser2** (Pro, Flash) | First | High text faithfulness (89.7). Flash has the best open-weight layout-box score (80.6). | Check model size and licence. |
| **Chandra-ocr-2** | Second | Best open-weight table score (89.2), which matters for holdings tables. | Weak layout boxes (51.2), so harder to trace values to the page. |
| **PaddleOCR-VL-1.6** | Second | Tops OmniDocBench (96.3) at 0.9B and has strong layout boxes. | Only 67.4 on business documents. Depends on PaddlePaddle, whose GB10 support is unconfirmed. |
| **Top "nano" parsers** (rakedoc, florin, KDL) | After review | Highest open-weight scores (76 to 77). | Lesser-known vendors: review licence and training-data provenance first. |
| **Docling with chart extraction** | Second | Closes Docling's biggest gap without changing tools. | Also try its forced-OCR mode on the scans. |

If policy allows sending documents to an external service, hosted options score higher (Claude Opus 5.5 at high effort: 79.9 overall and 94.3 on tables; LlamaParse Agentic at 87.0). Treat these as a quality ceiling, not the plan.

## Next steps

1. **Fix the two scoring issues** (score charts as label and value pairs, include chart data in the reference) and re-score the existing outputs.
2. **Improve Nemotron post-processing:** set heading levels from block types, and optionally drop tagged page headers and footers.
3. **Make the test harder:** add a lower-quality scan setting, run Docling with forced OCR, and measure Nemotron at batch sizes 1, 4 and 8.
4. **Add MinerU2.5-Pro and Infinity-Parser2-Flash** as extractors, each with its own report.
5. **Test on 10 to 20 real, sanitised memos** with hand-checked answers. This is the result that should drive the choice.

---

Data through 2026-09-27. ParseBench leaderboard as of 2026-09-25. Sources: [ParseBench leaderboard](https://github.com/run-llama/ParseBench/blob/main/leaderboard.csv), [Nemotron Parse 2.0 model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-2.0), [OmniDocBench](https://github.com/opendatalab/OmniDocBench), [ParseBench reproducibility issue](https://github.com/run-llama/ParseBench/issues/170).
