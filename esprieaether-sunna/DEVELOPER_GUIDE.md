# ESPRIEAETHER-SUNNA Developer Guide

> **Version**: 2.0  
> **Last Updated**: 2026-11-20  
> **Status**: Active Development

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [Development Workflow](#development-workflow)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Contributing](#contributing)

---

## 🏗 Architecture Overview

```
ESPRIEAETHER-SUNNA/
├── src/                          # Main Python application
│   ├── sunna_api.py             # Flask REST API (port 5100)
│   ├── sunna_executor.py        # Executive Director + Dashboard (port 5105)
│   └── __init__.py
├── brain/                        # AI Brain components
│   ├── router.py                # Smart Router with ML classification
│   ├── self_evolution.py        # Self-evolution engine
│   └── autotune.py              # Python port of AutoTune
├── tools/colibri/               # Colibri inference tools
│   ├── autotune.py              # Execution tuning
│   ├── doctor.py                # Diagnostics
│   ├── family_registry.py       # Model family registry
│   ├── openai_server.py         # OpenAI-compatible server
│   └── ...                      # Other engines
├── G0DM0D3/                     # G0DM0D3 safety research framework
│   ├── src/lib/                 # Core engines (TypeScript)
│   ├── api/                     # Node.js/Express API
│   ├── src/stm/                 # Semantic Transformation Modules
│   └── research/                # Evaluation scripts
├── obsidian/                    # Documentation (Obsidian vault)
│   └── Sunna-Equipe-Industrial/
├── data/                        # Data files
│   ├── airdrops.json
│   ├── learning_database.json
│   └── cost_estimates.json
└── evolution_reports/           # Self-evolution reports (auto-generated)
```

### Key Design Principles

1. **Modularity**: Each component is independently deployable and testable
2. **Observability**: Built-in metrics, logging, and health checks
3. **Resilience**: Fallback chains, retry logic, graceful degradation
4. **Security**: JWT auth, rate limiting, input validation
5. **Extensibility**: Plugin architecture for new engines and capabilities

---

## 🚀 Getting Started

### Prerequisites

```bash
# System
- Python 3.10+
- Node.js 20+ (for G0DM0D3)
- Redis (optional, for caching)
- Git

# Python packages
pip install flask flask-sock python-dotenv pyjwt radon scikit-learn numpy requests

# Node packages (for G0DM0D3)
cd G0DM0D3 && npm install
```

### Environment Setup

```bash
# Clone and setup
git clone <repo>
cd esprieaether-sunna

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Create data directories
mkdir -p ~/ESPRIEAETHER/data
mkdir -p ~/Desktop/Sunna-Equipe-Industrial
```

### Quick Start

```bash
# Terminal 1: Start API Bridge
python src/sunna_api.py

# Terminal 2: Start Executor + Dashboard
python src/sunna_executor.py

# Terminal 3: Run evolution cycle (optional)
python brain/self_evolution.py --cycle

# Access points:
# - API: http://localhost:5100
# - Dashboard: http://localhost:5105
# - Metrics: http://localhost:5100/metrics
# - WebSocket: ws://localhost:5105/ws
```

---

## 📁 Project Structure

### src/ - Main Application

| File | Purpose | Port |
|------|---------|------|
| `sunna_api.py` | REST API bridge for Sunna company data | 5100 |
| `sunna_executor.py` | Executive Director agent + Dashboard | 5105 |

#### sunna_api.py - Key Classes/Functions

```python
# Main Flask app
app = Flask(__name__)

# Key endpoints
GET  /health              # Basic health
GET  /health/deep         # Deep health with dependencies
GET  /metrics             # Prometheus metrics
GET  /v1/status           # Company snapshot
GET  /v1/bots             # Bot status
GET  /v1/research         # Research agents
GET  /v1/catalogue        # Product catalogue
GET  /v1/coordination     # Handoff + Hermes results
GET  /v1/tasks            # Task queue status
POST /v1/auth/token       # JWT authentication
WS   /v1/ws               # WebSocket for real-time
SSE  /v1/events           # Server-Sent Events
POST /v1/batch            # Batch operations
```

#### sunna_executor.py - Key Classes

```python
# Core classes
class SunnaDashboard:      # Flask + WebSocket dashboard
class SunnaTaskExecutor:   # Background task worker
class TaskQueue:           # Priority queue with scheduling
class SunnaTask:           # Task dataclass
class SunnaIntegrationManager:  # Main orchestrator
```

### brain/ - AI Brain

#### router.py - SmartRouter

```python
# Main class
class SmartRouter:
    def route(self, context: RoutingContext) -> RoutingResult

# Data classes
@dataclass
class RoutingContext:
    query: str
    conversation_history: List[Dict]
    preferred_engine: Optional[Engine]
    required_capabilities: List[str]
    max_latency: Optional[str]
    cost_preference: Optional[str]
    require_streaming: bool
    language: Optional[str]

@dataclass
class RoutingResult:
    engine: Engine
    confidence: float
    reasoning: str
    alternatives: List[Tuple[Engine, float]]
    fallback_chain: List[Engine]
    metadata: Dict

# Engines available
class Engine(Enum):
    HERMES, DOLPHIN, DEEPSEEK, METASPLOIT, CLOUD_CODE, KANBAN
    GLM, QWEN, KIMI, INKLING, OLMOE, LOCAL
```

#### self_evolution.py - SelfEvolution

```python
# Main class
class SelfEvolution:
    def analyze_code_quality(self) -> Dict
    def run_cycle(self, auto_apply: bool = False) -> Dict
    def get_history(self, limit: int) -> List[Dict]
    def get_trends(self) -> Dict
    def predict_issues(self) -> List[Dict]

# Issue types
class IssueType(Enum):
    TODO, FIXME, BARE_EXCEPT, LONG_FUNCTION, HIGH_COMPLEXITY
    DUPLICATE_CODE, MISSING_DOCSTRING, UNUSED_IMPORT
    SECURITY_RISK, PERFORMANCE, TYPE_HINT_MISSING, TEST_COVERAGE
```

### tools/colibri/ - Inference Tools

Key modules for model execution and optimization:

| Module | Purpose |
|--------|---------|
| `autotune.py` | Execution scheduling tuning |
| `doctor.py` | Engine diagnostics |
| `family_registry.py` | Model family registration |
| `openai_server.py` | OpenAI-compatible API server |
| `resource_plan.py` | Resource planning for models |
| `setup_flow.py` | Interactive setup wizard |

### G0DM0D3/ - Safety Research Framework

Core engines (TypeScript):

| Module | Lines | Purpose |
|--------|-------|---------|
| `src/lib/autotune.ts` | 639 | Context-adaptive parameters |
| `src/lib/autotune-feedback.ts` | ~200 | EMA feedback loop |
| `src/lib/parseltongue.ts` | 433 | Input perturbation |
| `src/stm/modules.ts` | 154 | Output normalization |
| `api/lib/ultraplinian.ts` | 360 | Multi-model evaluation |
| `api/lib/dataset.ts` | 162 | Dataset collection |
| `api/lib/metadata.ts` | ~400 | ZDR metadata tracker |

---

## 🔧 Development Workflow

### Adding a New Engine to Smart Router

1. **Add engine to ENGINE_CAPABILITIES** in `brain/router.py`:

```python
Engine.NEW_ENGINE: {
    "strengths": ["capability1", "capability2"],
    "max_tokens": 8192,
    "supports_streaming": True,
    "cost_tier": "local",
    "latency": "low",
}
```

2. **Add keywords** for routing:

```python
NEW_ENGINE_KEYWORDS = [
    "keyword1", "keyword2", "arabic_keyword",
]

# In _score_keywords():
new_score = sum(1 for kw in NEW_ENGINE_KEYWORDS if kw in query)
if new_score >= threshold:
    scores[Engine.NEW_ENGINE] += new_score * weight
```

3. **Test**:

```bash
python brain/router.py
```

### Adding a New API Endpoint

1. **In sunna_api.py**:

```python
@app.route("/v1/new-endpoint")
@optional_auth
@rate_limit(limit=50)
def new_endpoint():
    # Implementation
    return jsonify({"data": "result"})
```

2. **Add to OpenAPI spec** (if using)

3. **Test**:

```bash
curl http://localhost:5100/v1/new-endpoint
```

### Adding a New Scheduled Task

1. **In sunna_executor.py**, add to DEFAULT_TASKS:

```python
SunnaTask(
    id="custom_task",
    name="Custom Task Name",
    action="custom_action",
    schedule="0 3 * * *",  # Cron: daily at 3 AM
    priority=TaskPriority.NORMAL,
    tags=["custom", "tag"],
)
```

2. **Add action handler** in `_execute_action`:

```python
elif action == "custom_action":
    cmd = "python3 custom_script.py"
```

### Running Self-Evolution

```bash
# Analysis only
python brain/self_evolution.py --analyze

# Full cycle with auto-fix
python brain/self_evolution.py --cycle --auto-apply

# View history
python brain/self_evolution.py --history 20

# View trends
python brain/self_evolution.py --trends

# Predict issues
python brain/self_evolution.py --predict
```

---

## 🧪 Testing

### Unit Tests

```bash
# Python tests
python -m pytest tests/ -v

# Specific component
python -m pytest tests/test_router.py -v
python -m pytest tests/test_self_evolution.py -v
```

### Integration Tests

```bash
# Test API endpoints
python tests/test_api.py

# Test WebSocket
python tests/test_websocket.py

# Test task execution
python tests/test_executor.py
```

### G0DM0D3 Evaluation Scripts

```bash
cd G0DM0D3

# AutoTune classification
npx tsx research/eval_autotune_classification.ts

# Feedback convergence
npx tsx research/eval_feedback_convergence.ts

# STM precision
npx tsx research/eval_stm_precision.ts

# Scoring calibration
npx tsx research/eval_scoring_calibration.ts

# Parseltongue analysis
npx tsx research/eval_parseltongue_analysis.ts
```

### Manual Testing Checklist

- [ ] API health: `GET /health` returns 200
- [ ] Deep health: `GET /health/deep` checks dependencies
- [ ] Metrics: `GET /metrics` returns Prometheus format
- [ ] Auth: `POST /v1/auth/token` returns JWT
- [ ] WebSocket: Connect to `ws://localhost:5105/ws`
- [ ] SSE: Connect to `GET /v1/events`
- [ ] Dashboard: Load `http://localhost:5105`
- [ ] Task creation: POST to `/api/tasks`
- [ ] Task execution: WebSocket receives updates
- [ ] Evolution: Run cycle, check reports

---

## 🚀 Deployment

### Production Checklist

- [ ] Set strong `SUNNA_JWT_SECRET` in .env
- [ ] Set `ADMIN_PASSWORD` and `API_PASSWORD`
- [ ] Enable `RATE_LIMIT_ENABLED=true`
- [ ] Configure `LOG_LEVEL=INFO` or `WARNING`
- [ ] Set up SSL/TLS termination (nginx/Cloudflare)
- [ ] Configure Prometheus scraping
- [ ] Set up log aggregation
- [ ] Configure backup for `~/ESPRIEAETHER/data/`
- [ ] Set up monitoring alerts

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Data volumes
VOLUME ["/root/ESPRIEAETHER/data", "/app/Sunna-Equipe-Industrial"]

EXPOSE 5100 5105

CMD ["python", "src/sunna_executor.py"]
```

```bash
# Build
docker build -t esprieaether-sunna:latest .

# Run
docker run -d \
  --name esprieaether \
  -p 5100:5100 \
  -p 5105:5105 \
  -v /host/data:/root/ESPRIEAETHER/data \
  -v /host/Sunna:/app/Sunna-Equipe-Industrial \
  --env-file .env \
  --restart unless-stopped \
  esprieaether-sunna:latest
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: esprieaether-sunna
spec:
  replicas: 2
  selector:
    matchLabels:
      app: esprieaether-sunna
  template:
    metadata:
      labels:
        app: esprieaether-sunna
    spec:
      containers:
      - name: api
        image: esprieaether-sunna:latest
        command: ["python", "src/sunna_api.py"]
        ports:
        - containerPort: 5100
        envFrom:
        - secretRef:
            name: esprieaether-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      - name: executor
        image: esprieaether-sunna:latest
        command: ["python", "src/sunna_executor.py"]
        ports:
        - containerPort: 5105
        envFrom:
        - secretRef:
            name: esprieaether-secrets
```

### Monitoring Setup

**Prometheus** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'sunna-api'
    static_configs:
      - targets: ['sunna-api:5100']
  - job_name: 'sunna-dashboard'
    static_configs:
      - targets: ['sunna-dashboard:5105']
```

**Grafana Dashboards**:
- Import dashboard from `monitoring/grafana-dashboard.json`
- Key metrics: request rate, latency, error rate, task queue depth, WS connections

---

## 🤝 Contributing

### Code Style

```bash
# Python
black src/ brain/
isort src/ brain/
flake8 src/ brain/
mypy src/ brain/

# TypeScript (G0DM0D3)
cd G0DM0D3
npm run lint
npm run format
```

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with tests
4. Run full test suite
5. Update documentation
6. Submit PR with description

### Commit Convention

```
feat: add new engine to router
fix: resolve WebSocket reconnection bug
docs: update API documentation
refactor: simplify task queue logic
test: add integration tests for executor
chore: update dependencies
```

### Adding Documentation

- Code docstrings for all public functions/classes
- Update `DEVELOPER_GUIDE.md` for new features
- Update `PAPER.md` for research contributions
- Add Obsidian notes in `obsidian/Sunna-Equipe-Industrial/`

---

## 📚 Key References

| Document | Location |
|----------|----------|
| Research Paper | `G0DM0D3/PAPER.md` |
| API Documentation | `G0DM0D3/API.md` |
| Terms of Service | `G0DM0D3/TERMS.md` |
| Security Policy | `G0DM0D3/SECURITY.md` |
| Local Models Guide | `G0DM0D3/LOCAL_MODELS.md` |
| Company Docs | `obsidian/Sunna-Equipe-Industrial/` |

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: flask_sock` | `pip install flask-sock` |
| `Port 5100 already in use` | Kill existing process or change `SUNNA_API_PORT` |
| `JWT decode error` | Check `SUNNA_JWT_SECRET` matches in .env |
| `WebSocket connection fails` | Check firewall, ensure `flask-sock` installed |
| `Radon not found` | `pip install radon` (optional, for complexity) |
| `sklearn not found` | `pip install scikit-learn` (optional, for ML routing) |

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/sunna_executor.py

# API debug
export FLASK_DEBUG=1
python src/sunna_api.py
```

### Logs Location

- Application logs: stdout/stderr (capture with systemd/docker)
- Evolution reports: `evolution_reports/`
- Database: `~/ESPRIEAETHER/data/esprieaether.db`
- State: `src/sunna_state.json`

---

## 📄 License

This project is licensed under the AGPL-3.0 License - see the `G0DM0D3/LICENSE` file for details.

---

## 🙏 Acknowledgments

- **Elder Plinius** for G0DM0D3 framework
- **Sunna Équipe Industrial** for real-world integration
- **OpenRouter** for model gateway
- **Radon** for Python code metrics
- **scikit-learn** for ML classification

---

*Generated with ❤️ by the ESPRIEAETHER development team*