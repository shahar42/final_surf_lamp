# Render MCP Server Architecture Documentation

## 🏗️ System Overview

The Render MCP Server provides real-time access to Render platform APIs through a FastMCP-based interface, specifically designed for debugging the Surf Lamp background processor. It eliminates the need for manual log copying and provides structured access to production data.

## 📁 Project Structure

```
render-mcp-server/
├── main.py              # FastMCP server entry point & tool registration
├── config.py            # Pydantic settings with type-safe environment management
├── render_client.py     # Async HTTP client with retry logic & rate limiting
├── tools/
│   ├── logs.py         # Log fetching and searching tools
│   ├── deployments.py  # Deployment and service status tools
│   └── metrics.py      # Performance metrics tools
├── requirements.txt     # Dependencies (FastMCP, aiohttp, pydantic-settings)
├── .env.example        # Environment template
├── .env                # Environment variables (API keys, service IDs)
├── .gitignore          # Git ignore rules
├── README.md           # User documentation
└── ARCHITECTURE.md     # This file
```

## 🔧 Core Components

### 1. FastMCP Framework Integration

**File:** `main.py`

**Purpose:** Server initialization and tool registration

**Key Features:**
- **Modern MCP server** implementation using decorators
- **Async tool registration** with type hints and docstrings
- **Stdio transport** for local Claude Code integration
- **Lifecycle management** for HTTP session startup/shutdown

**Implementation Pattern:**
```python
from fastmcp import FastMCP
from tools.logs import get_render_logs, search_logs, get_recent_errors
from tools.deployments import get_deployments, get_service_status
from tools.metrics import get_service_metrics

mcp = FastMCP(name="RenderServer")

# Register all tools with decorators
@mcp.tool()
async def render_logs(...):
    return await get_render_logs(...)
```

### 2. Configuration Management

**File:** `config.py`

**Purpose:** Type-safe environment variable handling

**Key Features:**
- **Pydantic Settings** for validation and type safety
- **Environment variable loading** with dotenv support
- **Required field validation** with clear error messages
- **Production-ready defaults** with override capabilities

**Configuration Schema:**
```python
class Settings(BaseSettings):
    RENDER_API_KEY: str                    # Required: Render API authentication
    SERVICE_ID: str                        # Required: Target service identifier
    RENDER_BASE_URL: str = "https://..."   # Optional: API endpoint override
    MAX_LOGS_PER_REQUEST: int = 100        # Optional: Pagination control
    REQUEST_TIMEOUT: int = 30              # Optional: HTTP timeout
    MAX_RETRIES: int = 5                   # Optional: Retry attempts
```

### 3. Async HTTP Client

**File:** `render_client.py`

**Purpose:** Robust API communication with Render platform

**Key Features:**
- **aiohttp.ClientSession** with connection pooling
- **Exponential backoff** retry logic for 429 rate limit responses
- **Automatic cursor-based pagination** handling
- **Circuit breaker pattern** to prevent API hammering
- **Structured error handling** with meaningful Claude-readable messages

**Architecture Components:**

#### HTTP Session Management
```python
# Global session with connection pooling
client_session: aiohttp.ClientSession = None

async def startup():
    global client_session
    client_session = aiohttp.ClientSession(
        base_url=settings.RENDER_BASE_URL,
        headers={"Authorization": f"Bearer {settings.RENDER_API_KEY}"},
        timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    )

async def shutdown():
    if client_session:
        await client_session.close()
```

#### Rate Limiting Strategy
- **429 Detection**: Reads `Retry-After` headers from Render API responses
- **Exponential Backoff**: 1s, 2s, 4s, 8s delays with jitter to prevent thundering herd
- **Circuit Breaker**: Fails fast after 5 consecutive rate limit errors
- **Request Spacing**: Built-in delays between paginated requests

#### Pagination Engine
- **Cursor-based iteration** through Render API responses
- **Automatic aggregation** of results across multiple pages
- **Smart truncation** for large log volumes (first N + last N lines)
- **hasMore detection** to stop pagination appropriately

### 4. Tool Implementation Modules

#### Log Tools (`tools/logs.py`)

**Purpose:** Real-time log access and searching

**Available Tools:**
- `get_render_logs()` - Filtered log retrieval with time ranges
- `search_logs()` - Text pattern searching across logs
- `get_recent_errors()` - Automatic error detection and categorization

**Key Features:**
- **Time range filtering** with ISO 8601 or relative formats ("2h", "30m")
- **Severity filtering** (error, warn, info, debug)
- **Smart formatting** with timestamps and line numbers
- **Truncation strategy** for large result sets
- **Error context** preservation

**Implementation Pattern:**
```python
async def get_render_logs(
    service_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    severity: Optional[str] = None
) -> str:
    """
    Fetch logs with comprehensive filtering and pagination
    Returns formatted logs optimized for Claude analysis
    """
    # Handle pagination automatically
    # Apply filters and formatting
    # Implement smart truncation
```

#### Deployment Tools (`tools/deployments.py`)

**Purpose:** Deployment monitoring and service health

**Available Tools:**
- `get_deployments()` - Deployment history with status tracking
- `get_service_status()` - Current service health and configuration
- `get_latest_deployment_logs()` - Logs from most recent deployment

