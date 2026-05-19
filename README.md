# 🧠 CodeMind - Intelligent Code Review Agent

An AI-powered intelligent code review system built using Hindsight, CascadeFlow, Ollama, and Gradio.

This project demonstrates:
- persistent AI memory
- runtime intelligence
- multi-model orchestration
- adaptive code review behavior
- local-first AI systems
- production-style AI architecture

The agent performs intelligent code reviews with:
- persistent engineering memory
- reflection-based learning
- semantic memory recall
- complexity-aware routing
- automatic model escalation

---

# 🚀 Features

- 🔍 AI-powered code reviews
- 🧠 Persistent memory with Hindsight
- ⚡ Runtime intelligence using CascadeFlow
- 🔀 Multi-model routing
- 📜 Review history tracking
- 🧩 Reflection-based learning
- 🛡️ Security analysis
- 🏗️ Architecture review
- 💾 Local-first architecture
- 🐳 Docker-based Hindsight MCP server
- ⚙️ Environment variable configuration
- ⏱️ Timeout protection
- 🚦 Complexity-aware routing
- 💡 Adaptive review behavior
- 📚 Semantic memory recall
- 🧠 Reflection system
- 🔄 Review caching
- 🛠️ Health checks
- 🔒 Async memory locking

---

# 🏗️ Architecture

```text
User
  ↓
Gradio UI
  ↓
CascadeFlow Runtime Intelligence
  ├── Qwen2.5-Coder 7B
  └── Qwen2.5-Coder 14B
  ↓
Hindsight MCP Server
  ↓
Embedded PostgreSQL
  ↓
Persistent Agent Memory
```

---

# 🧠 Runtime Intelligence

The system automatically routes requests based on complexity.

## Fast Reviews
Handled by:
- qwen2.5-coder:7b

Used for:
- lightweight reviews
- syntax analysis
- simple fixes
- quick feedback
- smaller diffs

---

## Deep Reasoning Reviews
Escalated to:
- qwen2.5-coder:14b

Used for:
- architecture analysis
- security reviews
- performance optimization
- large diffs
- deep reasoning
- complex debugging

---

# 🧠 Persistent Memory

The agent remembers:
- recurring bugs
- developer preferences
- architecture patterns
- security issues
- performance bottlenecks
- previous review observations

Memory persists across sessions using:
- Hindsight MCP
- embedded PostgreSQL
- semantic retrieval
- reflection-based recall

---

# 📦 Tech Stack

| Layer | Technology |
|---|---|
| UI | Gradio |
| Runtime Intelligence | CascadeFlow |
| Memory System | Hindsight |
| LLM Runtime | Ollama |
| Models | Qwen2.5-Coder 7B + 14B |
| Database | Embedded PostgreSQL |
| Deployment | Docker |
| Language | Python |

---

# 📂 Project Structure

```text
CODE-REVIEW-AGENT/
│
├── reviewer.py
├── README.md
├── requirements.txt
├── .gitignore
├── .env
├── .env.example
├── LICENSE
├── article.md
│
└── docs/
```

---

# ⚙️ Installation

## 1. Clone Repository

```bash
git clone YOUR_REPOSITORY_URL
cd CODE-REVIEW-AGENT
```

---

## 2. Create Virtual Environment

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 📦 Requirements

Example `requirements.txt`

```txt
gradio
cascadeflow
hindsight-client
requests
litellm
fastembed
python-dotenv
```

---

# 🦙 Install Ollama

Install Ollama:

https://ollama.com

---

## Pull Models

```bash
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
```

---

## Start Ollama

```bash
ollama serve
```

---

# 🐳 Setup Hindsight MCP Server

Run:

```bash
docker run -it \
  -p 8888:8888 \
  -p 9999:9999 \
  -v $HOME/.hindsight-data:/home/hindsight/.pg0 \
  -e HINDSIGHT_API_LLM_PROVIDER=ollama \
  -e HINDSIGHT_API_LLM_MODEL=qwen2.5-coder:7b \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  --restart unless-stopped \
  --name hindsight-mcp \
  ghcr.io/vectorize-io/hindsight:latest
```

---

# ▶️ Run The Application

```bash
python reviewer.py
```

Open:

```text
http://127.0.0.1:7860
```

---

# 🔧 Environment Variables

Create `.env`

Example:

```env
HINDSIGHT_URL=http://localhost:8888
OLLAMA_URL=http://localhost:11434

BANK_ID=code-review-memory

REQUEST_TIMEOUT=180

MAX_MEMORY_ITEMS=8
MAX_REFLECTION_ITEMS=5
```

---

# 📜 Example Workflow

1. Paste code or git diff
2. Agent estimates complexity
3. CascadeFlow selects model
4. Hindsight recalls previous memory
5. Review is generated
6. Observations are retained
7. Future reviews improve over time

---

# 🧠 Reflection System

The agent periodically reflects on previous reviews to identify:
- recurring engineering issues
- architecture weaknesses
- performance bottlenecks
- security mistakes
- coding patterns

This creates adaptive review behavior over time.

---

# 🛡️ Safety & Reliability Features

- Async memory locking
- Timeout protection
- Health checks
- Review caching
- Local inference
- Persistent storage
- Error handling
- Complexity-aware routing

---

# 🚀 Future Improvements

- GitHub PR integration
- Streaming review generation
- Team memory spaces
- Multi-language embeddings
- VSCode extension
- CI/CD integration
- Cloud deployment
- RAG-enhanced codebase understanding
- Automatic PR comments
- Team collaboration memory
- Enterprise memory spaces

---

# 🧪 Recommended Hardware

## Minimum
- 16GB RAM

## Recommended
- 32GB RAM

---

# 🐳 Docker Workflow

## Start Ollama

```bash
ollama serve
```

---

## Start Hindsight MCP

```bash
docker start hindsight-mcp
```

---

## Run App

```bash
python reviewer.py
```

---

# 🧠 Why This Project Matters

Traditional code review tools:
- forget previous reviews
- lack adaptive behavior
- use static workflows

This project introduces:
- persistent engineering memory
- runtime model orchestration
- reflection-based learning
- adaptive review intelligence

creating a more intelligent software engineering assistant.

---

# 📄 License

MIT License

---

# 🙌 Acknowledgements

- Hindsight
- CascadeFlow
- Ollama
- Gradio
- Qwen Team

---

# ⭐ Project Goals

This project demonstrates:
- persistent AI memory
- runtime intelligence
- model orchestration
- adaptive agent behavior
- local-first AI systems
- production-grade architecture

built for modern AI engineering workflows and hackathon experimentation.