# SupportIQ

> **AI-powered real estate customer support automation platform — custom-tailored for the Pakistani market (Karachi-focused).**

---

## Overview

SupportIQ replaces the manual, WhatsApp-centric workflows of independent Karachi real estate agencies with a fully automated, intent-aware support stack. The platform stabilizes chaotic customer queries, captures qualified buyer intent, predicts listing valuations, and bridges the digital gap for agencies that previously had no automation infrastructure — all through a single, self-hosted FastAPI application.

---

## Architecture & Enterprise Tech Stack

SupportIQ follows a deliberately lean architecture: **no React, no Tailwind, no Webpack**. The frontend is rendered server-side via Jinja2 and animated by raw vanilla JavaScript modules, keeping the toolchain trivially debuggable and deployable on commodity hardware.

### Backend

| Layer | Technology | Notes |
|---|---|---|
| Web framework | FastAPI (latest) | Async REST + server-side rendering |
| ASGI server | Uvicorn | Hot-reload in development |
| ORM | SQLAlchemy | Declarative models |
| Database | SQLite (`supportiq.db`) | Auto-initialized, gitignored |
| Templating | Jinja2 | SSR for HTML pages |
| Config | `python-dotenv` | Loads `backend/.env` |

### Frontend

| Layer | Technology | Notes |
|---|---|---|
| Templates | Jinja2 + HTML5 | `base.html`, `index.html`, `listings.html`, `predictor.html`, `admin.html` |
| Stylesheets | CSS3 (`base.css`, `chat.css`) | Deep Blue theme |
| Client logic | Vanilla JavaScript | `chat.js`, `listings.js`, `predictor.js`, `admin.js` |
| Build step | **None** | No bundler, no transpiler |

### AI / ML Core

| Layer | Technology | Notes |
|---|---|---|
| Classical ML | scikit-learn | `LinearSVC` + `CalibratedClassifierCV` for intent; `RandomForestRegressor` / `LinearRegression` for price |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | 384-dim dense vectors |
| Vector store | FAISS (`faiss-cpu`, `IndexFlatL2`) | Local index persisted to `backend/data/faiss_index.bin` |
| Generative LLM | Google Gemini (`gemini-2.5-flash`) | Strict RAG grounding via system instruction |
| Serialization | `joblib`, `pickle` | All model artifacts in `backend/models/` |

### Pinned Dependency Ledger (`backend/requirements.txt`)

```
fastapi
uvicorn
sqlalchemy
python-dotenv
scikit-learn
pandas
numpy
joblib
faiss-cpu
google-genai
sentence-transformers
jinja2
python-multipart
```

> The runtime layers `STORAGE_OPTIONS`, `FORCE_TF_AVAILABLE`, `AA_IMPORT_TENSORFLOW`, and `USE_TORCH=1` into the environment at startup to bypass TensorFlow/protobuf binary conflicts and force the Transformers stack onto PyTorch.

---

## Core Feature Deep-Dive

### Property Listings System
Full DB-backed CRUD surface for property portfolios. Listings are persisted via SQLAlchemy and exposed both as JSON for the public `/listings` page and via the admin namespace for privileged management.

| Column | Type | Notes |
|---|---|---|
| `id` | `Integer` PK | Auto-increment |
| `title`, `location` | `String` | Indexed for search |
| `area` | `Float` | Square yards |
| `property_type` | `String` | Free-form (house/plot/apartment) |
| `price` | `Float` | PKR |
| `bedrooms`, `bathrooms` | `Integer` | — |
| `status` | `String` | Defaults to `available` |
| `agency_id` | `Integer` | Tenant boundary (default `1`) |
| `created_at` | `DateTime(timezone=True)` | Server default `now()` |

### ML Price Predictor Dashboard
Hybrid deterministic + ML pricing engine trained on `backend/data/Cleaned_Data.csv` (~16,850 rows):

- **Candidate models**: `LinearRegression` and `RandomForestRegressor(n_estimators=100, random_state=42)`.
- **Target transform**: `log1p(Price)` to stabilize variance across the PKR range.
- **Feature encoding**: One-hot on `Address`; numeric passthrough for `NoOfBedrooms`, `NoOfBathrooms`.
- **Address standardization dictionary**: `DHA / Defence` → `DHA Phase 6, DHA Defence`; `Bahria` → `Bahria Town Karachi, Karachi`; `Gulshan` → `Gulshan-e-Iqbal, Karachi`.
- **Post-prediction spatial adjustment**: `final = predicted_price * (area / 120) * (1 + 0.05 * (bedrooms − 2))`.
- **Fallback multipliers**: DHA/Defence `1.3×`, Bahria/Gulshan `1.0×`, Dalmia `0.7×` median baseline.
- **Selection rule**: Model with higher test R² is persisted as `backend/models/price_model.pkl`.

