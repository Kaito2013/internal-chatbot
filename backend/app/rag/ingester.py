"""
Document Ingester - Xử lý documents từ raw text sang vector database.
Luồng: Document -> Chunking -> Embedding -> Upsert to Vector DB
"""
import asyncio
import uuid
import time
import logging
from typing import List, Dict, Any, Optional

from ..config import settings
from ..db.vector import VectorDB
from .embedding import AsyncEmbeddingService
from .chunker import SmartChunker

logger = logging.getLogger(__name__)


class DocumentIngester:
    """
    Document Ingester xử lý documents vào vector database.
    
    Hỗ trợ:
    - Batch processing để tối ưu memory
    - Progress tracking
    - Async embedding và upsert
    """

    def __init__(
        self,
        vector_db: VectorDB,
        embedding_service: AsyncEmbeddingService,
        chunker: SmartChunker
    ):
        """
        Khởi tạo DocumentIngester.

        Args:
            vector_db: VectorDB instance để upsert documents
            embedding_service: AsyncEmbeddingService để tạo embeddings
            chunker: SmartChunker để chia documents thành chunks
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.chunker = chunker
        
        logger.info(
            f"DocumentIngester initialized: chunker={chunker.strategy}, "
            f"chunk_size={chunker.chunk_size}"
        )

    async def ingest(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest documents vào vector database.
        
        Luồng xử lý:
        1. Chunk documents (sync - nhanh)
        2. Embed chunks (async - batch)
        3. Upsert to Vector DB (async - batch)

        Args:
            documents: List of dicts với keys: content, source, metadata
            batch_size: Số chunks xử lý mỗi batch (embed + upsert)
            show_progress: Có hiển thị progress không

        Returns:
            Dict chứa:
            - total_documents: số documents đã xử lý
            - total_chunks: số chunks đã tạo
            - duration: thời gian xử lý (giây)
            - chunks_per_second: throughput
        """
        if not documents:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "duration": 0,
                "chunks_per_second": 0
            }
        
        start_time = time.time()
        
        # Bước 1: Chunking (sync operation - nhanh)
        logger.info(f"Chunking {len(documents)} documents...")
        chunks = self.chunker.chunk(documents)
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        
        if not chunks:
            return {
                "total_documents": len(documents),
                "total_chunks": 0,
                "duration": time.time() - start_time,
                "chunks_per_second": 0
            }
        
        # Bước 2: Embedding + Upsert theo batch
        total_embedded = 0
        total_upserted = 0
        
        # Tạo batches
        num_batches = (len(chunks) + batch_size - 1) // batch_size
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            if show_progress:
                logger.info(
                    f"Processing batch {batch_num}/{num_batches} "
                    f"({len(batch_chunks)} chunks)"
                )
            
            # Embed batch
            texts = [c["content"] for c in batch_chunks]
            embeddings = await self.embedding_service.embed_batch(texts)
            
            # Chuẩn bị points cho upsert
            points = []
            for chunk, embedding in zip(batch_chunks, embeddings):
                point_id = chunk.get("chunk_id", str(uuid.uuid4()))
                
                points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "content": chunk["content"],
                        "chunk_id": point_id,
                        "source": chunk.get("source", "unknown"),
                        "metadata": chunk.get("metadata", {}),
                        # Lưu thêm thông tin vị trí chunk
                        "char_count": len(chunk["content"]),
                        "word_count": len(chunk["content"].split())
                    }
                })
            
            # Upsert batch
            self.vector_db.upsert(points)
            total_upserted += len(points)
            total_embedded += len(embeddings)
            
            # Small delay để tránh rate limit (nếu dùng real API)
            if self.embedding_service.is_mock is False:
                await asyncio.sleep(0.1)
        
        duration = time.time() - start_time
        
        result = {
            "total_documents": len(documents),
            "total_chunks": total_upserted,
            "duration": round(duration, 2),
            "chunks_per_second": round(total_upserted / duration, 2) if duration > 0 else 0
        }
        
        logger.info(
            f"Ingestion complete: {result['total_chunks']} chunks from "
            f"{result['total_documents']} documents in {result['duration']}s "
            f"({result['chunks_per_second']} chunks/s)"
        )
        
        return result

    async def ingest_single(
        self,
        content: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest một document đơn lẻ.
        
        Args:
            content: Nội dung document
            source: Nguồn document (file path, URL, etc.)
            metadata: Additional metadata

        Returns:
            Dict với thông tin chunks đã tạo
        """
        document = {
            "content": content,
            "source": source,
            "metadata": metadata or {}
        }
        
        return await self.ingest(documents=[document])

    def ingest_sync(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Sync wrapper cho ingest (sử dụng trong sync contexts như CLI).
        
        Args:
            documents: List of documents
            batch_size: Batch size

        Returns:
            Dict với thống kê ingestion
        """
        return asyncio.run(self.ingest(documents, batch_size))


class BatchIngester:
    """
    Batch Ingester cho việc ingest nhiều files hoặc từ nhiều sources.
    Hỗ trợ:
    - Ingest từ directory
    - Ingest từ list of file paths
    - Parallel processing
    """

    def __init__(
        self,
        vector_db: VectorDB,
        embedding_service: AsyncEmbeddingService,
        chunker: SmartChunker,
        max_concurrent: int = 3
    ):
        """
        Khởi tạo BatchIngester.

        Args:
            vector_db: VectorDB instance
            embedding_service: AsyncEmbeddingService
            chunker: SmartChunker
            max_concurrent: Số lượng files xử lý đồng thời
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.chunker = chunker
        self.max_concurrent = max_concurrent
        self._ingester = DocumentIngester(
            vector_db=vector_db,
            embedding_service=embedding_service,
            chunker=chunker
        )

    async def ingest_files(
        self,
        file_paths: List[str],
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Ingest nhiều files.
        
        Args:
            file_paths: List of file paths
            batch_size: Batch size cho embedding

        Returns:
            Dict với tổng hợp thống kê
        """
        import os
        
        total_stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "total_duration": 0,
            "files_processed": 0,
            "files_failed": [],
            "chunks_per_second": 0
        }
        
        # Semaphore để giới hạn concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_file(file_path: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    document = {
                        "content": content,
                        "source": file_path,
                        "metadata": {
                            "file_name": os.path.basename(file_path),
                            "file_size": os.path.getsize(file_path)
                        }
                    }
                    
                    result = await self._ingester.ingest(
                        documents=[document],
                        batch_size=batch_size,
                        show_progress=False
                    )
                    
                    return {"success": True, "result": result}
                    
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    return {"success": False, "error": str(e), "file": file_path}
        
        # Process all files
        tasks = [process_file(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                stats = result["result"]
                total_stats["total_documents"] += stats["total_documents"]
                total_stats["total_chunks"] += stats["total_chunks"]
                total_stats["total_duration"] += stats["duration"]
                total_stats["files_processed"] += 1
            elif isinstance(result, dict):
                total_stats["files_failed"].append(result.get("file", "unknown"))
            else:
                total_stats["files_failed"].append(str(result))
        
        # Calculate overall throughput
        if total_stats["total_duration"] > 0:
            total_stats["chunks_per_second"] = round(
                total_stats["total_chunks"] / total_stats["total_duration"], 2
            )
        
        logger.info(
            f"Batch ingestion complete: {total_stats['files_processed']} files, "
            f"{total_stats['total_chunks']} chunks in {total_stats['total_duration']}s"
        )
        
        return total_stats
