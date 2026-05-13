# IP Creator - AI Cartoon IP Video Generation System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue3](https://img.shields.io/badge/Vue-3.5+-brightgreen.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element_Plus-2.13+-blue.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📖 Overview

**IP Creator** is a configurable, multi-LLM localized AI cartoon IP video generation system. It's a complete AIGC (AI-Generated Content) platform that enables autonomous, privacy-preserving production of cartoon character short videos with consistent IP identity.

### ✨ Key Features

#### 🎯 LLM & AI Management
- **🔄 Multi-LLM Hot-Switching**: Seamlessly switch between local (Ollama) and cloud APIs (Zhipu, Qwen, DeepSeek) without restart
- **📊 Provider-Model-Channel Architecture**: Three-tier management with automatic model sync
- **💚 Health Monitoring with EMA Metrics**: Exponential Moving Average for response time & success rate tracking
- **🏷️ Status Grouping Display**: Ready/Pending/Inactive grouping with color-coded indicators
- **🎨 Smart Capability Routing**: Auto-select channels by capability (text/image/video)

#### 🎬 Content Generation
- **🏷️ IP Asset Management**: Complete lifecycle with multi-angle reference images
- **🖼️ Three-View Generation**: Auto-generate front/side/back views for IP characters
- **🧠 LoRA Training**: Integrated fine-tuning with real-time progress tracking
- **🎭 IP-Adapter Integration**: Instant character consistency using reference images
- **🖼️ AI Image Generation**: Stable Diffusion with LoRA + IP-Adapter constraints
- **🎬 Video Generation**: CogVideoX image-to-video with temporal consistency
- **📝 Story Generation**: LLM-powered narrative creation with async processing

#### 💻 System & Platform
- **📁 Content Library**: Advanced filtering, favorites, statistics, and bulk operations
- **💚 System Health Dashboard**: Real-time monitoring of Redis, DB, GPU, Celery, LLM configs
- **🌐 Internationalization**: Full Chinese/English support with dynamic switching
- **🔒 Privacy-First**: Full offline capability - all data stays local
- **⚡ Async Task Queue**: Celery multi-queue with progress tracking and error handling
- **📊 Unified API Response**: All 53 endpoints follow standardized format

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Vue3 + Element Plus)             │
│  Dashboard | LLM Mgmt | IP Assets | Generate | Tasks | Library│
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST + JWT Auth
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend Layer                      │
│    API Routers | Auth | CORS | Static Files | SPA Fallback   │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   Core Business Layer                        │
│  LLM Manager | IP Manager | Video Generator | Storage       │
│  Generation Dispatcher | Post Processor                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Async Task Processing (Celery)                  │
│  Story Generation | Image Generation | Video Generation      │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Data & Storage Layer                        │
│  SQLite DB | Redis Cache | File Storage | Models             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Redis** (for Celery task queue)
- **SQLite** (included, no installation needed)

**Or use Docker:**
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **NVIDIA GPU** (optional, for AI generation)

### Option 1: Docker Deployment (Recommended)

```bash
# Build and start all services
docker-compose up -d --build

# Initialize database
docker-compose exec web python init_database.py

# Access the application
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**📚 For detailed Docker documentation, see: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)**

### Option 2: Local Development

### 1️⃣ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ip-creator.git
cd ip-creator

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend-vue
npm install
cd ..
```

### 2️⃣ Database Initialization

```bash
# Initialize database with schema, seed data, and admin user
python init_database.py
```

This will:
- ✅ Create all 10 database tables (using `sql/schema_complete.sql`)
- ✅ Insert 11 LLM providers (OpenAI, Anthropic, Google, DeepSeek, etc.)
- ✅ Insert pre-configured LLM models
- ✅ Create default admin account (admin/admin123)

**📚 Database Scripts Location:**
- Schema: `sql/schema_complete.sql` (v2.0, latest)
- Seed Data: `sql/seed_data.sql`
- Migrations: `sql/migrations/`
- Documentation: `sql/README.md`