### Stateful Client Communication Widget
- **Session tracking**: In-memory `SESSION_STORE` keyed by `session_id` (also persisted via the `Conversation` table).
- **Sequential 3-step lead capture**: `idle` → `collecting_lead` walks `name` → `budget` → `contact`, then writes a row to the `leads` table.
- **Polling**: Frontend `chat.js` polls `GET /api/history/{session_id}` at sub-3-second cadence for near-real-time rendering.
- **Escalation bypass**: Once a session is marked `escalated`, the AI is fully bypassed and messages route directly to the agent console.

### Admin Oversight Dashboard
Tabular monitoring surface backed by `/api/admin/*`:

- **`/listings`** — full listing inventory (admin view).
- **`/leads`** — every captured lead row.
- **`/conversations`** — full chat logs grouped by `session_id`.
- **`/escalated`** — filtered conversations where `status='escalated'`.
- **`/stats`** — `{ total_listings, total_leads, total_messages, unique_sessions }`.
- **`/resolve/{session_id}`** — marks a session `resolved`.
- **`/send-message`** — bidirectional agent takeover: writes a `role='bot'` message back to the user's session in real time.

### Core Intent Classifier
- **Algorithm**: `TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), max_df=0.95, min_df=2)` → `CalibratedClassifierCV(LinearSVC(C=1.0, random_state=42, dual=False), method='sigmoid')`.
- **Training set**: `backend/data/intent_dataset.csv` (~2,100 rows), stratified 80/20 split.
- **Confidence threshold**: scores `< 0.40` are downgraded to `uncertain` and routed to RAG fallback.
- **Localized preprocessing**: Pakistani phone numbers (`+92…`, `03xx…`) are normalized to `__PHONE__`; lowercase + whitespace collapse.
- **Intent labels**: `faq`, `lead_capture`, `escalation` (plus the runtime `uncertain` bucket).
- **Localized intent tokens absorbed by the model**: DHA, Bahria, marla, kanal, Clifton, Gulshan, North Nazimabad.

### Semantic RAG Pipeline
- **Knowledge base**: 40 hand-curated Karachi real estate FAQs (2026 market data) covering DHA phases, Bahria Town precincts, Clifton, Gulshan, transfer fees, NDC, CGT, scam avoidance, possession, and document checklists.
- **Embedding model**: `all-MiniLM-L6-v2` (384-dim).
- **Vector index**: FAISS `IndexFlatL2`, top-k = 3 retrieval, persisted to `backend/data/faiss_index.bin` and `faiss_texts.pkl`.
- **Generative model**: `gemini-2.5-flash` with `temperature=0.0` and a strict system instruction that forbids external knowledge and hallucinations.
- **Failure routing**: All Gemini/FAISS exceptions return a graceful string error rather than crashing the FastAPI worker.

---

## Verified Project Directory Tree

