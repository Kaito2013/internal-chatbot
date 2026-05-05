"""
Script nạp documents vào Vector DB.
Hỗ trợ: DOCX, TXT, PDF (skip with warning).

Usage:
    python -m scripts.ingest --source ./data/documents --recreate --limit 100
"""
import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.db.vector import VectorDB
from app.rag.embedding import AsyncEmbeddingService
from app.rag.chunker import SmartChunker


def read_docx(file_path: str) -> str:
    """
    Đọc nội dung file DOCX.

    Args:
        file_path: Đường dẫn file

    Returns:
        Nội dung text của document
    """
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs]
        return '\n'.join(paragraphs)
    except ImportError:
        print(f"  [WARNING] python-docx not installed, skipping {file_path}")
        return ""


def read_txt(file_path: str) -> str:
    """
    Đọc nội dung file TXT.

    Args:
        file_path: Đường dẫn file

    Returns:
        Nội dung text của file
    """
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    print(f"  [WARNING] Cannot decode {file_path}, trying with errors='ignore'")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def read_pdf_warning(file_path: str) -> str:
    """
    Placeholder cho PDF reading - trả về warning.

    Args:
        file_path: Đường dẫn file

    Returns:
        Empty string
    """
    print(f"  [WARNING] PDF parsing not implemented, skipping {file_path}")
    return ""


def load_file(file_path: str) -> Optional[str]:
    """
    Load file và trả về nội dung text.

    Args:
        file_path: Đường dẫn file

    Returns:
        Nội dung text hoặc None nếu unsupported format
    """
    ext = Path(file_path).suffix.lower()

    if ext == '.docx':
        return read_docx(file_path)
    elif ext == '.txt':
        return read_txt(file_path)
    elif ext == '.pdf':
        return None  # Skip PDF
    else:
        print(f"  [WARNING] Unsupported file type: {ext}, skipping {file_path}")
        return None


def generate_chunk_id(content: str) -> str:
    """
    Generate chunk ID từ content hash.

    Args:
        content: Text content

    Returns:
        Chunk ID string
    """
    return hashlib.sha256(content[:50].encode()).hexdigest()[:16]


async def process_documents(
    documents: List[Dict[str, Any]],
    vector_db: VectorDB,
    embedding_service: AsyncEmbeddingService,
    chunker: SmartChunker,
    batch_size: int = 32
) -> Dict[str, int]:
    """
    Process documents: chunk, embed, và upsert vào Vector DB.

    Args:
        documents: List of documents
        vector_db: VectorDB instance
        embedding_service: Embedding service instance
        chunker: Chunker instance
        batch_size: Batch size cho embedding

    Returns:
        Statistics dict
    """
    stats = {
        "total_docs": len(documents),
        "total_chunks": 0,
        "embedded_chunks": 0,
        "upserted_chunks": 0,
        "failed_chunks": 0
    }

    # Chunk documents
    print("  Chunking documents...")
    chunks = chunker.chunk(documents)
    stats["total_chunks"] = len(chunks)
    print(f"  Created {len(chunks)} chunks")

    if not chunks:
        print("  No chunks to process")
        return stats

    # Embed chunks in batches
    print("  Embedding chunks...")
    all_embeddings = []
    all_chunks = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_texts = [c["content"] for c in batch]

        try:
            embeddings = await embedding_service.embed_batch(batch_texts)
            all_embeddings.extend(embeddings)
            all_chunks.extend(batch)
            stats["embedded_chunks"] += len(batch)
        except Exception as e:
            print(f"  [ERROR] Batch embedding failed: {e}")
            stats["failed_chunks"] += len(batch)

        # Progress indicator
        progress = min(i + batch_size, len(chunks))
        print(f"  Progress: {progress}/{len(chunks)} chunks", end='\r')

    print()  # Newline after progress

    # Upsert to vector DB
    print("  Upserting to Vector DB...")
    points = []

    for chunk, embedding in zip(all_chunks, all_embeddings):
        chunk_id = generate_chunk_id(chunk["content"])
        point = {
            "id": chunk_id,
            "vector": embedding,
            "payload": {
                "content": chunk["content"],
                "chunk_id": chunk_id,
                "source": chunk["source"],
                "metadata": chunk.get("metadata", {})
            }
        }
        points.append(point)

    if points:
        try:
            vector_db.upsert(points)
            stats["upserted_chunks"] = len(points)
        except Exception as e:
            print(f"  [ERROR] Upsert failed: {e}")
            stats["failed_chunks"] = len(points)

    return stats


