# Internal Chatbot

Hệ thống Chatbot nội bộ với RAG (Retrieval-Augmented Generation) và CRM Integration.

## Tính năng

- **RAG Engine**: Hybrid Search (Semantic + Keyword) với Strict Grounding
- **Vector Database**: Qdrant (hoặc ChromaDB)
- **LLM**: Hỗ trợ OpenAI, Anthropic, Gemini, DeepSeek qua LiteLLM
- **CRM Integration**: Function Calling để lấy thông tin người dùng thực
- **JS Widget**: Nhúng vào website chỉ với 1 `<script>` tag
- **Dark Theme**: Giao diện hiện đại, monochrome palette

## Architecture

```
User → JS Widget → FastAPI Backend → Agentic Layer
                                    ├── RAG Pipeline → Qdrant (embeddings)
                                    └── CRM Tools → External CRM API
```

## Cấu trúc thư mục

```
internal-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (Pydantic)
│   │   ├── agentic/            # Agent + Tools
│   │   │   ├── agent.py
│   │   │   ├── memory.py
│   │   │   ├── tools.py
│   │   │   └── crm_tool.py
│   │   ├── crm/                # CRM clients
│   │   │   ├── base.py
│   │   │   └── factory.py
│   │   ├── db/                 # Vector DB
│   │   │   └── vector.py
│   │   └── rag/                # RAG pipeline
│   │       ├── chunker.py
│   │       ├── embedding.py
│   │       ├── ingester.py
│   │       ├── pipeline.py
│   │       ├── ranker.py
│   │       └── retriever.py
│   ├── scripts/
│   │   └── ingest.py           # CLI ingestion
│   └── requirements.txt
├── widget/
│   ├── widget.js               # Embeddable widget
│   ├── widget.css
│   ├── example.html
│   └── README.md
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── README.md (this file)
```

## Quick Start

### 1. Cài đặt

```bash
# Clone / Navigate
cd /root/internal-chatbot

# Copy env
cp backend/.env.example backend/.env
# Edit backend/.env và điền API keys

# Build & Run với Docker
docker-compose up -d

# Hoặc chạy local (cần Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Ingest Documents

```bash
# Ingest thư mục documents
python -m scripts.ingest --source ../../data/documents --recreate

# Ingest file đơn lẻ
python -m scripts.ingest --source ./data/docs/myfile.docx

# Kiểm tra stats
curl http://localhost:8000/api/stats
```

### 3. Nhúng Widget vào Website

```html
<!-- Thêm vào <head> hoặc <body> -->
<script>
  window.chatbotConfig = {
    apiUrl: 'https://api.your-domain.com',
    chatbotId: 'your-chatbot-id',
    authToken: 'optional-jwt-token',  // Optional
    position: 'right',                 // 'left' | 'right'
  };
</script>
<script src="https://your-domain.com/widget/widget.js"></script>
```

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/health` | Health check |
| POST | `/api/chat` | Chat với bot |
| POST | `/api/ingest` | Ingest documents |
| POST | `/api/ingest/text` | Ingest single text |
| DELETE | `/api/ingest/source/{name}` | Delete by source |
| GET | `/api/stats` | Vector DB stats |

### Chat Request

```json
{
  "session_id": "sess_abc123",
  "question": "Gói dịch vụ của tôi là gì?",
  "user_id": "user_123",
  "email": "user@company.com"
}
```

### Chat Response

```json
{
  "answer": "Dựa trên hồ sơ của bạn, gói dịch vụ hiện tại là Enterprise.",
  "sources": [
    {"content": "...", "source": "contracts.docx", "score": 0.92}
  ],
  "used_crm": true,
  "session_id": "sess_abc123",
  "mode": "HYBRID"
}
```

## Environment Variables

```bash
# ========================
# Vector Database
# ========================
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=documents

# ========================
# LLM (OpenAI)
# ========================
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
MAX_TOKENS=1000

# ========================
# CRM (Mock mode = True for dev)
# ========================
CRM_PROVIDER=generic
CRM_API_URL=https://your-crm.com/api
CRM_API_KEY=your_key
CRM_USE_MOCK=true

# ========================
# Backend
# ========================
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=*
```

## Widget API (JavaScript)

```javascript
// Open/Close/Toggle
window.Chatbot.open();
window.Chatbot.close();
window.Chatbot.toggle();

// Clear history
window.Chatbot.clearHistory();

// Send message programmatically
window.Chatbot.sendMessage('Hello!');

// Events
window.Chatbot.on('message', (data) => {
  console.log('Message sent:', data);
});

window.Chatbot.on('sessionCreate', (session) => {
  console.log('Session created:', session.id);
});
```

## Development

```bash
# Run backend locally
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Test API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","question":"Hello"}'

# Run with Docker
docker-compose up -d
docker-compose logs -f backend

# Stop
docker-compose down
```

## License

MIT
