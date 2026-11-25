# ESPRIEAETHER-SUNNA Architecture

> **Version**: 2.0  
> **Generated**: 2026-11-20

---

## 🏛 System Architecture Diagram

```mermaid
graph TB
    subgraph "External Access"
        UI[Web Dashboard :5105]
        API_CLIENT[API Clients]
        WS_CLIENT[WebSocket Clients]
        SSE_CLIENT[SSE Clients]
    end

    subgraph "Load Balancer / Reverse Proxy"
        LB[Nginx / Cloudflare]
    end

    subgraph "ESPRIEAETHER Agent OS"
        subgraph "Sunna API Bridge :5100"
            API[Flask App]
            WS_API[WebSocket /v1/ws]
            SSE_API[SSE /v1/events]
            AUTH[JWT Auth]
            RATE[Rate Limiter]
            METRICS_API[Prometheus /metrics]
        end

        subgraph "Sunna Executor :5105"
            DASH[Flask Dashboard]
            WS_DASH[WebSocket /ws]
            TASK_QUEUE[Task Queue + Scheduler]
            EXECUTOR[Task Executor]
            STATE[Persistent State JSON]
        end

        subgraph "AI Brain"
            ROUTER[Smart Router]
            ML_ROUTER[ML Classifier]
            EVOLUTION[Self-Evolution Engine]
            ANALYZER[Code Analyzer]
            FIXER[Auto-Fixer]
        end

        subgraph "Data Layer"
            SQLITE[(SQLite DB)]
            FILES[Sunna Workspace Files]
            REDIS[(Redis Cache)]
        end
    end

    subgraph "External Services"
        OPENROUTER[OpenRouter API]
        VENICE[Venice AI]
        LOCAL_MODELS[Local Models]
        HF[HuggingFace]
        NETLIFY[Netlify]
        CF[Cloudflare]
    end

    UI --> LB
    API_CLIENT --> LB
    WS_CLIENT --> LB
    SSE_CLIENT --> LB

    LB --> API
    LB --> DASH

    API --> WS_API
    API --> SSE_API
    API --> AUTH
    API --> RATE
    API --> METRICS_API

    API --> ROUTER
    API --> FILES
    API --> SQLITE

    DASH --> WS_DASH
    DASH --> TASK_QUEUE
    DASH --> EXECUTOR
    DASH --> STATE

    TASK_QUEUE --> EXECUTOR
    EXECUTOR --> ROUTER
    EXECUTOR --> FILES
    EXECUTOR --> SQLITE

    ROUTER --> ML_ROUTER
    ROUTER --> EVOLUTION

    EVOLUTION --> ANALYZER
    EVOLUTION --> FIXER
    EVOLUTION --> SQLITE

    API --> OPENROUTER
    API --> VENICE
    API --> LOCAL_MODELS
    EVOLUTION --> HF
    DASH --> NETLIFY
    API --> CF

    REDIS -.-> API
    REDIS -.-> DASH
```

---

## 🔄 Data Flow Diagrams

### Request Flow (API Bridge)

```mermaid
sequenceDiagram
    participant Client
    participant LB as Load Balancer
    participant API as Sunna API
    participant Auth as JWT Auth
    participant Rate as Rate Limiter
    participant Router as Smart Router
    participant Files as Sunna Workspace
    participant Metrics as Prometheus

    Client->>LB: HTTP Request
    LB->>API: Forward Request
    API->>Auth: Validate JWT (if required)
    API->>Rate: Check Rate Limit
    Rate-->>API: Allow/Deny
    API->>Router: Route Decision (if needed)
    API->>Files: Read Workspace Data
    API->>Metrics: Record Metrics
    API-->>Client: JSON Response
```