**⚠️ Note:** Always use `schema_complete.sql` for new installations. Migration scripts in `sql/migrations/` are only for upgrading existing databases.

### 3️⃣ Start Services

**Terminal 1 - Backend API:**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
# Linux / macOS (推荐: 自动从 celery_worker.py 读取队列列表并携带 -Q)
./start_celery.sh

# Windows / 手动启动 (必须显式带 -Q, 否则任务会堆积在 Redis 中无人消费)
celery -A celery_worker.celery_app worker --loglevel=info --pool=solo \
  -Q celery,story_generation,image_generation,video_generation,training
```

> ⚠️ **重要**: `celery_worker.py` 中 `task_routes` 将生成任务路由到 `story_generation/image_generation/video_generation` 等自定义队列；worker 默认只监听 `celery` 队列，必须通过 `-Q` 参数显式声明。

**Terminal 3 - Frontend:**
```bash
cd frontend-vue
npm run dev
```

### 4️⃣ Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login**: admin / admin123

⚠️ **IMPORTANT**: Change the admin password immediately after first login!

---

## 📁 Project Structure

```
ip-creator/
├── app/                        # Backend application (FastAPI)
│   ├── api/v1/                # API endpoints (9 routers, 53 endpoints)
│   │   ├── auth_router.py     # Authentication & JWT
│   │   ├── llm_router.py      # LLM channel management
│   │   ├── llm_provider_router.py # LLM provider management
│   │   ├── ip_router.py       # IP asset management
│   │   ├── generation_router.py # Content generation
│   │   ├── lora_router.py     # LoRA training
│   │   ├── task_router.py     # Task monitoring
│   │   ├── content_router.py  # Content library
│   │   ├── system_health.py   # Health checks
│   │   └── settings_router.py # System settings
│   ├── config/                # Configuration
│   │   ├── database.py        # Async SQLAlchemy setup
│   │   └── settings.py        # Pydantic settings
│   ├── core/                  # Business logic (10 modules)
│   │   ├── llm_manager.py     # Multi-LLM routing & health
│   │   ├── llm_provider_registry.py # Provider registry
│   │   ├── generation_dispatcher.py # Task dispatching
│   │   ├── video_generator.py # Video generation pipeline
│   │   ├── post_processor.py  # Post-processing
│   │   ├── lora_trainer.py    # LoRA training (mock/real)
│   │   ├── ip_manager.py      # IP asset management
│   │   ├── gpu_cache.py       # GPU memory management
│   │   └── exceptions.py      # Unified exception handling
│   ├── models/                # SQLAlchemy ORM (9 models)
│   ├── schemas/               # Pydantic validation (5 schemas)
│   ├── services/              # Service layer (9 services + adapters)
│   │   ├── adapters/          # Protocol adapters (text/image/video)
│   │   ├── cloud_gen_service.py # Cloud generation
│   │   ├── diffusion_service.py # Diffusion models
│   │   └── ...
│   ├── security/              # Auth, JWT, encryption
│   ├── utils/                 # Logger, response helpers
│   └── tasks/                 # Celery task definitions
├── frontend-vue/              # Vue3 frontend (Vite + Element Plus)
│   ├── src/
│   │   ├── api/              # Axios API clients (8 modules)
│   │   ├── views/            # Page components (9 views)
│   │   ├── components/       # Reusable components
│   │   ├── composables/      # Vue composables (pagination, delete)
│   │   ├── stores/           # Pinia state management (auth, app)
│   │   ├── i18n/             # Internationalization (zh-CN, en-US)
│   │   ├── router/           # Vue Router
│   │   └── utils/            # Logger, time formatting
│   └── dist/                 # Production build (auto-generated)
├── data/                      # Data storage (auto-created)
│   ├── ip_creator.db         # SQLite database
│   ├── ip_assets/            # IP reference images
│   ├── stories/              # Generated stories (JSON)
│   ├── videos/               # Generated videos
│   ├── lora_models/          # Trained LoRA models
│   ├── models/               # Diffusion model files
│   └── exports/              # Data backups (JSON)
├── sql/                       # Database schemas and migrations
│   ├── README.md             # Database documentation
│   ├── schema_complete.sql   # Complete schema (v2.0, latest)
│   ├── seed_data.sql         # Initial seed data (11 providers)
│   └── migrations/           # SQL migration scripts
│       ├── 004_create_generated_contents.sql
│       └── 005_add_performance_indexes.sql
├── Dockerfile                 # Docker multi-stage build
├── docker-compose.yml         # Docker Compose configuration
├── nginx.conf                 # Nginx reverse proxy config
├── .dockerignore              # Docker build exclusions
├── DOCKER_DEPLOYMENT.md       # Docker deployment guide
├── docs/                      # Documentation
│   ├── ERROR_HANDLING_GUIDE.md # Error handling reference
│   └── 可配置多LLM本地化AI卡通IP视频生成系统——详细项目设计文档.md
├── celery_worker.py           # Celery worker for async tasks
├── init_database.py           # DB initialization (schema + seed + admin)
├── init_admin.py             # Admin user creation
├── export_database.py        # Data export utility
├── start.bat                 # Windows startup script
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
└── README.md                  # This file
```

---

## 🗄️ Database Schema

### Database Files

All database scripts are organized in the `sql/` directory:

```
sql/
├── README.md                     # Detailed database documentation
├── schema_complete.sql           # Complete schema (v2.0, use this!)
├── seed_data.sql                 # Seed data (11 LLM providers)
└── migrations/                   # SQL migration scripts
    ├── 004_create_generated_contents.sql
    └── 005_add_performance_indexes.sql
