"""
Result Ranker - Cải thiện thứ hạng kết quả retrieval bằng reranking.
Sử dụng cross-encoder model để tính relevance scores chính xác hơn.
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class ResultReranker:
    """
    Reranker sử dụng cross-encoder để cải thiện relevance scoring.
    
    Cross-encoder đánh giá query-document pair trực tiếp,
    cho kết quả chính xác hơn vector similarity đơn thuần.
    
    Fallback: Nếu không có cross-encoder model, sử dụng
    semantic similarity scoring đơn giản.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_mock: bool = False
    ):
        """
        Khởi tạo ResultReranker.

        Args:
            model_name: Tên cross-encoder model (SentenceTransformers)
            use_mock: Force mock mode (cho testing/dev)
        """
        self.model_name = model_name
        self._model = None
        self._use_mock = use_mock
        
        # Kiểm tra xem có API key không - nếu không dùng mock
        self._use_mock = self._use_mock or not bool(settings.OPENAI_API_KEY)
        
        if not self._use_mock:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(model_name)
                logger.info(f"ResultReranker loaded cross-encoder: {model_name}")
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, using mock reranker"
                )
                self._use_mock = True
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder: {e}, using mock")
                self._use_mock = True

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank kết quả theo relevance với query.
        
        Args:
            query: Query string
            results: List of search results từ vector search
            limit: Số lượng kết quả cuối cùng

        Returns:
            List of reranked results với rerank_score
        """
        if not results:
            return []
        
        if len(results) == 1:
            # Chỉ có 1 kết quả, không cần rerank
            results[0]["rerank_score"] = results[0].get("score", 1.0)
            return results[:limit]
        
        if self._use_mock:
            return await self._mock_rerank(query, results, limit)
        
        return await self._cross_encoder_rerank(query, results, limit)

    async def _cross_encoder_rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank sử dụng cross-encoder model.
        
        Args:
            query: Query string
            results: List of search results
            limit: Số lượng kết quả

        Returns:
            Reranked results
        """
        # Chuẩn bị query-document pairs
        pairs = []
        for r in results:
            payload = r.get("payload", {})
            content = payload.get("content", "")
            pairs.append([query, content])
        
        # Tính scores bằng cross-encoder (sync nhưng nhanh)
        try:
            scores = self._model.predict(pairs)
            
            # Gắn rerank_score vào results
            for r, score in zip(results, scores):
                r["rerank_score"] = float(score)
                # Giữ lại original score
                r["original_score"] = r.get("score", 0)
            
        except Exception as e:
            logger.error(f"Cross-encoder prediction failed: {e}")
            return await self._mock_rerank(query, results, limit)
        
        # Sắp xếp theo rerank_score giảm dần
        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        
        return reranked[:limit]

    async def _mock_rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Mock rerank sử dụng keyword overlap và length scoring.
        
        Args:
            query: Query string
            results: List of search results
            limit: Số lượng kết quả

        Returns:
            Reranked results
        """
        query_words = set(query.lower().split())
        
        for r in results:
            payload = r.get("payload", {})
            content = payload.get("content", "").lower()
            content_words = set(content.split())
            
            # Keyword overlap score
            overlap = len(query_words & content_words)
            keyword_score = overlap / max(len(query_words), 1)
            
            # Length penalty - quá ngắn hoặc quá dài đều không tốt
            content_len = len(content)
            if content_len < 50:
                length_score = content_len / 50
            elif content_len > 1000:
                length_score = 1000 / content_len
            else:
                length_score = 1.0
            
            # Combined score với original similarity
            original_score = r.get("score", 0.5)
            rerank_score = (
                0.4 * original_score +
                0.4 * keyword_score +
                0.2 * length_score
            )
            
            r["rerank_score"] = rerank_score
            r["original_score"] = original_score
        
        # Sắp xếp theo rerank_score
        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        
        return reranked[:limit]

    @property
    def is_mock(self) -> bool:
        """Kiểm tra có đang dùng mock reranker không."""
        return self._use_mock


class MMRReranker:
    """
    Maximal Marginal Relevance (MMR) reranker.
    
    MMR giúp chọn kết quả vừa relevant với query, vừa diverse giữa các kết quả.
    Tránh trùng lặp nội dung trong top-k results.
    """

    def __init__(self, reranker: Optional[ResultReranker] = None):
        """
        Khởi tạo MMRReranker.

        Args:
            reranker: ResultReranker instance (mặc định tạo mới)
        """
        self.reranker = reranker or ResultReranker()

    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        limit: int = 5,
        diversity_lambda: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Rerank với MMR để đảm bảo diversity.
        
        Args:
            query: Query string
            results: List of search results
            limit: Số lượng kết quả cuối cùng
            diversity_lambda: Hệ số diversity (0 = chỉ relevance, 1 = chỉ diversity)

        Returns:
            List of diverse, relevant results
        """
        if not results:
            return []
        
        if len(results) <= limit:
            # Không cần MMR nếu kết quả ít hơn limit
            return results
        
        # Bước 1: Rerank lần đầu để có relevance scores
        reranked = await self.reranker.rerank(query, results, limit=len(results))
        
        # Bước 2: MMR selection
        selected = []
        remaining = reranked.copy()
        
        while len(selected) < limit and remaining:
            if not selected:
                # Chọn kết quả relevant nhất
                selected.append(remaining.pop(0))
            else:
                # Tính MMR score cho từng candidate
                best_mmr = float('-inf')
                best_idx = 0
                
                for i, candidate in enumerate(remaining):
                    relevance = candidate.get("rerank_score", 0)
                    
                    # Tính max similarity với các results đã chọn
                    max_sim = 0
                    for selected_doc in selected:
                        sim = self._cosine_similarity(
                            candidate.get("payload", {}).get("content", ""),
                            selected_doc.get("payload", {}).get("content", "")
                        )
                        max_sim = max(max_sim, sim)
                    
                    # MMR formula
                    mmr_score = (
                        (1 - diversity_lambda) * relevance -
                        diversity_lambda * max_sim
                    )
                    
                    if mmr_score > best_mmr:
                        best_mmr = mmr_score
                        best_idx = i
                
                selected.append(remaining.pop(best_idx))
        
        return selected

    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """
        Tính cosine similarity đơn giản giữa 2 texts (word overlap).
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