### Task Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Dash as Dashboard
    participant Queue as Task Queue
    participant Exec as Executor
    participant Router as Smart Router
    participant WS as WebSocket
    participant State as Persistent State

    User->>Dash: Create Task (UI)
    Dash->>Queue: Add Task
    Queue->>State: Persist Task
    Dash->>WS: Broadcast "task_update"
    WS-->>User: Real-time Update

    loop Scheduler
        Queue->>Queue: Check Due Tasks
        Queue->>Exec: Queue Task
    end

    Exec->>Exec: Start Task
    Exec->>State: Update Status=RUNNING
    Exec->>WS: Broadcast "task_update"
    Exec->>Router: Route Action (if needed)
    Exec->>Exec: Execute Command
    Exec->>State: Update Status=COMPLETED/FAILED
    Exec->>WS: Broadcast "task_completed/failed"
    WS-->>User: Real-time Result
```

### Self-Evolution Flow

```mermaid
sequenceDiagram
    participant Scheduler
    participant Evolution as Self-Evolution
    participant Analyzer as Code Analyzer
    participant Fixer as Auto-Fixer
    participant DB as SQLite
    participant Reports as Reports Dir
    participant WS as WebSocket

    Scheduler->>Evolution: Trigger Cycle
    Evolution->>Analyzer: Analyze All Files
    Analyzer-->>Evolution: Issues + Metrics
    Evolution->>DB: Store Metrics
    Evolution->>Reports: Generate JSON/HTML Report

    alt Auto-Apply Enabled
        Evolution->>Fixer: Generate Fixes
        Fixer-->>Evolution: Diffs
        Evolution->>Evolution: Apply Safe Fixes
        Evolution->>DB: Record Improvements
        Evolution->>WS: Broadcast "evolution_update"
    end

    Evolution-->>Scheduler: Cycle Complete
```

---

## 🧩 Component Interaction Matrix

| Component | sunna_api | sunna_executor | router | self_evolution | colibri | G0DM0D3 |
|-----------|-----------|----------------|--------|----------------|---------|---------|
| **sunna_api** | — | HTTP + WS | Calls | Reads metrics | — | — |
| **sunna_executor** | HTTP + WS | — | Calls | Triggers cycles | Calls | — |
| **router** | — | — | — | Gets feedback | — | — |
| **self_evolution** | — | Triggered by | — | — | Analyzes | — |
| **colibri** | — | Called by | — | Analyzed by | — | — |
| **G0DM0D3** | — | — | — | — | — | Standalone |

---

## 🔌 Port Allocation

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| 5000 | Web Interface | HTTP | Main web UI |
| 5001 | Cloud Desktop | HTTP | Desktop streaming |
| 5100 | Sunna API Bridge | HTTP/WS/SSE | Company data API |
| 5105 | Sunna Dashboard | HTTP/WS | Executive Director UI |
| 8000 | Agent OS / JARVIS | HTTP | Agent orchestration |
| 11434 | Ollama | HTTP | Local LLM server |
| 11435 | Router | HTTP | Internal routing |
| 6379 | Redis | TCP | Caching/Sessions |
| 9090 | Prometheus | HTTP | Metrics scraping |
| 3000 | Grafana | HTTP | Visualization |

---

## 📊 State Management

### Sunna API State (In-Memory + Workspace Files)
- Company info (static)
- Team structure (static)
- File listings (dynamic, read from disk)
- Bot schedules (static config)
- Research agents (static config)

### Sunna Executor State (Persistent JSON + SQLite)
```json
{
  "status": "running",
  "last_veille": "2026-11-20T10:00:00Z",
  "last_prices": "2026-11-20T08:00:00Z",
  "tasks": { "task_id": { ... } },
  "metrics": {
    "tasks_executed": 42,
    "tasks_failed": 3,
    "uptime_start": "2026-11-19T00:00:00Z"
  }
}
```

### Evolution State (SQLite)
- `evolution_log`: Cycle history
- `improvements`: Applied fixes
- `code_metrics`: Complexity trends
- `performance_baselines`: Regression detection

### Router State (In-Memory + SQLite)
- `routing_history`: Last 1000 decisions
- `engine_health`: Success/error/latency per engine
- `confidence_calibration`: Learned per-engine factors

---

## 🛡 Security Architecture

```mermaid
graph LR
    subgraph "Authentication"
        JWT[JWT Tokens<br/>HS256<br/>24h expiry]
        API_KEY[API Keys<br/>Header: Authorization]
    end

    subgraph "Authorization"
        ROLES[Roles: admin, user]
        SCOPES[Scopes: read, write, execute]
    end

    subgraph "Transport"
        TLS[TLS 1.3<br/>Terminated at LB]
        CORS[CORS Policy<br/>Configurable origins]
    end

    subgraph "Application"
        RATE[Rate Limiting<br/>100 req/min default]
        VALIDATE[Input Validation<br/>Pydantic schemas]
        SANITIZE[Output Sanitization<br/>No PII in logs]
    end

    JWT --> ROLES
    API_KEY --> SCOPES
    TLS --> RATE
    RATE --> VALIDATE
    VALIDATE --> SANITIZE