```
SupportIQ/
├── backend/
│   ├── .env                          # Local secrets (gitignored)
│   ├── requirements.txt              # Pinned dependency ledger
│   ├── app/
│   │   ├── database.py               # SQLite engine + session factory
│   │   ├── main.py                   # FastAPI app, CORS, static mount, page routes
│   │   ├── models.py                 # SQLAlchemy: Listing, Lead, Conversation
│   │   ├── data/                     # (empty placeholder)
│   │   ├── ml/
│   │   │   ├── classifier.py         # Intent prediction + preprocessing
│   │   │   ├── price_model.py        # Train + predict_price()
│   │   │   ├── rag.py                # FAISS + Gemini RAG pipeline
│   │   │   └── verify_scaling.py     # Scaling regression checks
│   │   └── routes/
│   │       ├── admin.py              # /api/admin/* (admin oversight)
│   │       ├── chatbot.py            # /api/chat, /api/history/{session_id}
│   │       ├── listings.py           # /listings CRUD
│   │       └── predictor.py          # /predict-price
│   ├── data/
│   │   ├── Cleaned_Data.csv          # Price training set (~16,850 rows)
│   │   ├── intent_dataset.csv        # Intent training set (~2,100 rows)
│   │   ├── faiss_index.bin           # Persisted FAISS vector index
│   │   └── faiss_texts.pkl           # Persisted KB text corpus
│   ├── models/
│   │   ├── classifier.pkl            # Trained intent pipeline
│   │   ├── price_model.pkl           # Trained price estimator
│   │   ├── feature_columns.pkl       # Training column order
│   │   ├── label_encoder.pkl         # Intent label encoder
│   │   └── median_price.pkl          # Fallback baseline price
│   └── venv/                         # Local virtualenv (gitignored)
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   ├── base.css              # Deep Blue theme tokens + layout
│   │   │   └── chat.css              # Chat bubble + widget styles
│   │   └── js/
│   │       ├── admin.js              # Admin dashboard polling + actions
│   │       ├── chat.js               # Widget session + sub-3s polling
│   │       ├── listings.js           # Listings page logic
│   │       └── predictor.js          # Predictor form + result rendering
│   └── templates/
│       ├── base.html                 # Layout shell
│       ├── index.html                # Landing page
│       ├── listings.html             # Public listings
│       ├── predictor.html            # Price predictor dashboard
│       └── admin.html                # Admin oversight dashboard
├── notebooks/
│   ├── classifier_training.ipynb     # Intent training notebook
│   └── backend/
│       └── models/                   # Training scratch space
├── scripts/
│   └── train_classifier.py           # Reproducible intent pipeline trainer
├── tests/
│   ├── list_models.py
│   ├── test_classifier_live.py
│   └── test_rag.py
├── supportiq.db                      # SQLite DB (gitignored, auto-created)
└── README.md
```

---

## Detailed Setup & Installation Pipeline

### 1. Clone the Repository
```bash
git clone https://github.com/hamzaihsan475/SupportIQ.git
cd SupportIQ
```

### 2. Create a Virtual Environment
```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 5. Environment Configuration
Create `backend/.env` (this file is gitignored):
```env
GEMINI_API_KEY=your_gemini_api_key_here

