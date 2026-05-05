"""
RAG Pipeline - Điều phối toàn bộ quy trình Retrieval Augmented Generation.
Bao gồm: ingestion (chunk -> embed -> store) và retrieval (search -> rerank).
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging

from ..config import settings
from ..db.vector import VectorDB
from .embedding import AsyncEmbeddingService
from .chunker import SmartChunker
from .ingester import DocumentIngester
from .retriever import HybridRetriever
from .ranker import ResultReranker

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG Pipeline hoàn chỉnh.
    
    Cung cấp 2 luồng chính:
    1. Ingestion: Document -> Chunking -> Embedding -> Vector DB
    2. Retrieval: Query -> Search -> Rerank -> Results
    """

    def __init__(
        self,
        vector_db: Optional[VectorDB] = None,
        embedding_service: Optional[AsyncEmbeddingService] = None,
        chunker: Optional[SmartChunker] = None,
        reranker: Optional[ResultReranker] = None
    ):
        """
        Khởi tạo RAG Pipeline.

        Args:
            vector_db: VectorDB instance (mặc định tạo mới)
            embedding_service: AsyncEmbeddingService instance (mặc định tạo mới)
            chunker: SmartChunker instance (mặc định tạo mới với recursive strategy)
            reranker: ResultReranker instance (mặc định tạo mới)
        """
        self.vector_db = vector_db or VectorDB()
        self.embedding_service = embedding_service or AsyncEmbeddingService()
        self.chunker = chunker or SmartChunker(strategy="recursive")
        self.reranker = reranker or ResultReranker()
        
        # Khởi tạo các components
        self.ingester = DocumentIngester(
            vector_db=self.vector_db,
            embedding_service=self.embedding_service,
            chunker=self.chunker
        )
        
        self.retriever = HybridRetriever(
            vector_db=self.vector_db,
            embedding_service=self.embedding_service
        )
        
        logger.info(
            f"RAG Pipeline initialized: vector_db={self.vector_db.collection_name}, "
            f"embedding_model={self.embedding_service.model}"
        )

    async def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest documents vào vector database.
        
        Luồng xử lý:
        1. Chunk documents
        2. Embed chunks
        3. Upsert vào vector DB

        Args:
            documents: List of dicts với keys: content, source, metadata
            batch_size: Số chunks xử lý mỗi batch
            show_progress: Có hiển thị progress không

        Returns:
            Dict chứa thống kê ingestion (total_chunks, total_documents, duration)
        """
        return await self.ingester.ingest(
            documents=documents,
            batch_size=batch_size,
            show_progress=show_progress
        )

    async def ingest_directory(
        self,
        directory_path: str,
        file_patterns: List[str] = ["*.txt", "*.md", "*.pdf"],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest tất cả files từ một directory.

        Args:
            directory_path: Đường dẫn directory
            file_patterns: Các file patterns cần tìm (glob patterns)
            batch_size: Số chunks xử lý mỗi batch
            show_progress: Có hiển thị progress không

        Returns:
            Dict chứa thống kê ingestion
        """
        import glob
        import os
        
        documents = []
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(directory_path, pattern)):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    documents.append({
                        "content": content,
                        "source": file_path,
                        "metadata": {
                            "file_name": os.path.basename(file_path),
                            "file_size": os.path.getsize(file_path)
                        }
                    })
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
        
        return await self.ingest_documents(
            documents=documents,
            batch_size=batch_size,
            show_progress=show_progress
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        rerank: bool = True,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents cho query.

        Args:
            query: Query string
            limit: Số lượng kết quả cuối cùng sau rerank
            rerank: Có áp dụng reranking không
            score_threshold: Ngưỡng similarity score (trước rerank)

        Returns:
            List of relevant documents đã được sắp xếp theo relevance
        """
        # Bước 1: Vector search - lấy nhiều hơn để có buffer cho rerank
        search_limit = limit * 3 if rerank else limit
        
        results = await self.retriever.retrieve(
            query=query,
            limit=search_limit,
            score_threshold=score_threshold
        )
        
        if not results:
            return []
        
        # Bước 2: Rerank kết quả
        if rerank and len(results) > 1:
            results = await self.reranker.rerank(
                query=query,
                results=results,
                limit=limit
            )
        
        return results

    async def query(
        self,
        query: str,
        limit: int = 5,
        rerank: bool = True,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Query RAG pipeline và trả về kết quả structured.
        
        Args:
            query: Query string
            limit: Số lượng documents trả về
            rerank: Có áp dụng reranking không
            include_context: Có bao gồm combined context không

        Returns:
            Dict với keys:
            - query: original query
            - results: list of relevant documents
            - context: combined context string (nếu include_context=True)
            - num_results: số lượng results
        """
        results = await self.retrieve(
            query=query,
            limit=limit,
            rerank=rerank
        )
        
        response = {
            "query": query,
            "results": results,
            "num_results": len(results)
        }
        
        if include_context:
            # Tạo combined context từ các chunks
            contexts = []
            for r in results:
                payload = r.get("payload", {})
                content = payload.get("content", "")
                if content:
                    contexts.append(content)
            
            response["context"] = "\n\n---\n\n".join(contexts)
        
        return response

    def get_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê về vector database.

        Returns:
            Dict chứa stats (total_documents, collection_name, embedding_dim)
        """
        try:
            count = self.vector_db.count()
            return {
                "total_documents": count,
                "collection_name": self.vector_db.collection_name,
                "embedding_dim": self.vector_db.vector_dim,
                "embedding_model": self.embedding_service.model,
                "chunking_strategy": self.chunker.strategy,
                "chunk_size": self.chunker.chunk_size,
                "chunk_overlap": self.chunker.chunk_overlap
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def delete_by_source(self, source: str) -> int:
        """
        Xóa tất cả documents theo source.
        
        Lưu ý: Qdrant không hỗ trợ delete by payload trực tiếp.
        Cần scan và delete theo ID.

        Args:
            source: Source filter

        Returns:
            Số lượng documents đã xóa
        """
        # Scroll qua tất cả points để tìm matching source
        try:
            from qdrant_client.models import Filter
            
            offset = None
            deleted_count = 0
            
            while True:
                # Scroll points
                results, offset = self.vector_db.client.scroll(
                    collection_name=self.vector_db.collection_name,
                    scroll_filter=Filter(
                        must=[
                            {
                                "key": "payload.source",
                                "match": {"value": source}
                            }
                        ]
                    ),
                    offset=offset,
                    limit=100
                )
                
                if not results:
                    break
                
                # Delete by IDs
                ids_to_delete = [r.id for r in results]
                self.vector_db.client.delete(
                    collection_name=self.vector_db.collection_name,
                    points_selector=ids_to_delete
                )
                deleted_count += len(ids_to_delete)
                
                if offset is None:
                    break
            
            logger.info(f"Deleted {deleted_count} documents from source: {source}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete by source: {e}")
            raise

    async def recreate_collection(self) -> None:
        """
        Xóa và tạo lại collection.
        Cẩn thận: Data sẽ bị mất!
        """
        logger.warning(f"Recreating collection: {self.vector_db.collection_name}")
        self.vector_db.create_collection(recreate=True)
        logger.info("Collection recreated successfully")


class AsyncRAGPipeline(RAGPipeline):
    """
    Async RAG Pipeline với batch processing tối ưu.
    Kế thừa từ RAGPipeline, bổ sung async context manager.
    """
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        # VectorDB client không cần close với QdrantClient
        pass
