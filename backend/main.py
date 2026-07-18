from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import io
import csv
import json
import secrets
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from services.document_processor import document_processor
from services.vector_db import vector_db
from services.llm_manager import llm_manager
from services.data_analyzer import data_analyzer

app = FastAPI(
    title="RAGify API",
    description="AI-powered document analysis and retrieval system. Upload files, ask questions, get insights.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: Allow Vercel frontend + localhost
frontend_url = os.getenv("FRONTEND_URL", "*")
origins = [frontend_url] if frontend_url != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Supported file types ─────────────────────────────────────────────────────
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# ─── Simple in-memory API key store (persists while server is running) ────────
# In production, store these in a database
_api_keys: set[str] = set()


def _verify_api_key(x_api_key: str | None) -> bool:
    """Returns True if the key is valid OR if no keys have been generated yet."""
    if not _api_keys:
        return True  # Open mode: no key required until first key is generated
    return x_api_key in _api_keys


# ═════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["System"])
def health_check():
    """Health check — returns status and loaded LLM models."""
    return {
        "status": "healthy",
        "app": "RAGify API",
        "version": "2.0.0",
        "loaded_models": llm_manager.available_models,
        "api_key_required": len(_api_keys) > 0,
        "docs": "/docs",
    }


# ═════════════════════════════════════════════════════════════════════════════
#  API KEY MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/generate-api-key", tags=["API Key"])
def generate_api_key():
    """
    Generate a new API key for programmatic access.
    Share this key with developers who want to integrate RAGify into their own projects.
    """
    new_key = "ragify-" + secrets.token_urlsafe(32)
    _api_keys.add(new_key)
    logger.info(f"New API key generated. Total keys: {len(_api_keys)}")
    return {
        "api_key": new_key,
        "message": "Keep this key safe. Use it in the 'X-Api-Key' header for all API requests.",
        "example": {
            "curl": f'curl -X POST https://ragify-backend.loca.lt/chat -H "X-Api-Key: {new_key}" -F "message=What is in my document?"',
            "python": (
                "import requests\n"
                f'headers = {{"X-Api-Key": "{new_key}"}}\n'
                'requests.post("https://ragify-backend.loca.lt/chat", headers=headers, data={"message": "Hello"})'
            )
        }
    }


@app.get("/list-api-keys", tags=["API Key"])
def list_api_keys():
    """List all active API keys (masked for security)."""
    masked = [k[:12] + "..." + k[-4:] for k in _api_keys]
    return {"active_keys": masked, "total": len(_api_keys)}


@app.delete("/revoke-api-key", tags=["API Key"])
def revoke_api_key(api_key: str):
    """Revoke an existing API key."""
    if api_key in _api_keys:
        _api_keys.discard(api_key)
        return {"message": "API key revoked successfully."}
    raise HTTPException(status_code=404, detail="API key not found.")


# ═════════════════════════════════════════════════════════════════════════════
#  FILE UPLOAD & PROCESSING
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/upload", tags=["Documents"])
async def upload_file(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    """
    Upload and process any supported file:
    - **PDF, DOCX, TXT** → Chunked, embedded, stored in local FAISS vector DB (RAG pipeline)
    - **XLSX, XLS, CSV** → Analyzed with Pandas → returns Chart.js-ready JSON for the dashboard

    Supports multiple files — each upload **merges** into the existing knowledge base.
    """
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    contents = await file.read()

    # ── Document files (RAG pipeline) ────────────────────────────────────────
    if document_processor.is_supported(filename):
        try:
            chunks = await document_processor.process_file(contents, filename)
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Processing error: {exc}")

        vector_db.add_chunks(chunks, filename=filename)

        prompt = (
            f"I just uploaded a document named '{filename}' with {len(chunks)} text chunks. "
            "Acknowledge it in one professional sentence and confirm you are ready for questions."
        )
        try:
            summary = await llm_manager.generate_response(prompt)
        except Exception:
            summary = (
                f"✅ '{filename}' has been indexed ({len(chunks)} chunks). "
                "Ask me anything about it!"
            )

        return {
            "filename": filename,
            "status": "processed",
            "type": "document",
            "chunks": len(chunks),
            "message": summary,
        }

    # ── Excel / CSV files (analytics pipeline) ───────────────────────────────
    if ext in EXCEL_EXTENSIONS:
        try:
            analysis = await data_analyzer.analyze_excel(contents, filename)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Analysis error: {exc}")

        return {
            "filename": filename,
            "status": "analyzed",
            "type": "excel",
            "analysis": analysis,
            "message": "✅ Excel data analyzed. Visit the Analytics Dashboard to explore your data.",
        }

    # ── Unsupported ───────────────────────────────────────────────────────────
    raise HTTPException(
        status_code=415,
        detail=(
            f"Unsupported file type '{ext}'. "
            "Supported: PDF, DOCX, TXT, PPTX, PNG, JPG, JPEG, XLSX, XLS, CSV."
        ),
    )


# ═════════════════════════════════════════════════════════════════════════════
#  CHAT (RAG)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/chat", tags=["Chat"])
async def chat(
    message: str = Form(...),
    x_api_key: str | None = Header(default=None),
):
    """
    RAG Chat endpoint.
    1. Embeds the question and retrieves the top-5 most relevant chunks from FAISS.
    2. Sends context + question to the active LLM (auto-fallback across all providers).
    3. Returns the generated answer.

    Works across ALL uploaded documents simultaneously — no need to specify which file.
    """
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ── Retrieve context from FAISS Vector DB ─────────────────────────────────
    context = ""
    try:
        results = vector_db.query(message, top_k=5)
        if results and results.get("matches"):
            context_texts = [
                m["metadata"]["text"]
                for m in results["matches"]
                if m.get("metadata", {}).get("text")
            ]
            context = "\n\n---\n\n".join(context_texts)
    except Exception as exc:
        logger.warning(f"Vector DB query failed (answering without context): {exc}")

    # ── Build prompt ──────────────────────────────────────────────────────────
    if context:
        prompt = (
            "You are a professional AI assistant with access to uploaded documents.\n"
            "Answer the question using ONLY the context provided below.\n"
            "If the answer is not in the context, say: 'I could not find this information in the uploaded documents.'\n"
            "IMPORTANT: Always answer in the exact same language as the user's QUESTION (e.g., if the question is in Arabic, answer in Arabic).\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {message}\n\n"
            "ANSWER:"
        )
    else:
        prompt = (
            "You are a professional AI assistant.\n"
            "No documents have been indexed yet. Answer using your general knowledge.\n"
            "Remind the user they can upload PDF, DOCX, or Excel files for document-specific answers.\n"
            "IMPORTANT: Always answer in the exact same language as the user's QUESTION (e.g., if the question is in Arabic, answer in Arabic).\n\n"
            f"QUESTION: {message}\n\n"
            "ANSWER:"
        )

    # ── Generate response ─────────────────────────────────────────────────────
    try:
        response_text = await llm_manager.generate_response(prompt)
        return {"response": response_text, "context_found": bool(context)}
    except RuntimeError as exc:
        return {
            "response": (
                "⚠️ All AI providers are currently unavailable (quota exceeded). "
                "Please try again in a few minutes."
            ),
            "context_found": False,
            "error": str(exc),
        }


# ═════════════════════════════════════════════════════════════════════════════
#  EXPORT ANALYTICS DATA
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/export", tags=["Export"])
async def export_data(
    format: str = Form("json"),
    data: str = Form(...),
    x_api_key: str | None = Header(default=None),
):
    """
    Export analytics data in multiple formats:
    - **json** → JSON file
    - **csv** → CSV file
    - **xlsx** → Excel file (requires openpyxl)

    Pass the analysis JSON from the frontend as the `data` field.
    """
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data provided.")

    fmt = format.lower().strip()

    # ── JSON export ───────────────────────────────────────────────────────────
    if fmt == "json":
        content = json.dumps(parsed, indent=2, ensure_ascii=False)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=ragify_export.json"},
        )

    # ── CSV export ────────────────────────────────────────────────────────────
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        summary = parsed.get("summary", {})
        columns = summary.get("columns", [])
        writer.writerow(["RAGify Analytics Export"])
        writer.writerow([])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Rows", summary.get("rows_count", "N/A")])
        writer.writerow(["Total Columns", len(columns)])
        writer.writerow(["Insights", parsed.get("insights", "")])
        writer.writerow([])
        writer.writerow(["Detected Columns"] + columns)

        chart = parsed.get("chart_data")
        if chart and chart.get("labels") and chart.get("datasets"):
            writer.writerow([])
            writer.writerow(["Chart Data"])
            writer.writerow(["Label", chart["datasets"][0].get("label", "Value")])
            for label, val in zip(chart["labels"], chart["datasets"][0]["data"]):
                writer.writerow([label, val])

        content = output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ragify_export.csv"},
        )

    # ── XLSX export ───────────────────────────────────────────────────────────
    if fmt == "xlsx":
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            raise HTTPException(status_code=500, detail="openpyxl not installed.")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "RAGify Analytics"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="6366F1")  # indigo

        summary = parsed.get("summary", {})
        columns = summary.get("columns", [])

        # Summary section
        ws.append(["RAGify Analytics Export"])
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([])
        ws.append(["Metric", "Value"])
        for cell in ws[3]:
            cell.font = header_font
            cell.fill = header_fill
        ws.append(["Total Rows", summary.get("rows_count", "N/A")])
        ws.append(["Total Columns", len(columns)])
        ws.append(["Insights", parsed.get("insights", "")])
        ws.append([])
        ws.append(["Detected Columns"])
        ws.append(columns)

        chart = parsed.get("chart_data")
        if chart and chart.get("labels") and chart.get("datasets"):
            ws.append([])
            ws.append(["Chart Data"])
            ws.append(["Label", chart["datasets"][0].get("label", "Value")])
            for label, val in zip(chart["labels"], chart["datasets"][0]["data"]):
                ws.append([label, val])

        # Adjust column widths
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=ragify_export.xlsx"},
        )
    # ── PDF export ───────────────────────────────────────────────────────────
    if fmt == "pdf":
        try:
            from fpdf import FPDF
        except ImportError:
            raise HTTPException(status_code=500, detail="fpdf2 not installed.")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        summary = parsed.get("summary", {})
        columns = summary.get("columns", [])

        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(200, 10, txt="RAGify Analytics Export", ln=1, align="C")
        pdf.ln(10)

        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(200, 10, txt="Summary Metrics", ln=1)
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, txt=f"Total Rows: {summary.get('rows_count', 'N/A')}", ln=1)
        pdf.cell(200, 10, txt=f"Total Columns: {len(columns)}", ln=1)
        pdf.ln(5)

        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(200, 10, txt="Insights", ln=1)
        pdf.set_font("Helvetica", size=12)
        # multi_cell handles line wrapping automatically
        pdf.multi_cell(0, 10, txt=parsed.get("insights", ""))
        pdf.ln(5)

        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(200, 10, txt="Detected Columns", ln=1)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, txt=", ".join(columns))

        content = pdf.output()
        buffer = io.BytesIO(content)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ragify_export.pdf"},
        )

    raise HTTPException(status_code=400, detail=f"Unknown format '{fmt}'. Use: json, csv, xlsx, pdf.")


# ═════════════════════════════════════════════════════════════════════════════
#  RESET KNOWLEDGE BASE
# ═════════════════════════════════════════════════════════════════════════════

@app.delete("/reset", tags=["System"])
def reset_knowledge_base(x_api_key: str | None = Header(default=None)):
    """
    Wipe the entire FAISS vector database.
    All uploaded documents will be forgotten. Use with caution.
    """
    if not _verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    import shutil
    db_path = os.path.join(os.path.dirname(__file__), "services", "..", "vectorstore", "db_faiss")
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        logger.info("FAISS vector database wiped.")
        return {"message": "✅ Knowledge base reset. All documents have been removed."}
    return {"message": "Nothing to reset — no documents were indexed."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999, reload=True)
