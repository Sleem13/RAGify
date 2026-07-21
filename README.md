# 🤖 RAGify — AI Document Intelligence Platform

![RAGify](https://img.shields.io/badge/Status-Active-success.svg) ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg) ![Next.js](https://img.shields.io/badge/Frontend-Next.js-black.svg) ![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED.svg)

**RAGify** is a powerful, locally-hosted Retrieval-Augmented Generation (RAG) and Data Analytics platform. It allows you to upload documents and spreadsheets, ask intelligent questions, and automatically generate interactive dashboards—all powered by state-of-the-art AI models.

## ✨ Key Features

- 📄 **Universal Document Support**: Upload PDF, DOCX, PPTX, TXT, Excel (XLSX, XLS, CSV), and Images (PNG, JPG).
- 💬 **Intelligent Chat**: Ask natural language questions about your documents. The AI strictly uses your documents as context.
- 📊 **Auto-Generated Dashboards**: Upload Excel/CSV files and instantly get professional, interactive charts and insights.
- ⚡ **Lightning Fast**: Uses FAISS for sub-millisecond vector similarity search.
- 🔎 **Hybrid Retrieval**: Combines semantic similarity with BM25-style lexical ranking and source-aware context selection.
- 🔒 **Privacy First**: Your documents are chunked, embedded, and stored locally on your machine.
- 🌐 **Multi-Language UI**: Full support for English and Arabic with dynamic RTL/LTR layouts.
- 🐳 **One-Click Deployment**: Fully containerized with Docker for seamless deployment anywhere.

---

## RAG pipeline

The backend follows the staged SimpleRAG architecture while retaining RAGify's richer file support:

1. `services/document_processor.py` loads PDF, Office, image, text, and tabular files and creates metadata-rich chunks.
2. `services/preprocessing.py` normalizes text for lexical search while preserving negation and multilingual tokens.
3. `services/vector_db.py` persists MiniLM embeddings in FAISS and combines semantic and BM25-style scores.
4. `services/retrieval.py` selects diverse results, numbers sources, validates conversation history, and builds a grounded prompt.
5. `services/llm_manager.py` sends the grounded prompt through the configured provider fallback chain.

## 🚀 Getting Started

The easiest way to run RAGify is using Docker. You don't need to install Python, Node.js, or any other dependencies.

### Streamlit demo

If you want a lightweight visual demo of the same workflow, you can run the Streamlit app separately:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The demo expects the backend to be available at http://localhost:9999. If your backend runs elsewhere, set the RAGIFY_BACKEND_URL environment variable before launching Streamlit.

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) installed on your machine.
- API Keys for the AI models (both have generous free tiers):
  - [Google Gemini API Key](https://aistudio.google.com/app/apikey)
  - [Groq API Key](https://console.groq.com/keys)

### 2. Installation

Clone the repository and prepare your environment variables:

```bash
git clone https://github.com/your-username/RAGify.git
cd RAGify

# Create your .env file
cp .env.example .env
```

Open the `.env` file and paste your API keys.

### 3. Run the Application

Using Docker Compose (or the provided Makefile):

```bash
# Using Makefile
make up

# OR using Docker Compose directly
docker compose up --build -d
```

That's it! 
- The **Frontend** will be available at: [http://localhost:3000](http://localhost:3000)
- The **Backend API** will be available at: [http://localhost:9999/docs](http://localhost:9999/docs)

---

## ☁️ Running on GitHub Codespaces

RAGify is pre-configured to run perfectly in GitHub Codespaces.

1. Go to your repository on GitHub.
2. Go to **Settings > Secrets and variables > Codespaces**.
3. Add two repository secrets:
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
4. Click the `<> Code` button -> **Codespaces** -> **Create codespace on main**.
5. The environment will build automatically, inject your keys, and start the Docker containers.

---

## 🛠️ Architecture

- **Frontend**: Next.js 16, Tailwind CSS, Lucide Icons, React Markdown.
- **Backend**: FastAPI, LangChain, FAISS, Pandas, PyMuPDF.
- **AI Models**: 
  - *Embeddings*: `all-MiniLM-L6-v2` (runs locally)
  - *LLMs*: Automatic fallback chain across Gemini 2.5 Flash/Flash-Lite and Groq GPT-OSS 20B/120B.

---

## 🛑 Useful Commands (Makefile)

| Command | Description |
|---------|-------------|
| `make up` | Start all services in the background |
| `make down` | Stop all services |
| `make logs` | View live logs from all containers |
| `make reset` | ⚠️ **Wipe all indexed data** and restart fresh |
| `make status` | Check container status |

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
