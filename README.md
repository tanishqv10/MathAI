# MathAI v2

AI-powered mathematical assistant with grounded explanations, real-time streaming, and full observability.

## ✨ Features

- **Accurate Math**: SymPy ensures mathematically correct results (no hallucinations)
- **Grounded Explanations**: LLM explains but doesn't compute
- **Real-time Streaming**: See answers instantly, explanations stream in
- **Smart Caching**: Repeated queries return instantly
- **Parallel Execution**: Compute and RAG run simultaneously
- **Full Observability**: LangFuse tracing for debugging and evaluation
- **Beautiful Frontend**: Modern Next.js UI with LaTeX rendering

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                               │
│          "differentiate sin(x^2) with respect to x"              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Cache Check                                 │
│           If cached → Return instantly (0ms)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ (cache miss)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    1. LLM Router                                 │
│        Classifies → differentiate, integrate, simplify, solve    │
│        Extracts → expression, variable, assumptions              │
│        Model: gpt-4o-mini (fast, lightweight)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │      PARALLEL             │
              ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐
│  2. SymPy Compute    │    │   3. RAG Retrieval   │
│  Authoritative math  │    │  Semantic search     │
│  Result: 2*x*cos(x²) │    │  Knowledge chunks    │
└──────────┬───────────┘    └──────────┬───────────┘
           │                           │
           └─────────────┬─────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                4. LLM Explanation (Streaming)                    │
│         Explains the SymPy result (no new computation)           │
│         Grounded by: query + routing + result + RAG chunks       │
│         Model: gpt-4o-mini                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Response + Cache                              │
│         ✓ Answer: 2*x*cos(x²) (from SymPy)                       │
│         ✓ Explanation: Streamed step-by-step                    │
│         ✓ Cached for instant repeat queries                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- (Optional) LangFuse account for observability

### 1. Backend Setup

```bash
cd MathAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config.example.txt .env
# Edit .env with your API keys
```

### 2. Frontend Setup

```bash
cd mathai-frontend

# Install dependencies
npm install --legacy-peer-deps

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 3. Run the Application

**Terminal 1 - Backend:**
```bash
cd MathAI
source venv/bin/activate
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd mathai-frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## 📡 API Endpoints

### POST `/solve`

Standard endpoint for math queries.

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{"query": "integrate x^2 * e^x dx"}'
```

**Response:**
```json
{
  "success": true,
  "query": "integrate x^2 * e^x dx",
  "operation": "integrate",
  "answer": "(x**2 - 2*x + 2)*exp(x)",
  "latex_answer": "\\left(x^{2} - 2 x + 2\\right) e^{x}",
  "explanation": "Step-by-step explanation...",
  "assumptions": [],
  "citations": ["integrate_0", "integrate_1"]
}
```

### POST `/solve/stream`

Streaming endpoint for real-time responses (used by frontend).

Returns Server-Sent Events:
1. `{"type": "answer", "data": {...}}` - Answer arrives first
2. `{"type": "explanation", "data": "token"}` - Explanation streams in
3. `{"type": "done"}` - Complete

### GET `/health`

Health check with LangFuse status.

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "langfuse_enabled": true
}
```

## ⚡ Performance Optimizations

| Optimization | Impact |
|-------------|--------|
| **Smart Caching** | Repeated queries: **0ms** |
| **Parallel Execution** | Compute + RAG run together: saves **~1s** |
| **Streaming** | Answer appears in **~2s**, explanation streams |
| **gpt-4o-mini** | Faster and cheaper than gpt-4o |

### Typical Latency

| Query Type | Time |
|------------|------|
| First query (cold) | ~5-8s |
| Cached query | **<10ms** |
| With streaming | Answer in ~2s, full response ~8s |

## 📊 LangFuse Observability

When configured, MathAI traces every request:

| Span | Metrics Captured |
|------|-----------------|
| **math_router** | Latency, tokens, confidence |
| **sympy_compute** | Execution time, success/failure |
| **rag_retrieval** | Chunk IDs, relevance scores |
| **llm_explanation** | Token usage, cost, latency |

### Setup LangFuse

1. Create account at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Add to `.env`:
   ```
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
   LANGFUSE_SECRET_KEY=sk-lf-xxxxx
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

## 📁 Project Structure

```
MathAI/
├── MathAI/                    # Backend
│   ├── app.py                 # FastAPI application
│   ├── core/
│   │   ├── models.py          # Pydantic data models
│   │   ├── router.py          # LLM-based query router
│   │   ├── compute.py         # SymPy computation engine
│   │   ├── rag.py             # RAG retrieval system
│   │   ├── explainer.py       # LLM explanation generator
│   │   ├── pipeline.py        # Main orchestrator (caching, parallel)
│   │   └── instrumentation.py # LangFuse integration
│   ├── data/
│   │   └── vectordb/          # ChromaDB storage
│   ├── requirements.txt
│   └── .env                   # Environment variables
│
└── mathai-frontend/           # Frontend
    ├── app/
    │   ├── page.tsx           # Main UI with streaming
    │   ├── layout.tsx
    │   └── globals.css
    ├── package.json
    └── .env.local             # Frontend config
```

## 🔧 Supported Operations

| Operation | Example Queries |
|-----------|-----------------|
| **Differentiate** | "find the derivative of ln(x)", "d/dx sin(x^2)" |
| **Integrate** | "integrate e^x * cos(x)", "find antiderivative of 1/x" |
| **Simplify** | "simplify (x^2-1)/(x-1)", "expand (a+b)^3" |
| **Solve** | "solve x^2 + 2x - 3 = 0", "find roots of x^3 - x" |

## 🧪 Development

### Running Tests

```bash
cd MathAI
pytest tests/ -v
```

### Debug Mode

Set `MATHAI_ENV=development` to enable debug endpoints:

- `POST /debug/route` - See routing decision
- `POST /debug/compute` - See compute result

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ROUTER_MODEL` | No | Router model (default: gpt-4o-mini) |
| `EXPLAINER_MODEL` | No | Explainer model (default: gpt-4o-mini) |
| `LANGFUSE_ENABLED` | No | Enable LangFuse (default: true) |
| `LANGFUSE_PUBLIC_KEY` | No | LangFuse public key |
| `LANGFUSE_SECRET_KEY` | No | LangFuse secret key |
| `LANGFUSE_HOST` | No | LangFuse host URL |
| `PORT` | No | Server port (default: 8000) |

