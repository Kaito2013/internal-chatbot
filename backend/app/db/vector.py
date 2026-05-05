"""
Vector Database wrapper sử dụng Qdrant.
Cung cấp các methods để upsert, search, retrieve documents.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse
from typing import List, Dict, Any, Optional
import uuid

from ..config import settings


class VectorDB:
    """
    Wrapper class cho QdrantClient.
    Tự động tạo collection nếu chưa tồn tại.
    """

    def __init__(self, url: Optional[str] = None, collection_name: Optional[str] = None):
        """
        Khởi tạo VectorDB client.

        Args:
            url: Qdrant server URL (mặc định từ settings)
            collection_name: Tên collection (mặc định từ settings)
        """
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_dim = settings.EMBEDDING_DIM
        self.client = QdrantClient(url=self.url)
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        """Kiểm tra và tạo collection nếu chưa tồn tại."""
        try:
            self.client.get_collection(self.collection_name)
        except (UnexpectedResponse, Exception):
            self.create_collection()

    def create_collection(self, recreate: bool = False) -> None:
        """
        Tạo collection mới với cosine distance.

        Args:
            recreate: Nếu True, xóa collection cũ trước khi tạo mới
        """
        if recreate:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_dim,
                distance=Distance.COSINE
            )
        )

    def upsert(self, points: List[Dict[str, Any]]) -> bool:
        """
        Upsert documents vào collection.

        Args:
            points: List of dicts với keys: id, vector, payload

        Returns:
            True nếu thành công
        """
        if not points:
            return True

        # Convert dicts to PointStruct
        point_structs = [
            PointStruct(
                id=p.get("id", str(uuid.uuid4())),
                vector=p["vector"],
                payload=p.get("payload", {})
            )
            for p in points
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=point_structs
        )
        return True

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm vectors gần nhất.

        Args:
            query_vector: Query vector
            limit: Số lượng kết quả trả về
            score_threshold: Ngưỡng similarity score
            query_filter: Filter conditions

        Returns:
            List of search results với score và payload
        """
        search_params = {}
        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            **search_params
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload
            }
            for r in results
        ]

    def retrieve(
        self,
        ids: List[str],
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents by IDs.

        Args:
            ids: List of document IDs
            collection_name: Tên collection (mặc định dùng self.collection_name)

        Returns:
            List of documents với payload
        """
        results = self.client.retrieve(
            collection_name=collection_name or self.collection_name,
            ids=ids
        )

        return [
            {
                "id": r.id,
                "vector": r.vector,
                "payload": r.payload
            }
            for r in results
        ]

    def count(self) -> int:
        """
        Đếm số lượng documents trong collection.

        Returns:
            Số lượng documents
        """
        result = self.client.get_collection(self.collection_name)
        return result.points_count
