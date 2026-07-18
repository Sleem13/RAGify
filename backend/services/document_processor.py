from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import os
import tempfile
import logging
import base64

logger = logging.getLogger(__name__)

# Supported file types and their loader classes
SUPPORTED_EXTENSIONS = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt":  TextLoader,
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PPT_EXTENSIONS = {".pptx"}

class DocumentProcessor:
    """
    Handles loading, chunking, and preparing documents for vector storage.
    Supports PDF, DOCX, TXT, PPTX, and Images (PNG, JPG, JPEG via Vision API).
    """

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    async def process_file(self, file_bytes: bytes, filename: str):
        ext = os.path.splitext(filename)[1].lower()

        if not self.is_supported(filename):
            raise ValueError(
                f"Unsupported file type '{ext}'. Supported: PDF, DOCX, TXT, PPTX, PNG, JPG, JPEG."
            )

        documents = []

        # ── 1. Image Processing (via Gemini Vision) ───────────────────────────
        if ext in IMAGE_EXTENSIONS:
            extracted_text = await self._extract_image_text(file_bytes, ext)
            documents = [Document(page_content=extracted_text, metadata={"source": filename})]

        # ── 2. PowerPoint Processing ──────────────────────────────────────────
        elif ext in PPT_EXTENSIONS:
            extracted_text = self._extract_pptx_text(file_bytes)
            documents = [Document(page_content=extracted_text, metadata={"source": filename})]

        # ── 3. Standard Document Processing (PDF, DOCX, TXT) ──────────────────
        else:
            loader_class = SUPPORTED_EXTENSIONS[ext]
            temp_file_path = None
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_bytes)
                temp_file_path = tmp.name

            try:
                if ext == ".txt":
                    loader = loader_class(temp_file_path, encoding="utf-8")
                else:
                    loader = loader_class(temp_file_path)
                documents = loader.load()
                # Update metadata for all standard docs to just the filename (not temp path)
                for doc in documents:
                    doc.metadata["source"] = filename
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        # ── Chunking ──────────────────────────────────────────────────────────
        chunks = self.text_splitter.split_documents(documents)
        logger.info(
            f"Processed '{filename}': {len(documents)} page(s) → {len(chunks)} chunks."
        )
        return chunks

    async def _extract_image_text(self, file_bytes: bytes, ext: str) -> str:
        """Extract text from an image using Gemini Vision."""
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_key or gemini_key == "your_gemini_key_here":
            raise ValueError("Processing images requires a valid GEMINI_API_KEY in the .env file.")

        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        
        b64_img = base64.b64encode(file_bytes).decode('utf-8')
        mime_type = f"image/{ext.strip('.')}"
        if mime_type == "image/jpg": 
            mime_type = "image/jpeg"

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_key)
        msg = HumanMessage(content=[
            {
                "type": "text", 
                "text": "Extract all text from this image accurately. Describe any charts, diagrams, or visual data in detail. Do not add conversational filler, just the extracted text and descriptions."
            },
            {
                "type": "image_url", 
                "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}
            }
        ])
        
        # We use ainvoke for async call
        response = await llm.ainvoke([msg])
        return response.content

    def _extract_pptx_text(self, file_bytes: bytes) -> str:
        """Extract text from a PowerPoint presentation."""
        try:
            import io
            from pptx import Presentation
        except ImportError:
            raise ValueError("python-pptx is not installed. Run: pip install python-pptx")

        prs = Presentation(io.BytesIO(file_bytes))
        text_runs = []
        for slide_idx, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            if slide_text:
                text_runs.append(f"--- Slide {slide_idx + 1} ---\n" + "\n".join(slide_text))
        
        return "\n\n".join(text_runs)

    @staticmethod
    def is_supported(filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in SUPPORTED_EXTENSIONS or ext in IMAGE_EXTENSIONS or ext in PPT_EXTENSIONS


# Singleton – imported by main.py
document_processor = DocumentProcessor()
