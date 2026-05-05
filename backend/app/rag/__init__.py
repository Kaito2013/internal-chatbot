"""
RAG Package - Retrieval Augmented Generation components.

Exports:
- RAGPipeline: Main pipeline orchestration
- DocumentIngester: Document ingestion
- HybridRetriever: Hybrid retrieval (dense + sparse)
- ResultReranker: Reranking results
- SmartChunker: Document chunking
- AsyncEmbeddingService: Text embedding
- VectorDB: Vector database wrapper
"""

from .pipeline import RAGPipeline, AsyncRAGPipeline
from .ingester import DocumentIngester, BatchIngester
from .retriever import HybridRetriever, DenseRetriever
from .ranker import ResultReranker, MMRReranker
from .chunker import SmartChunker
from .embedding import AsyncEmbeddingService
from ..db.vector import VectorDB

__all__ = [
    # Pipeline
    "RAGPipeline",
    "AsyncRAGPipeline",
    # Ingestion
    "DocumentIngester",
    "BatchIngester",
    # Retrieval
    "HybridRetriever",
    "DenseRetriever",
    # Reranking
    "ResultReranker",
    "MMRReranker",
    # Chunking
    "SmartChunker",
    # Embedding
    "AsyncEmbeddingService",
    # Database
    "VectorDB",
]
