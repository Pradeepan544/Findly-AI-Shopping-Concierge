# Findly — AI Shopping Concierge (Revised)

A local Flask + HTML/CSS/JavaScript prototype. The conversation brain uses an OpenRouter-compatible chat API; product retrieval is deterministic and grounded in the Kaggle CSV.

## Setup (Windows / VS Code)

1. Extract this ZIP.
2. Download `amazon.csv` from https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset
3. Put `amazon.csv` in the same folder as `app.py`.
4. Rename `.env.example` to `.env` and paste your OpenRouter API key.
5. Open a terminal in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

6. Open http://127.0.0.1:5000

## Model configuration

Default: `OPENROUTER_MODEL=openrouter/free`. This uses an eligible free model but does NOT guarantee the provider/model is Mistral. If your OpenRouter dashboard shows a specific Mistral free model, set its exact model slug in `.env`. Model availability and free limits can change.

The API key stays in `.env` and is only read by Python. Never paste it into frontend JavaScript or commit `.env`.

## What this version demonstrates

- LLM-driven, adaptive follow-up selection (not a hard-coded five-question form).
- Full conversation history plus structured requirement state sent to the LLM each turn.
- State fields track value and source: explicit, inferred, unknown.
- The prompt instructs the LLM not to repeat answered topics and to stop when enough information exists.
- Special handling for open-ended brand preference ("any brand").
- One question at a time.
- Structured price/rating filters plus text matching against product title/category/about_product.
- Product cards show dataset-backed price/rating/review count and source links.

## Honest data limitations

- The dataset has no dedicated brand column; brand is inferred by searching product title/description.
- Purpose (music/calls) is not a dedicated column. For calls, the retriever can prioritize records whose text mentions microphone/mic/ENC/calling. This is weak textual evidence, not proof of call quality.
- Do not claim durability, comfort, workout suitability, battery life, or other facts unless the dataset text explicitly supports them.
- Data is a historical scrape, not live Amazon inventory or current prices.

## RAG note

This is a lightweight retrieval-augmented approach: structured Pandas filtering and product-text retrieval from the CSV provide records to the recommendation flow. It does not require a vector database for this small dataset. The current implementation returns grounded records to the UI; a further enhancement would pass the retrieved records back to the LLM to generate evidence-cited natural-language explanations.

## Fallback mode

If the API key is missing or OpenRouter is unavailable, a basic deterministic fallback keeps the app runnable for UI testing. It is not equivalent to the intended adaptive LLM experience. For assignment evaluation, test with a working OpenRouter model.


## Filter-edit and price-range improvements

- Supports minimum price (`above ₹4,000`, `over 4k`, `at least 25000`), maximum price (`under ₹3,000`) and ranges (`between ₹3,000 and ₹5,000`).
- Explicit edits such as `remove rating`, `remove brand`, `any brand` and `no budget, any price` override stale session values.
- Purpose and descriptive feature matches are relevance signals rather than requiring every word to occur in the product listing.
- The Live Requirements panel shows lower and upper price bounds.


## Dataset-aware retrieval update

The app loads all 1,465 unique records in the supplied Kaggle CSV. Search returns all records matching the active hard filters (not just the first six). Price, brand, broad product family, and explicitly requested rating constraints are hard filters. Use-case/features are soft relevance signals and do not exclude records merely because the wording is absent.

Category phrases such as "Samsung Galaxy S series" are normalized to the smartphone taxonomy, with S-series matching handled as a model-family constraint. The dataset includes only the products actually present in this CSV; it is not a complete Amazon catalogue. No software can return a product absent from the dataset.