def find_document_files(source_dir: str, extensions: List[str] = None) -> List[str]:
    """
    Tìm tất cả document files trong directory.

    Args:
        source_dir: Thư mục nguồn
        extensions: List of file extensions (e.g., ['.txt', '.docx'])

    Returns:
        List of file paths
    """
    if extensions is None:
        extensions = ['.txt', '.docx', '.pdf']

    files = []
    source_path = Path(source_dir)

    if not source_path.exists():
        print(f"[ERROR] Source directory does not exist: {source_dir}")
        return files

    for ext in extensions:
        files.extend([str(f) for f in source_path.rglob(f'*{ext}')])

    return sorted(files)


async def main_async(args):
    """Main async function."""
    print(f"=== Document Ingestion Service ===")
    print(f"Source directory: {args.source}")
    print(f"Recreate collection: {args.recreate}")
    print(f"Limit files: {args.limit or 'No limit'}")
    print()

    # Initialize Vector DB
    print("Initializing Vector DB...")
    vector_db = VectorDB()
    if args.recreate:
        print("Recreating collection...")
        vector_db.create_collection(recreate=True)
    print(f"  Connected to Qdrant at {settings.QDRANT_URL}")
    print(f"  Collection: {settings.QDRANT_COLLECTION}")

    # Initialize embedding service
    embedding_service = AsyncEmbeddingService()
    if embedding_service.is_mock:
        print("  Using MOCK embeddings (no OpenAI API key)")
    else:
        print(f"  Using OpenAI: {settings.EMBEDDING_MODEL}")

    # Initialize chunker
    chunker = SmartChunker(
        strategy=args.chunk_strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    print(f"  Chunking strategy: {args.chunk_strategy}")
    print(f"  Chunk size: {chunker.chunk_size}, Overlap: {chunker.chunk_overlap}")
    print()

    # Find files
    print("Scanning for documents...")
    all_files = find_document_files(args.source)

    if not all_files:
        print("No documents found!")
        return

    print(f"Found {len(all_files)} document(s)")

    # Apply limit
    if args.limit:
        all_files = all_files[:args.limit]

    print(f"Processing {len(all_files)} file(s)...")
    print()

    # Load documents
    documents = []
    skipped = 0

    for i, file_path in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] Loading: {file_path}")

        content = load_file(file_path)
        if content is None:
            skipped += 1
            continue

        content = content.strip()
        if not content:
            print(f"  [WARNING] Empty file: {file_path}")
            skipped += 1
            continue

        doc = {
            "content": content,
            "source": os.path.basename(file_path),
            "metadata": {
                "file_path": str(file_path),
                "file_size": os.path.getsize(file_path)
            }
        }
        documents.append(doc)
        print(f"  Loaded {len(content)} characters")

    print()
    print(f"Successfully loaded {len(documents)} document(s), skipped {skipped}")
    print()

    if not documents:
        print("No documents to process!")
        return

    # Process documents
    stats = await process_documents(
        documents=documents,
        vector_db=vector_db,
        embedding_service=embedding_service,
        chunker=chunker,
        batch_size=args.batch_size
    )

    # Print statistics
    print()
    print("=== Ingestion Complete ===")
    print(f"Documents processed: {stats['total_docs']}")
    print(f"Chunks created:      {stats['total_chunks']}")
    print(f"Chunks embedded:    {stats['embedded_chunks']}")
    print(f"Chunks upserted:    {stats['upserted_chunks']}")
    print(f"Chunks failed:      {stats['failed_chunks']}")
    print(f"Total in collection: {vector_db.count()}")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into Vector DB"
    )

    parser.add_argument(
        "--source",
        type=str,
        default="./data/documents",
        help="Source directory containing documents"
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate collection before ingesting"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files to process"
    )

    parser.add_argument(
        "--chunk-strategy",
        type=str,
        choices=["by_paragraph", "by_sentence", "recursive"],
        default="recursive",
        help="Chunking strategy (default: recursive)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size in characters (default from settings)"
    )

    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Chunk overlap in characters (default from settings)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32)"
    )

    args = parser.parse_args()

    # Use settings defaults if not provided
    if args.chunk_size is None:
        args.chunk_size = settings.CHUNK_SIZE
    if args.chunk_overlap is None:
        args.chunk_overlap = settings.CHUNK_OVERLAP

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
