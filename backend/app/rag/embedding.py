"""
Embedding service sử dụng OpenAI API.
Fallback sang mock embeddings nếu không có API key.
"""
import os
from typing import List, Optional
import numpy as np

from ..config import settings


class AsyncEmbeddingService:
    """
    Async embedding service sử dụng OpenAI API.
    Fallback sang mock embeddings khi không có API key.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Khởi tạo embedding service.

        Args:
            api_key: OpenAI API key (mặc định từ settings)
            model: Tên model embedding (mặc định từ settings)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIM
        self._client = None
        self._use_mock = not bool(self.api_key)

        if not self._use_mock:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)

    async def embed(self, text: str) -> List[float]:
        """
        Tạo embedding cho một đoạn text.

        Args:
            text: Text cần embed

        Returns:
            List of floats là embedding vector
        """
        if self._use_mock:
            return self._mock_embedding(text)

        response = await self._client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo embeddings cho nhiều texts.

        Args:
            texts: List of texts cần embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self._use_mock:
            return [self._mock_embedding(text) for text in texts]

        # OpenAI batch embedding
        response = await self._client.embeddings.create(
            model=self.model,
            input=texts
        )

        # Sắp xếp theo thứ tự input
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding

        return embeddings

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Tạo mock embedding vector cho testing.
        Sử dụng deterministic hash để tạo consistent vectors.

        Args:
            text: Text cần embed

        Returns:
            Mock embedding vector
        """
        # Tạo seed từ text hash
        hash_val = hash(text) % (2**32)
        np.random.seed(hash_val)

        # Tạo vector với unit length (L2 normalized)
        vec = np.random.randn(self.dimension).astype(np.float32)
        vec = vec / np.linalg.norm(vec)

        return vec.tolist()

    @property
    def is_mock(self) -> bool:
        """Kiểm tra có đang dùng mock embeddings không."""
        return self._use_mock
