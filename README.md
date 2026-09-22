# Group Expense Splitter

A two-person academic GenAI project that allows groups to track shared expenses, split costs, and settle balances — powered by natural-language expense entry via an LLM.

## Features

- **Create groups** and manage members
- **Add expenses** with payer and participant selection
- **Equal splitting** with correct monetary rounding
- **Balance calculation** — who owes whom
- **Record settlements** and track history
- **Natural-language expense entry** — type *"I paid ₹1200 for dinner for me, Rahul and Aman"* and the AI extracts the structured data
- **AI confirmation UI** — review and confirm AI interpretation before saving

## Tech Stack

| Layer        | Technology                    |
|--------------|-------------------------------|
| Frontend     | React 18 + Vite + TailwindCSS |
| Backend      | Python 3.12 + FastAPI         |
| ORM          | SQLAlchemy 2 + Alembic        |
| Database     | SQLite (dev) / PostgreSQL (prod) |
| AI           | Google Gemini API             |
| Testing BE   | Pytest + HTTPX                |
| Testing FE   | Vitest + React Testing Library|

## Project Structure

```
group-expense-splitter/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, dependencies
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   │   └── ai/       # GenAI integration
│   │   └── db/           # Database setup & migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/             # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/     # API clients
│   │   └── hooks/
│   └── package.json
├── docs/                 # Project documentation
│   ├── IMPLEMENTATION_PLAN.md
│   ├── AI_USAGE_LOG.md
│   ├── decisions/        # ADRs
│   ├── sprints/
│   └── api/
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- A Google Gemini API key (for AI features)

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`.

The API docs are at `http://localhost:8000/docs`.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your values:

```env
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./expense_splitter.db
SECRET_KEY=your_secret_key_here
```

**Never commit `.env` to version control.**

## Development Workflow

This project follows an Agile/Sprint-based methodology:

- Work is tracked in the [Product Backlog](docs/IMPLEMENTATION_PLAN.md#product-backlog)
- Each sprint targets a complete vertical slice
- All GenAI use is logged in [AI_USAGE_LOG.md](docs/AI_USAGE_LOG.md)
- Architectural decisions are documented as [ADRs](docs/decisions/)
- Sprint reports are in [docs/sprints/](docs/sprints/)

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

## Academic Context

This project was developed for **DSC4141** as a two-person team academic project demonstrating:
- Agile/Sprint-based development
- GenAI integration with responsible AI practices
- Clean architecture and separation of concerns
- Comprehensive testing strategy

## License

Academic project — not for commercial use.
