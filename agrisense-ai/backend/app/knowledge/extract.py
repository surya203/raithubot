import io
import re

from pypdf import PdfReader

from app.errors import IntegrationError


def extract_pages(filename: str, content_type: str, data: bytes) -> list[tuple[int | None, str]]:
    lowered = filename.lower()
    if lowered.endswith(".pdf") or content_type == "application/pdf":
        return _pdf_pages(data)
    if content_type in {"text/plain", "text/markdown"} or lowered.endswith((".txt", ".md")):
        return [(1, clean_text(data.decode("utf-8", errors="replace")))]
    raise IntegrationError("Upload a PDF, plain text, or Markdown document.")


def _pdf_pages(data: bytes) -> list[tuple[int | None, str]]:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise IntegrationError("The PDF could not be read.") from exc
    pages: list[tuple[int | None, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise IntegrationError(f"Text could not be read from page {index}.") from exc
        pages.append((index, clean_text(text)))
    return pages


def clean_text(text: str) -> str:
    without_nulls = text.replace("\x00", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in without_nulls.splitlines()]
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return cleaned.strip()
