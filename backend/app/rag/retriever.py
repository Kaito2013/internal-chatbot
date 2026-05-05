"""
Hybrid Retriever - Kết hợp dense và sparse retrieval.
Dense: Vector similarity search
Sparse: BM25 keyword search (tương lai)
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging

from ..config import settings
from ..db.vector import VectorDB
from .embedding import AsyncEmbeddingService

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid Retriever kết hợp:
    1. Dense retrieval: Vector similarity search
    2. (Future) Sparse retrieval: BM25 keyword search
    
    Kết quả được fusion lại bằng Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        vector_db: VectorDB,
        embedding_service: AsyncEmbeddingService,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        rrf_k: int = 60
    ):
        """
        Khởi tạo HybridRetriever.

        Args:
            vector_db: VectorDB instance
            embedding_service: AsyncEmbeddingService instance
            dense_weight: Trọng số cho dense retrieval (0-1)
            sparse_weight: Trọng số cho sparse retrieval (0-1)
            rrf_k: K parameter cho RRF algorithm
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        
        # Normalize weights
        total = dense_weight + sparse_weight
        self.dense_weight /= total
        self.sparse_weight /= total
        
        logger.info(
            f"HybridRetriever initialized: dense_weight={self.dense_weight}, "
            f"sparse_weight={self.sparse_weight}"
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        return_all_scores: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents cho query sử dụng hybrid search.

        Args:
            query: Query string
            limit: Số lượng kết quả trả về
            score_threshold: Ngưỡng similarity score
            filters: Filter conditions (metadata filtering)
            return_all_scores: Có trả về tất cả scores không

        Returns:
            List of retrieved documents với scores
        """
        # Bước 1: Dense retrieval (vector search)
        dense_results = await self._dense_retrieve(
            query=query,
            limit=limit * 2,  # Lấy nhiều hơn để có buffer
            score_threshold=score_threshold,
            filters=filters
        )
        
        # Bước 2: Sparse retrieval (BM25) - placeholder for future
        sparse_results = await self._sparse_retrieve(
            query=query,
            limit=limit * 2,
            filters=filters
        )
        
        # Bước 3: Fusion kết quả
        if sparse_results:
            fused_results = self._reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                limit=limit
            )
        else:
            # Không có sparse results, chỉ dùng dense
            fused_results = dense_results[:limit]
        
        # Thêm metadata
        for r in fused_results:
            r["search_type"] = "hybrid" if sparse_results else "dense"
        
        return fused_results

    async def _dense_retrieve(
        self,
        query: str,
        limit: int,
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Dense retrieval sử dụng vector similarity.

        Args:
            query: Query string
            limit: Số lượng kết quả
            score_threshold: Ngưỡng score
            filters: Metadata filters

        Returns:
            List of results với dense_score
        """
        # Embed query
        query_vector = await self.embedding_service.embed(query)
        
        # Search in vector DB
        results = self.vector_db.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=filters
        )
        
        # Thêm dense_score
        for r in results:
            r["dense_score"] = r.get("score", 0)
        
        return results

    async def _sparse_retrieve(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sparse retrieval sử dụng BM25 keyword matching.
        
        Hiện tại là placeholder - trả về empty list.
        Sẽ được implement đầy đủ trong tương lai với Elasticsearch
        hoặc Qdrant's sparse vector support.

        Args:
            query: Query string
            limit: Số lượng kết quả
            filters: Metadata filters

        Returns:
            Empty list (placeholder)
        """
        # TODO: Implement BM25 sparse retrieval
        # Có thể sử dụng:
        # - rank_bm25 library
        # - Elasticsearch
        # - Qdrant sparse vectors
        
        return []

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) để combine rankings.
        
        RRF formula: RRF(d) = Σ 1/(k + rank(d))
        
        Args:
            dense_results: Kết quả từ dense retrieval
            sparse_results: Kết quả từ sparse retrieval
            limit: Số lượng kết quả cuối cùng

        Returns:
            Fused and reranked results
        """
        # Tạo dict lưu RRF scores
        rrf_scores: Dict[str, Dict[str, Any]] = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results, 1):
            doc_id = str(result["id"])
            rrf_scores[doc_id] = result.copy()
            rrf_scores[doc_id]["dense_rank"] = rank
            rrf_scores[doc_id]["rrf_score"] = (
                self.dense_weight * (1 / (self.rrf_k + rank))
            )
        
        # Process sparse results
        for rank, result in enumerate(sparse_results, 1):
            doc_id = str(result["id"])
            if doc_id in rrf_scores:
                rrf_scores[doc_id]["sparse_rank"] = rank
                rrf_scores[doc_id]["rrf_score"] += (
                    self.sparse_weight * (1 / (self.rrf_k + rank))
                )
            else:
                rrf_scores[doc_id] = result.copy()
                rrf_scores[doc_id]["sparse_rank"] = rank
                rrf_scores[doc_id]["rrf_score"] = (
                    self.sparse_weight * (1 / (self.rrf_k + rank))
                )
        
        # Sort theo RRF score
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        return sorted_results[:limit]

    async def retrieve_by_source(
        self,
        query: str,
        source: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents từ một source cụ thể.

        Args:
            query: Query string
            source: Source filter
            limit: Số lượng kết quả

        Returns:
            List of results từ specified source
        """
        filters = {
            "must": [
                {
                    "key": "payload.source",
                    "match": {"value": source}
                }
            ]
        }
        
        return await self.retrieve(
            query=query,
            limit=limit,
            filters=filters
        )

    async def retrieve_by_metadata(
        self,
        query: str,
        metadata_filter: Dict[str, Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents với metadata filtering.

        Args:
            query: Query string
            metadata_filter: Metadata filter conditions
            limit: Số lượng kết quả

        Returns:
            List of filtered results
        """
        # Build filter
        must_clauses = []
        for key, value in metadata_filter.items():
            must_clauses.append({
                "key": f"payload.metadata.{key}",
                "match": {"value": value}
            })
        
        filters = {"must": must_clauses} if must_clauses else None
        
        return await self.retrieve(
            query=query,
            limit=limit,
            filters=filters
        )


class DenseRetriever:
    """
    Simple Dense Retriever chỉ sử dụng vector similarity.
    Sử dụng khi không cần hybrid search.
    """

    def __init__(
        self,
        vector_db: VectorDB,
        embedding_service: AsyncEmbeddingService
    ):
        """
        Khởi tạo DenseRetriever.

        Args:
            vector_db: VectorDB instance
            embedding_service: AsyncEmbeddingService instance
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents sử dụng vector similarity.

        Args:
            query: Query string
            limit: Số lượng kết quả
            score_threshold: Ngưỡng similarity score

        Returns:
            List of retrieved documents
        """
        query_vector = await self.embedding_service.embed(query)
        
        return self.vector_db.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
