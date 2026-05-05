# Internal Chatbot

Hệ thống Chatbot nội bộ với RAG (Retrieval-Augmented Generation) và CRM Integration.

## Tính năng

- **RAG Engine**: Hybrid Search (Semantic + Keyword) với Strict Grounding
- **Vector Database**: Qdrant (hoặc ChromaDB)
- **LLM**: Hỗ trợ OpenAI, Minimax, Anthropic, Gemini, DeepSeek
- **CRM Integration**: Function Calling để lấy thông tin người dùng thực
- **JS Widget**: Nhúng vào website chỉ với 1 `<script>` tag
- **Admin Panel**: Dashboard quản lý tài liệu, phiên hội thoại, thống kê token
- **Token Tracking**: Theo dõi input/output tokens cho mỗi request

## Architecture

```
User → JS Widget → FastAPI Backend → Agentic Layer
                                    ├── RAG Pipeline → Qdrant (embeddings)
                                    └── CRM Tools → External CRM API

Admin Browser → Admin Panel (Next.js) → FastAPI Admin API → PostgreSQL
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
│   │   ├── admin/               # Admin Panel Backend (NEW)
│   │   │   ├── models.py        # Session, ChatLog, UsageStats, Document
│   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   ├── service.py       # CRUD operations
│   │   │   ├── routes.py        # REST API endpoints
│   │   │   └── middleware.py    # Logging middleware
│   │   ├── crm/                # CRM clients
│   │   │   ├── base.py
│   │   │   └── factory.py
│   │   ├── db/
│   │   │   ├── vector.py        # Vector DB (Qdrant)
│   │   │   └── database.py      # PostgreSQL (NEW)
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
├── frontend/
│   └── apps/
│       └── admin/              # Admin Panel Frontend (NEW - Next.js)
│           ├── src/
│           │   ├── app/         # Pages (login, overview, documents, sessions, stats)
│           │   ├── components/ # UI components
│           │   ├── lib/        # API client, auth utilities
│           │   └── store/      # Zustand stores
│           └── package.json
├── widget/
│   ├── widget.js               # Embeddable widget
│   ├── widget.css
│   ├── example.html
│   └── README.md
├── nginx/
│   └── nginx.conf
├── docker-compose.yml          # + PostgreSQL + Adminer
└── README.md
```

## Quick Start

### 1. Cài đặt

```bash
# Clone / Navigate
cd /root/internal-chatbot

# Copy env
cp backend/.env.example backend/.env
# Edit backend/.env và điền API keys

# Build & Run với Docker (Backend + PostgreSQL + Qdrant + Redis + Adminer)
docker-compose up -d

# Hoặc chạy local (cần Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Chạy Admin Panel

```bash
cd frontend/apps/admin
npm install
npm run dev
```

Truy cập:
- **Admin Panel**: http://localhost:3001
- **Adminer (DB)**: http://localhost:8080 (System: PostgreSQL)

### 3. Đăng nhập Admin

```
Username: admin
Password: changeme (đổi trong .env)
```

### 4. Ingest Documents

```bash
# Qua Admin Panel
# Upload trực tiếp .txt, .md, .pdf, .docx, .html

# Hoặc qua CLI
cd backend
python -m scripts.ingest --source ../../data/documents --recreate

# Kiểm tra stats
curl http://localhost:8000/api/stats
```

### 5. Nhúng Widget vào Website

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

## Admin Panel Features

### Trang Tổng quan
- Thống kê: Sessions, Messages, Users, Documents
- Token usage chart (7 ngày)
- Performance metrics: Latency, Input/Output tokens

### Quản lý Tài liệu
- Upload drag-drop (txt, md, pdf, docx, html)
- Search, Delete, Re-ingest documents
- Xem chunk count, file size, upload date

### Phiên Hội thoại
- List tất cả sessions
- Search nội dung chat
- View chi tiết từng message
- Export JSON/CSV

### Thống kê (Chart.js)
- Token Usage (Line chart)
- RAG Effectiveness (Bar chart)
- Top Sources (Doughnut chart)
- Period selector: 7d / 30d / 90d

## API Endpoints

### Chat API

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/health` | Health check |
| POST | `/api/chat` | Chat với bot |
| POST | `/api/ingest` | Ingest documents |
| POST | `/api/ingest/text` | Ingest single text |
| DELETE | `/api/ingest/source/{name}` | Delete by source |
| GET | `/api/stats` | Vector DB stats |

### Admin API

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/admin/auth/login` | Login, lấy JWT token |
| POST | `/api/admin/auth/verify` | Verify token |
| GET | `/api/admin/documents` | List documents |
| POST | `/api/admin/documents/upload` | Upload document |
| DELETE | `/api/admin/documents/{source}` | Delete document |
| POST | `/api/admin/documents/{source}/reingest` | Re-ingest |
| GET | `/api/admin/sessions` | List sessions |
| GET | `/api/admin/sessions/search` | Search sessions |
| GET | `/api/admin/sessions/{id}` | Session detail |
| DELETE | `/api/admin/sessions/{id}` | Delete session |
| GET | `/api/admin/sessions/export/{id}` | Export JSON/CSV |
| GET | `/api/admin/stats/overview` | Dashboard overview |
| GET | `/api/admin/stats/tokens` | Token usage |
| GET | `/api/admin/stats/rag-effectiveness` | RAG metrics |
| GET | `/api/admin/stats/top-sources` | Top sources |

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
# LLM Provider
# ========================
LLM_PROVIDER=minimax           # openai | minimax | anthropic | deepseek | mock
LLM_MODEL=abab6.5s-chat
LLM_TEMPERATURE=0.1
MAX_TOKENS=1000

# Minimax (OpenAI-compatible)
MINIMAX_API_KEY=***
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_GROUP_ID=***

# ========================
# Embedding
# ========================
OPENAI_API_KEY=***
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# ========================
# Vector Database (Qdrant)
# ========================
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=documents

# ========================
# PostgreSQL (Admin Panel)
# ========================
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot_admin

# ========================
# Admin Panel Auth
# ========================
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
ADMIN_SECRET_KEY=your-256-bit-secret-key
ADMIN_TOKEN_EXPIRE_HOURS=24

# ========================
# File Upload
# ========================
UPLOAD_DIR=/tmp/chatbot_uploads
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=txt,md,pdf,docx,html

# ========================
# CRM
# ========================
CRM_PROVIDER=generic
CRM_API_URL=https://your-crm.com/api
CRM_API_KEY=***
CRM_USE_MOCK=true
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

# Run Admin Panel locally
cd frontend/apps/admin
npm install
npm run dev

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

## Database

### PostgreSQL (Admin Panel)
- Chứa: Sessions, ChatLogs, UsageStats, DocumentMetadata
- Truy cập qua Adminer: http://localhost:8080

### Qdrant (Vector DB)
- Chứa: Document embeddings cho RAG
- Truy cập: http://localhost:6333/dashboard

### Redis (Session Store)
- Chứa: Chat session data
- Port: 6379

## License

MIT