```

---

## 📈 Scaling Considerations

### Horizontal Scaling
- **Sunna API**: Stateless, can run multiple replicas behind LB
- **Sunna Executor**: Single leader for task execution (use Redis lock)
- **Dashboard**: Sticky sessions for WebSocket, or use Redis pub/sub

### Vertical Scaling
- Increase worker threads for Flask: `threaded=True`
- Use gunicorn for production: `gunicorn -w 4 -k gevent src.sunna_api:app`

### Database
- SQLite: Single writer, multiple readers (current)
- PostgreSQL: For multi-replica deployments (future)

### Caching
- Redis for: Session storage, Rate limit windows, Task queue coordination
- In-memory: Router decisions, Engine health, Evolution metrics

---

## 🔄 Failure Modes & Mitigations

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| API Bridge down | `/health/deep` fails | Dashboard shows degraded, cached data |
| Executor down | WebSocket disconnect | Auto-reconnect, task queue persists |
| Database locked | SQLite error | Retry with backoff, WAL mode |
| Model API down | Router health check | Fallback chain activation |
| Disk full | Metrics alert | Log rotation, cleanup old reports |
| Memory leak | Prometheus alerts | Restart policy, memory limits |

---

## 📝 Deployment Topology

### Development
```
localhost
├── sunna_api.py (5100)
├── sunna_executor.py (5105)
├── ollama (11434)
└── sqlite (local)
```

### Production (Single Server)
```
production-server
├── nginx (80/443) → TLS termination
├── gunicorn → sunna_api (5100, 4 workers)
├── gunicorn → sunna_executor (5105, 2 workers)
├── redis (6379)
├── ollama (11434)
├── prometheus (9090)
├── grafana (3000)
└── postgresql (5432) [optional]
```

### Production (Kubernetes)
```yaml
# See DEPLOYMENT.md for full manifests
Deployments:
  - sunna-api (3 replicas, HPA)
  - sunna-executor (1 replica, leader election)
  - sunna-dashboard (2 replicas, sticky sessions)
StatefulSets:
  - redis (1 replica)
  - postgresql (1 replica)
Services:
  - sunna-api (ClusterIP)
  - sunna-executor (ClusterIP)
  - sunna-dashboard (LoadBalancer)
Ingress:
  - api.esprieaether.com → sunna-api
  - dashboard.esprieaether.com → sunna-dashboard
```

---

## 🔮 Future Architecture Evolution

### Planned Enhancements

1. **Distributed Agent Coordination**
   - gRPC/Protobuf for inter-agent communication
   - Consensus protocols for multi-agent decisions
   - Event sourcing for audit trails

2. **Advanced ML Pipeline**
   - Online learning for router
   - Embedding-based semantic routing
   - A/B testing framework for engine selection

3. **Enhanced Observability**
   - OpenTelemetry integration
   - Distributed tracing (Jaeger)
   - Custom Grafana dashboards per component

4. **Security Hardening**
   - mTLS between services
   - SPIFFE/SPIRE for identity
   - Policy engine (OPA) for authorization

5. **Data Pipeline**
   - Kafka for event streaming
   - ClickHouse for analytics
   - Airflow for scheduled workflows

---

*Architecture documentation generated from code analysis. Update when components change.*