```

**📖 For detailed documentation, see: [sql/README.md](sql/README.md)**

### Tables Overview

| Table | Description | Key Fields |
|-------|-------------|------------|
| **users** | User authentication | username, email, role, permissions |
| **llm_providers** | LLM provider configs | code, name, endpoint, requires_api_key |
| **llm_models** | Model versions | provider_id, code, capabilities |
| **llm_configs** | Active channels | provider, model_name, is_active |
| **ip_assets** | IP characters | name, trigger_word, style_template |
| **ip_reference_images** | IP reference images | ip_asset_id, image_type, file_path |
| **lora_models** | Trained LoRA models | name, file_path, training_status |
| **task_records** | Async task tracking | task_id, task_type, status, progress |
| **generated_contents** | Content library | content_type, file_path, tags, is_favorite |
| **system_settings** | System configuration | key, value, category |

### Relationships

```
llm_providers ────< llm_models (1:N, CASCADE DELETE)
lora_models ────< ip_assets (1:N, SET NULL)
ip_assets ────< task_records (1:N, SET NULL)
ip_assets ────< generated_contents (1:N, SET NULL)
```

### Initialize Database

```bash
# Full initialization (schema + seed data + admin)
python init_database.py

# Or manually:
sqlite3 data/ip_creator.db < sql/schema_complete.sql
sqlite3 data/ip_creator.db < sql/seed_data.sql
python init_admin.py
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/ip_creator.db

