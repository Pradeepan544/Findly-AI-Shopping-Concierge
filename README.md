# Findly — AI Shopping Concierge 🛍️

**Findly** is an AI-powered shopping concierge designed to make product discovery more conversational, intuitive, and personalised.

Instead of navigating through multiple filters and product listings, users can describe what they are looking for in natural language. Findly understands their requirements, asks relevant follow-up questions, and retrieves matching products from a structured product dataset.

The goal is to bring the experience of speaking with a knowledgeable shopping assistant into an AI-powered interface.

---

## ✨ Key Features

### 1. Natural Language Shopping
- Describe shopping requirements in everyday language.
- Specify product categories, brands, budgets, and desired features in a single message.
- Understands conversational inputs rather than requiring users to follow rigid search formats.

### 2. Adaptive AI Conversations
- Uses an LLM-powered conversation flow to identify missing shopping requirements.
- Generates contextual follow-up questions based on the user's responses.
- Asks one question at a time instead of presenting a fixed questionnaire.
- Maintains conversation history and structured shopping requirements across turns.

### 3. Structured Requirement Management
Findly maintains a live shopping brief with attributes such as:
- Product category
- Brand preference
- Minimum and maximum budget
- Product features
- Intended purpose
- Minimum rating
- Review volume

Requirements are tracked with their source:
- **Explicit:** Directly mentioned by the user.
- **Inferred:** Interpreted from the conversation.
- **Unknown:** Not yet established.

Users can also update or remove previously specified requirements.

### 4. Dataset-Grounded Product Discovery
- Retrieves products from a structured Amazon sales dataset.
- Uses product names, categories, descriptions, prices, ratings, and review counts.
- Applies structured filters for supported requirements such as category, brand, budget, and rating.
- Uses product text as a relevance signal for descriptive features and intended use cases.
- Displays product information and source links from the dataset.

### 5. Product Recommendations
Product results are presented through product cards containing:
- Product name
- Product image
- Discounted price
- Original price, where available
- Customer rating
- Rating count
- Product link

---

## 🧠 How Findly Works

Findly combines LLM-powered conversational understanding with structured product retrieval.

**Step 1 — Understand**

The user describes what they want to purchase in natural language.

**Step 2 — Clarify**

The conversation layer identifies the requirements already provided and determines whether additional information would improve the search.

**Step 3 — Structure**

The conversation manager maintains a structured representation of the shopping brief, including explicit and inferred attributes.

**Step 4 — Retrieve**

The product retriever processes the requirements against the product dataset using structured filtering and text-based relevance matching.

**Step 5 — Recommend**

Matching product records are displayed to the user with dataset-backed information and product links.

---

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| LLM Integration | OpenRouter API |
| Product Retrieval | Pandas, structured filtering, text matching |
| Dataset | Kaggle Amazon Sales Dataset |
| Configuration | Python dotenv |

---

## 📂 Project Structure

```text
findly/
│
├── app.py                  # Flask application and API routes
├── conversation_manager.py # AI conversation and requirement management
├── product_retriever.py    # Dataset loading, filtering and retrieval
│
├── amazon.csv              # Product dataset
│
├── templates/
│   └── index.html          # Main application interface
│
├── static/
│   ├── app.js              # Frontend interaction logic
│   └── style.css           # Application styling
│
├── requirements.txt        # Python dependencies
├── .env.example            # Environment configuration template
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or later
- An OpenRouter API key
- Git (optional)

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd findly
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a template.

Add your configuration:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openrouter/free
FLASK_SECRET_KEY=your_secret_key
DATA_PATH=amazon.csv
PORT=5000
```

Replace the placeholder values with your own credentials.

### 5. Run the application

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

---

## 📊 Dataset

Findly uses the [Amazon Sales Dataset on Kaggle](https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset).

The supplied CSV contains product-level information, including:

- Product ID and product name
- Product category
- Discounted and actual prices
- Discount percentage
- Customer ratings and rating counts
- Product descriptions
- Product images and Amazon product links
- Customer review information

The dataset contains 1,465 rows and 1,351 unique product IDs.

**Important:** This is a historical dataset, not a live Amazon product feed. Product availability, prices, ratings, and links may have changed.

---

## ⚙️ Retrieval Approach

Findly uses a lightweight, dataset-grounded retrieval approach.

Rather than relying on an LLM to invent product recommendations, the application retrieves product records from the supplied dataset.

The retrieval process distinguishes between:

- **Hard filters:** Requirements that should constrain the matching products, such as supported product categories, brand preferences, price boundaries, and explicitly requested rating thresholds.
- **Soft relevance signals:** Descriptive features and use-case terms that help rank or prioritise relevant records without automatically excluding every product that lacks the exact wording.

This approach aims to balance requirement accuracy with the flexibility of natural-language shopping.

---

## ⚠️ Current Limitations

- Recommendations are limited to products available in the supplied dataset.
- The dataset does not contain a dedicated brand field; brand identification relies on product text.
- Product features and intended use cases are inferred from available descriptions and text, not independently verified specifications.
- The application does not currently retrieve live Amazon inventory or real-time prices.
- An LLM's interpretation can vary depending on the selected model and its availability through OpenRouter.
- The fallback conversation mode supports basic application testing but does not provide the full adaptive LLM experience.

Findly avoids treating unsupported product claims as verified facts.

---

## 🔮 Future Improvements

Potential areas for further development:

- Expand product coverage with additional structured datasets or live commerce integrations.
- Improve semantic product retrieval using embeddings and vector search.
- Generate product comparisons based on user priorities.
- Provide evidence-backed explanations for recommendations.
- Introduce user preference memory across shopping sessions.
- Add product comparison and shortlist functionality.
- Integrate live inventory and price information through authorised commerce APIs.

---

## 🎯 Project Objective

Findly explores how conversational AI can simplify product discovery by combining natural-language understanding, adaptive questioning, structured requirement management, and grounded product retrieval.

**The idea is simple: users should be able to explain what they need, not learn how to search for it.**

---

## 📄 Disclaimer

This project is a prototype developed for product exploration and demonstration purposes. Product information is sourced from the referenced Kaggle dataset and is not affiliated with, endorsed by, or maintained by Amazon.

