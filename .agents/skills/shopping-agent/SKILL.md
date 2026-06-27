---
name: shopping-agent
description: Runs an autonomous ReAct loop using Groq and Gemini Search Grounding to extract e-commerce prices, save to MongoDB, and formulate shopping recommendations.
---

# AI Shopping Agent Orchestrator

This skill allows the AI assistant to coordinate, run, and modify the Autonomous AI Shopping Agent web application.

## 📂 Core Structure

The application is structured into separated subdirectories:
* `frontend/`: Web interface assets (`index.html`, `styles.css`, `app.js`).
* `backend/`: FastAPI server (`server.py`), Database layer (`db.py`), Key rotator (`api_balancer.py`).
* `skills/`: The ReAct Loop orchestrator (`shopping_agent.py`) and scraper logic (`scraper_skill.py`).
* `tests/`: Unit tests and diagnostics.
* `scripts/`: Seeding and cache utilities.

## ⚙️ How to Load and Run

### 1. Requirements
Install the dependencies listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```
Make sure **Node.js** is installed on the system (used by the backend to launch the MCP browser crawler via `npx`).

### 2. Environment Variables (.env)
Create a `.env` file in the project root containing:
```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
MONGO_URI=your_mongodb_connection_string
```

### 3. Execution
Start the FastAPI server:
```bash
python -m uvicorn backend.server:app --reload --port 8000
```
Open your browser to `http://127.0.0.1:8000`.

## 🧠 Logical Workflows

### ReAct Loop Process (`skills/shopping_agent.py`)
1. **Fetch**: Uses `fetch_html_via_mcp` to download raw HTML via ScraperAPI.
2. **Extract**: Falls back through CSS selectors, JSON-LD schema parsing, and Groq `llama-3.3-70b-versatile` text extraction.
3. **Compare**: Queries Gemini (`gemini-2.5-flash-lite`) with Google Search grounding to find competitor prices, filters outliers using a statistical median filter, and determines the cheapest deal in Python space (`find_cheapest_deal`).
4. **Cache & Recommend**: Stores current checks in MongoDB and fetches historical baselines to decide on a `BUY NOW` or `WAIT` verdict.
