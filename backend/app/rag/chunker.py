"""
Document chunking với nhiều strategies.
Hỗ trợ: by_paragraph, by_sentence, recursive.
"""
import re
import uuid
from typing import List, Dict, Any
from typing import Literal

from ..config import settings


class SmartChunker:
    """
    Smart document chunker với 3 strategies:
    - by_paragraph: Split theo paragraph
    - by_sentence: Split theo sentence (hỗ trợ tiếng Việt)
    - recursive: Recursively split với chunk_size + overlap
    """

    def __init__(
        self,
        strategy: Literal["by_paragraph", "by_sentence", "recursive"] = "recursive",
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Khởi tạo SmartChunker.

        Args:
            strategy: Chiến lược chunking
            chunk_size: Kích thước chunk (chars)
            chunk_overlap: Số char overlap giữa các chunks
        """
        self.strategy = strategy
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk documents theo strategy đã chọn.

        Args:
            documents: List of dicts với keys: content, source, metadata

        Returns:
            List of chunks với keys: content, chunk_id, source, metadata
        """
        if self.strategy == "by_paragraph":
            return self._chunk_by_paragraph(documents)
        elif self.strategy == "by_sentence":
            return self._chunk_by_sentence(documents)
        else:
            return self._chunk_recursive(documents)

    def _chunk_by_paragraph(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split documents theo paragraph.
        Mỗi paragraph thành một chunk.
        """
        chunks = []

        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})

            # Split bằng double newline hoặc paragraph mark
            paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', content)

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                chunk_id = self._generate_chunk_id(para)
                chunks.append({
                    "content": para,
                    "chunk_id": chunk_id,
                    "source": source,
                    "metadata": metadata
                })

        return chunks

    def _chunk_by_sentence(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split documents theo sentence.
        Hỗ trợ tiếng Việt và tiếng Anh.
        """
        chunks = []

        # Regex cho sentence splitting - hỗ trợ tiếng Việt
        # Dấu chấm câu: . ! ? … (cho cả tiếng Việt)
        sentence_endings = r'(?<=[.!?…])\s+'
        # Thêm các dấu câu tiếng Việt: (hoặc , nhưng separator)
        # Với tiếng Việt: bỏ qua các trường hợp như "..."
        # Sử dụng lookahead để giữ lại dấu câu

        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})

            # Tạm thời thay thế ... bằng placeholder để không split nhầm
            content = re.sub(r'\.{3,}', '<<<ELLIPSIS>>>', content)

            # Split theo sentence
            sentences = re.split(sentence_endings, content)

            current_chunk = []
            current_len = 0

            for sentence in sentences:
                # Restore ellipsis
                sentence = sentence.replace('<<<ELLIPSIS>>>', '...')
                sentence = sentence.strip()

                if not sentence:
                    continue

                sentence_len = len(sentence)

                # Nếu sentence quá dài, vẫn thêm vào chunk
                if current_len + sentence_len > self.chunk_size and current_chunk:
                    # Emit current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunk_id = self._generate_chunk_id(chunk_text)
                    chunks.append({
                        "content": chunk_text,
                        "chunk_id": chunk_id,
                        "source": source,
                        "metadata": metadata
                    })
                    current_chunk = [sentence]
                    current_len = sentence_len
                else:
                    current_chunk.append(sentence)
                    current_len += sentence_len + 1  # +1 for space

            # Emit remaining chunk
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(chunk_text)
                chunks.append({
                    "content": chunk_text,
                    "chunk_id": chunk_id,
                    "source": source,
                    "metadata": metadata
                })

        return chunks

    def _chunk_recursive(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Recursively split documents với chunk_size và overlap.
        Ưu tiên split theo paragraph, sau đó sentence, cuối cùng là word.
        """
        chunks = []

        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})

            # Tách content thành các phần lớn bằng paragraph
            paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', content)

            current_chunk = []
            current_len = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                para_len = len(para)

                # Nếu paragraph nhỏ hơn chunk_size
                if para_len <= self.chunk_size:
                    # Thêm vào chunk hiện tại
                    if current_len + para_len > self.chunk_size and current_chunk:
                        # Emit current chunk với overlap
                        chunk_text = ' '.join(current_chunk)
                        chunk_id = self._generate_chunk_id(chunk_text)
                        chunks.append({
                            "content": chunk_text,
                            "chunk_id": chunk_id,
                            "source": source,
                            "metadata": metadata
                        })

                        # Bắt đầu chunk mới với overlap
                        overlap_text = ' '.join(current_chunk)
                        overlap_words = overlap_text.split()
                        if len(overlap_words) > self.chunk_overlap:
                            # Lấy overlap từ cuối chunk cũ
                            overlap = ' '.join(overlap_words[-self.chunk_overlap:])
                            current_chunk = [overlap]
                            current_len = len(overlap)
                        else:
                            current_chunk = []
                            current_len = 0

                    current_chunk.append(para)
                    current_len += para_len + 1

                else:
                    # Paragraph dài hơn chunk_size, cần split thêm
                    # Trước tiên emit current chunk nếu có
                    if current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        chunk_id = self._generate_chunk_id(chunk_text)
                        chunks.append({
                            "content": chunk_text,
                            "chunk_id": chunk_id,
                            "source": source,
                            "metadata": metadata
                        })
                        current_chunk = []
                        current_len = 0

                    # Split paragraph bằng recursive approach
                    sub_chunks = self._split_long_text(para)

                    for sub_chunk in sub_chunks:
                        if current_len + len(sub_chunk) > self.chunk_size and current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            chunk_id = self._generate_chunk_id(chunk_text)
                            chunks.append({
                                "content": chunk_text,
                                "chunk_id": chunk_id,
                                "source": source,
                                "metadata": metadata
                            })

                            # Overlap
                            overlap_text = ' '.join(current_chunk)
                            overlap_words = overlap_text.split()
                            if len(overlap_words) > self.chunk_overlap:
                                overlap = ' '.join(overlap_words[-self.chunk_overlap:])
                                current_chunk = [overlap]
                                current_len = len(overlap)
                            else:
                                current_chunk = []
                                current_len = 0

                        current_chunk.append(sub_chunk)
                        current_len += len(sub_chunk) + 1

            # Emit remaining chunk
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_chunk_id(chunk_text)
                chunks.append({
                    "content": chunk_text,
                    "chunk_id": chunk_id,
                    "source": source,
                    "metadata": metadata
                })

        return chunks

    def _split_long_text(self, text: str) -> List[str]:
        """
        Split text dài thành nhiều phần nhỏ hơn.
        Ưu tiên split theo sentence, sau đó word.
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        sentences = re.split(r'(?<=[.!?…])\s+', text)

        current = []
        current_len = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_len = len(sentence)

            if sentence_len <= self.chunk_size:
                if current_len + sentence_len > self.chunk_size and current:
                    chunks.append(' '.join(current))
                    current = [sentence]
                    current_len = sentence_len
                else:
                    current.append(sentence)
                    current_len += sentence_len + 1
            else:
                # Quá dài, split theo word
                if current:
                    chunks.append(' '.join(current))
                    current = []
                    current_len = 0

                words = sentence.split()
                for word in words:
                    word_len = len(word)
                    if current_len + word_len > self.chunk_size and current:
                        chunks.append(' '.join(current))
                        current = [word]
                        current_len = word_len
                    else:
                        current.append(word)
                        current_len += word_len + 1

        if current:
            chunks.append(' '.join(current))

        return chunks if chunks else [text]

    def _generate_chunk_id(self, content: str) -> str:
        """
        Generate deterministic chunk ID từ content.

        Args:
            content: Text content

        Returns:
            Chunk ID string
        """
        # Lấy prefix của content để tạo unique ID
        prefix = content[:50] if len(content) >= 50 else content
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, prefix))