# Redis (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# App Settings
MAX_CONCURRENT_TASKS=2
DEBUG=True
```

### LLM Provider Setup

1. **OpenAI**: Get API key from https://platform.openai.com
2. **Zhipu AI**: Get API key from https://open.bigmodel.cn
3. **Qwen**: Get API key from https://dashscope.console.aliyun.com
4. **DeepSeek**: Get API key from https://platform.deepseek.com
5. **Ollama**: Install from https://ollama.com (no API key needed)

Configure API keys in the LLM Management page after login.

---

## 📚 API Documentation

Once the backend is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Detailed Reference**: See [API_REFERENCE.md](API_REFERENCE.md)
- **Project Analysis**: See [PROJECT_ANALYSIS_REPORT.md](PROJECT_ANALYSIS_REPORT.md)

### API Modules (53 Endpoints Total)

| Module | Endpoints | Description |
|--------|-----------|-------------|
| **Auth** | 1 | User login and JWT token |
| **LLM Management** | 9 | Channel CRUD, health check, hot switch |
| **Provider Management** | 9 | Provider/model CRUD, sync models |
| **IP Assets** | 6 | IP CRUD, three-view generation |
| **LoRA Models** | 6 | Training CRUD, progress tracking |
| **Generation** | 9 | Story/image/video sync & async |
| **Task Management** | 4 | Task list, details, cancel, delete |
| **Content Library** | 5 | Content CRUD, favorites, stats |
| **Settings** | 5 | System settings CRUD |
| **System Health** | 2 | Health check and summary |
| **Dashboard** | 1 | Dashboard statistics |

### Key Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/login` | User login | ❌ |
| GET | `/api/v1/llm/list` | List LLM channels | ✅ |
| POST | `/api/v1/llm/register` | Register new channel | ✅ Admin |
| GET | `/api/v1/llm/health/all` | Check all channel health | ✅ |
| PUT | `/api/v1/llm/switch` | Switch active model | ✅ Admin |
| GET | `/api/v1/providers` | List providers | ✅ Admin |
| POST | `/api/v1/providers/{code}/sync-models` | Sync models | ✅ Admin |
| GET | `/api/v1/ip/list` | List IP assets | ✅ |
| POST | `/api/v1/ip/{id}/generate-three-views` | Generate 3 views | ✅ |
| GET | `/api/v1/lora/list` | List LoRA models | ✅ |
| POST | `/api/v1/generate/story/async` | Async story generation | ✅ |
| POST | `/api/v1/generate/image/async` | Async image generation | ✅ |
| POST | `/api/v1/generate/video/async` | Async video generation | ✅ |
| GET | `/api/v1/tasks/list` | List all tasks | ✅ |
| GET | `/api/v1/tasks/{task_id}` | Get task details | ✅ |
| GET | `/api/v1/contents` | List generated content | ✅ |
| GET | `/api/v1/settings` | Get system settings | ✅ |
| GET | `/api/v1/health` | System health check | ❌ |
| GET | `/api/v1/dashboard/stats` | Dashboard statistics | ✅ |

---

## 🎯 Core Features

### 1. LLM Management

- Add and configure multiple LLM providers
- Sync available models automatically
- Create channels with custom configurations
- Monitor health and performance metrics
- Switch models without restart
- **Channel-centric abstraction**: Manage providers/models through channels
- **Smart type badges**: Local/Cloud indicators on channel names
- **Immutable core fields**: Provider, model, and channel name locked in edit mode

### 1.5. Settings - Provider & Model Management

- **Provider Management**:
  - View all LLM providers with model counts
  - Enable/disable providers with status toggles
  - Sync models from provider APIs
  - Hover to see model names
  
- **Model Management**:
  - Filter by provider and capability
  - View detailed model specifications
  - Enable/disable models independently
  - See pricing information (input/output per million tokens)
  - Backend API integration for all state changes

### 2. IP Asset Management

- Create IP characters with reference images
- Configure trigger words for consistency
- Set style templates (3D cartoon, blind box, healing, anime)
- Associate with LoRA models
- Multi-angle image upload

### 3. Content Generation

**Story Generation:**
- Async generation via LLM
- Automatic file saving (JSON format)
- Title and description extraction
- Word count tracking

**Image Generation:**
- Stable Diffusion with Diffusers
- LoRA model integration
- IP-Adapter for character consistency
- Reference image support

**Video Generation:**
- CogVideoX image-to-video
- Temporal consistency
- Fallback animation mode

### 4. Content Library

- Browse all generated content
- Filter by type, status, IP asset, tags
- Advanced search and date range
- Bulk operations (favorite, delete)
- Content preview (video player, image viewer, story text)
- Download generated files
- Automatic thumbnail generation

### 5. Task Monitoring

- Real-time progress tracking
- Task status (pending, running, completed, failed)
- Execution time and resource usage
- Error messages and retry logic
- Filter by IP asset and task type
- Pagination support for large task lists

### 6. System Health Dashboard

