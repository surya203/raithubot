import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    page_number: int | None
    chunk_index: int


def chunk_pages(
    pages: list[tuple[int | None, str]],
    size: int = 1000,
    overlap: int = 150,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    buffer = ""
    buffer_page: int | None = None
    for page_number, text in pages:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        for paragraph in paragraphs:
            if buffer and len(buffer) + len(paragraph) + 1 > size:
                chunks.append(TextChunk(buffer.strip(), buffer_page, len(chunks)))
                tail = buffer[-overlap:].strip()
                buffer = f"{tail}\n{paragraph}".strip()
                buffer_page = page_number
            elif buffer:
                buffer = f"{buffer}\n{paragraph}".strip()
            else:
                buffer = paragraph
                buffer_page = page_number
            while len(buffer) > size:
                chunks.append(TextChunk(buffer[:size].strip(), buffer_page, len(chunks)))
                buffer = buffer[size - overlap :].strip()
                buffer_page = page_number
    if buffer.strip():
        chunks.append(TextChunk(buffer.strip(), buffer_page, len(chunks)))
    return [chunk for chunk in chunks if chunk.content]