**Key Features:**
- **Deployment status tracking** (building, live, failed, cancelled)
- **Timing analysis** (deploy duration, start/end times)
- **Git commit correlation** when available from Render
- **Failure reason extraction** from deployment logs
- **Service configuration overview** (memory, CPU, environment)

#### Metrics Tools (`tools/metrics.py`)

**Purpose:** Performance monitoring and trend analysis

**Available Tools:**
- `get_service_metrics()` - CPU, memory, request metrics with time series
- `get_health_check()` - Comprehensive system overview combining logs, deployments, and metrics

**Key Features:**
- **Time series data** with configurable lookback windows
- **Metric type filtering** (cpu, memory, requests, response_time)
- **Trend analysis** with peak/average calculations
- **Correlation detection** between metrics and deployment events

## 🔒 Security Architecture

### API Key Management
- **Environment variable storage** only - no hardcoded credentials
- **Validation on startup** with secure error messages
- **Key rotation support** through configuration reload
- **Scope limitation** - read-only access to specified service

### Input Validation
- **Pydantic models** for all tool parameters with type checking
- **Time range validation** to prevent excessive API usage
- **Service ID validation** to prevent unauthorized access
- **Rate limiting** built into client to respect API quotas

### Network Security
- **HTTPS-only** communication with Render API
- **Local stdio transport** - no network exposure of MCP server
- **Connection pooling** with timeout limits
- **Error message sanitization** to prevent information disclosure

## 🚀 Performance Optimizations

### Connection Management
- **Persistent HTTP connections** to Render API
- **Connection limits** to prevent resource exhaustion
- **Timeout configuration** optimized for different request types
- **Graceful degradation** when API is slow or unavailable

### Response Handling
- **Smart caching** for deployment and service info (5-minute TTL)
- **Memory-efficient** streaming for large log responses
- **Compression support** for reduced bandwidth usage
- **Concurrent request limits** to prevent overwhelming Render API

### Data Processing
- **Incremental parsing** for large JSON responses
- **Result streaming** for real-time log access
- **Smart truncation** algorithms for optimal Claude consumption
- **Efficient text searching** with regex compilation caching

## 🔄 Error Handling Architecture

### Classification System
```python
# HTTP errors mapped to meaningful categories
if resp.status == 401:
    raise AuthenticationError("Invalid Render API key")
elif resp.status == 404:
    raise ServiceNotFoundError(f"Service {service_id} not found")
elif resp.status == 429:
    # Handled by retry logic with exponential backoff
elif resp.status >= 500:
    raise RenderAPIError("Render service temporarily unavailable")
```

### Recovery Strategies
- **Automatic retries** with intelligent backoff for transient failures
- **Graceful degradation** when partial data is available
- **Context preservation** for debugging failed requests
- **Alternative data sources** when primary endpoints fail

### User Experience
- **Clear error messages** with actionable suggestions
- **Partial results** when some data is unavailable
- **Retry suggestions** with estimated wait times
- **Status indicators** for ongoing operations

## 🧪 Testing Strategy

### Unit Testing
- **Mock Render API responses** for reliable testing
- **Configuration validation** testing
- **Error handling** verification
- **Pagination logic** validation

### Integration Testing
- **Real API calls** with test service
- **Rate limiting** behavior verification
- **Authentication** validation
- **Error recovery** testing

### Performance Testing
- **Large log volume** handling
- **Concurrent request** behavior
- **Memory usage** under load
- **Response time** optimization

## 📊 Monitoring and Observability

### Logging Strategy
- **Structured logging** with JSON format for parsing
- **Request/response logging** for debugging
- **Performance metrics** (response times, error rates)
- **User interaction tracking** for tool usage analysis

### Health Monitoring
- **API connection status** monitoring
- **Rate limit usage** tracking
- **Error rate** alerting
- **Performance degradation** detection

## 🔮 Future Architecture Considerations

### Scalability
- **Multi-service support** for complex deployments
- **Horizontal scaling** with service discovery
- **Load balancing** across multiple Render regions
- **Caching layers** for frequently accessed data

### Advanced Features
- **Real-time log streaming** with WebSocket support
- **Alert integration** with external notification systems
- **Custom dashboard** generation for visual metrics
- **Machine learning** for anomaly detection in logs

### Platform Extensions
- **Multi-cloud support** (AWS, GCP, Azure monitoring)
- **Database integration** for historical analysis
- **Custom metric** collection and analysis
- **Automated remediation** based on error patterns

## 🎯 Design Principles

### Reliability
- **Fail-safe defaults** - system degrades gracefully
- **Idempotent operations** - safe to retry
- **Circuit breaker** patterns for external dependencies
- **Comprehensive error handling** at all levels

### Performance
- **Async-first design** for high concurrency
- **Connection pooling** for efficiency
- **Smart caching** for reduced API calls
- **Streaming responses** for large datasets

### Maintainability
- **Type safety** throughout the codebase
- **Clear separation** of concerns
- **Comprehensive documentation** with examples
- **Modular architecture** for easy extension

### User Experience
- **Claude-optimized** response formatting
- **Intuitive tool names** and parameters
- **Helpful error messages** with context
- **Consistent behavior** across all tools

This architecture provides a robust, scalable foundation for real-time Render platform monitoring while maintaining simplicity and reliability for production debugging workflows.