- **Comprehensive Checks**:
  - Redis connectivity
  - Database accessibility
  - LLM configurations (with status grouping: Ready/Pending/Inactive)
  - Directory structure
  - Disk space
  - GPU availability and memory
  - Celery worker status
  - Diffusion model files
  - LoRA training mode
  
- **Interactive UI**:
  - Color-coded status indicators
  - Hover popovers with detailed model lists
  - EMA metrics (response time, success rate)
  - Cloud/Local model type labels
  - Real-time refresh capability
  - Warning/error counts in header

### 7. Settings Management

- **System Configuration**:
  - Category-based settings organization
  - Real-time updates with validation
  - Reset to defaults per category
  - Category listing and navigation
  
- **Available Categories**:
  - Generation settings (timeouts, limits)
  - Storage paths configuration
  - LLM default parameters
  - System behavior settings

---

## 🌐 Internationalization

The frontend supports Chinese and English:

- **Default Language**: Chinese (zh-CN)
- **Switch Language**: User profile menu
- **Coverage**: All UI elements, messages, and labels
- **Dynamic**: No page reload required

Translation files:
- `frontend-vue/src/i18n/zh-CN.json` - Chinese
- `frontend-vue/src/i18n/en-US.json` - English

---

## 🔐 Security

- **JWT Authentication**: Token-based auth with expiration
- **Password Hashing**: Bcrypt with salt
- **Role-Based Access Control**: Admin and user roles
- **API Key Encryption**: Secure storage of LLM API keys
- **File Upload Validation**: Type and size restrictions
- **SQL Injection Prevention**: Parameterized queries (SQLAlchemy ORM)
- **CORS Configuration**: Configurable allowed origins

---

## 🛠️ Development

### Backend Development

```bash
# Run with auto-reload
python -m uvicorn app.main:app --reload --port 8000

# Or use the startup script
python start.py

# Run on specific host/port
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend-vue

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

### Database Migrations

```bash
# Run migration script
python migrations/002_create_task_records_table.py

# Or apply SQL directly
sqlite3 data/ip_creator.db < migrations/004_create_generated_contents.sql
```

---

## 📦 Deployment

### Production Checklist

- [ ] Change default admin password
- [ ] Set strong JWT_SECRET_KEY
- [ ] Configure CORS allowed origins
- [ ] Set DEBUG=False
- [ ] Use production Redis instance
- [ ] Set up reverse proxy (Nginx)
- [ ] Enable HTTPS
- [ ] Configure backup for database
- [ ] Set up monitoring and logging
- [ ] Configure Celery as system service

### Docker Deployment (Coming Soon)

```bash
# Build and run with Docker Compose
docker-compose up -d
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI**: Modern Python web framework
- **Vue 3**: Progressive JavaScript framework
- **Element Plus**: Vue 3 component library
- **Celery**: Distributed task queue
- **Stable Diffusion**: Open-source image generation
- **CogVideoX**: Video generation model
- **Ollama**: Local LLM runtime

---

## 📞 Support

- **Documentation**: This README
- **Issues**: GitHub Issues
- **Email**: support@ipcreator.local

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)
- [x] Multi-LLM management with hot-switching
- [x] Provider-model-channel architecture
- [x] Health monitoring with EMA metrics
- [x] IP asset management with three-view generation
- [x] LoRA training with progress tracking
- [x] Content generation (story/image/video)
- [x] Content library with advanced filtering
- [x] System health dashboard
- [x] Internationalization (CN/EN)
- [x] Unified API response format (53 endpoints)

### 🚧 In Progress
- [ ] Dataset preparation assistant for LoRA training
- [ ] LoRA test bench for model validation
- [ ] One-click IP creation wizard

### 📋 Planned
- [ ] Automated testing framework (pytest)
- [ ] Alembic database migration
- [ ] API rate limiting
- [ ] Prometheus monitoring integration
- [ ] Docker deployment optimization
- [ ] Expression set generation (6 standard expressions)
- [ ] Scene template library (50+ presets)
- [ ] Batch generation tool
- [ ] Frontend error boundaries
- [ ] Advanced analytics dashboard

---

**Made with ❤️ by the IP Creator Team**