# --- Admin HTTP Basic Auth (security audit fix #1) ---
# Both values are read on every request, so rotation does not require a restart.
# Replace the demo password below with a strong secret in real deployments.
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-to-a-strong-password
```
Without a Gemini key, `rag.py` will print a warning and any RAG request will return a graceful error string. Without `ADMIN_USERNAME` / `ADMIN_PASSWORD`, **all** `/admin*` routes (page + API) refuse access with HTTP 401.

### 6. Verify Local Data Assets
The repo already ships with:
- `backend/data/Cleaned_Data.csv` — price training corpus.
- `backend/data/intent_dataset.csv` — intent training corpus.
- `backend/data/faiss_index.bin` + `faiss_texts.pkl` — pre-built RAG index.
- `backend/models/*.pkl` — pre-trained model artifacts.

Re-train only if you change the source datasets:
```bash
python scripts/train_classifier.py          # rebuild classifier.pkl
python -m backend.app.ml.price_model        # rebuild price_model.pkl
```

### 7. Launch the Application
```bash
uvicorn backend.app.main:app --reload
```
The local SQLite instance (`supportiq.db`) is created automatically on first boot via `Base.metadata.create_all(bind=engine)` and is excluded from source tracking via `.gitignore`.

### 8. Access the Surfaces
| Surface | URL |
|---|---|
| Landing page | `http://127.0.0.1:8000/` |
| Listings | `http://127.0.0.1:8000/listings` |
| Price predictor | `http://127.0.0.1:8000/predictor` |
| Admin console | `http://127.0.0.1:8000/admin` |
| OpenAPI docs | `http://127.0.0.1:8000/docs` |

---

## Exhaustive API Routing Matrix

| Method | Endpoint | Payload | Description |
|---|---|---|---|
| `GET` | `/` | — | Render landing page (`index.html`) |
| `GET` | `/listings` | — | Render public listings page |
| `GET` | `/predictor` | — | Render price predictor dashboard |
| `GET` | `/admin` | — | Render admin oversight dashboard |
| `GET` | `/api/listings` | — | Static demo listings (landing-page helper) |
| `GET` | `/api/locations` | — | Unique addresses from `Cleaned_Data.csv` (autocomplete cache) |
| `GET` | `/listings/` | — | List all listings (DB) |
| `POST` | `/listings/` | `ListingCreate` JSON | Create a new listing |
| `GET` | `/listings/{id}` | — | Fetch a listing by ID |
| `PUT` | `/listings/{id}` | `ListingUpdate` JSON | Partial update of a listing |
| `DELETE` | `/listings/{id}` | — | Delete a listing |
| `POST` | `/predict-price` | `{ address, bedrooms, bathrooms, area }` | Run hybrid ML pricing pipeline |
| `POST` | `/api/chat` | `{ message, session_id }` | Stateful chat: intent → lead/escalate/RAG |
| `GET` | `/api/history/{session_id}` | — | Poll conversation history for a session |
| `GET` | `/api/admin/listings` | — | Admin view of all listings |
| `POST` | `/api/admin/listings` | `ListingCreate` JSON | Create a listing from the admin panel |
| `GET` | `/api/admin/leads` | — | List all captured leads |
| `GET` | `/api/admin/conversations` | — | Conversations grouped by `session_id` |
| `GET` | `/api/admin/escalated` | — | Escalated conversations grouped by `session_id` |
| `POST` | `/api/admin/resolve/{session_id}` | — | Mark a session as resolved |
| `POST` | `/api/admin/send-message` | `{ session_id, message_text }` | Agent → user takeover message |
| `GET` | `/api/admin/stats` | — | Aggregated system metrics |

---

## Known Engineering Constraints & Gotchas

- [ ] **Polling path is canonical.** Frontend polling **must** hit `GET /api/history/{session_id}`. The legacy `/api/chat/history/` prefix does not exist — any client calling it will receive a 404.
- [ ] **No TensorFlow / `tf-keras` allowed.** The runtime forces `USE_TORCH=1`, `AA_IMPORT_TENSORFLOW=0`, and `FORCE_TF_AVAILABLE=0` to bypass protobuf binary conflicts. Adding TF packages will break the embedding model loader.
- [ ] **Gemini model is fixed to `gemini-2.5-flash`.** The Pakistan free tier quota only covers this model. Switching to `gemini-1.5-*` or `gemini-pro` will trigger 429 / quota errors.
- [ ] **`sentence-transformers` must remain on PyTorch backend.** Do not add a `tensorflow` extras_require; the project pins the PyTorch pathway explicitly.
- [ ] **In-memory `SESSION_STORE` lives in the FastAPI process.** Multi-worker deployments (e.g., `--workers 4`) will fragment session state — escalate to a Redis-backed store before scaling horizontally.
- [ ] **SQLite is single-writer.** Suitable for development and small-scale single-instance deploys. Migrate to PostgreSQL before production multi-tenant rollout.
- [ ] **FAISS index is local.** It is built and persisted at `backend/data/faiss_index.bin` on first run. Treat this file as build artifact + source of truth (it is committed in-repo).
- [ ] **Address dictionary is intentionally narrow.** Only DHA/Defence, Bahria, and Gulshan tokens are auto-mapped; unknown addresses fall back to a median price with a per-token multiplier.
- [ ] **Confidence threshold is `0.40`.** Scores below this are downgraded to `uncertain` and routed through the RAG fallback rather than committed to `lead_capture` or `escalation`.

---

## Future Strategic Roadmap

- **Production WhatsApp Business API integration** — replace the polling-based widget with native WhatsApp Cloud API webhooks for two-way messaging at scale.
- **Multi-tenant agency isolation & auth** — promote the existing `agency_id` column into a full JWT-based auth layer with row-level scoping across `listings`, `leads`, and `conversations`.
- **Cloud deployment runbooks** — first-class deploy guides for Railway, Azure App Service, and Fly.io, including managed PostgreSQL, persistent FAISS storage, and environment-secret rotation.
- **Roman Urdu localized translation layer via Gemini** — on-the-fly transliteration pipeline that lets customers converse in Roman Urdu and receive responses in their preferred language while preserving the strict RAG grounding contract.
- **Horizontal scaling for the chatbot** — move `SESSION_STORE` to Redis, add a worker queue for outbound notifications, and enable Uvicorn `--workers` safely.
- **Observability** — structured logging, Prometheus metrics, and a lightweight analytics dashboard for intent distribution and RAG hit rates.