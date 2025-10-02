# TARA Course Generation Agent

An intelligent AI agent that automatically generates technical courses by combining internal knowledge (RAG), GitHub repositories (MCP), and web search to create comprehensive, practical learning content.

## 🚀 Quick Start

### API Server
```bash
# 1. Setup environment
cp .env.example .env  # Add your tokens

# 2. Start server
python main.py

# 3. Generate a course
curl -X POST http://localhost:8000/course/generate \
  -H "Content-Type: application/json" \
  -d '{"token_github":"","token_drive":"","prompt":"Create a Python course","files_url":""}'
```

**API Endpoint**: `POST /course/generate`
- ✅ Full agent functionality (RAG + GitHub + Search)
- ✅ Real-time course generation from discovered sources
- ✅ Returns structured JSON with 30K+ chars
- 📚 See [API_DEV_SUMMARY.md](API_DEV_SUMMARY.md) for complete API docs

## 🏗️ Architecture Overview

```
TARA Agent
├── Agent Core (Google ADK)
├── Source Discovery System (3-tier)
│   ├── 1. RAG (Internal Knowledge) - Priority
│   ├── 2. GitHub MCP (Code Examples) - Fallback
│   └── 3. Google Search (Web Resources) - Final Fallback
├── Configuration System
├── Source Tracking & Validation
└── Course Generation Pipeline
```

## 🧠 How the Agent Works

### 1. **Agent Initialization**
```python
from course_agent import course_generator

# The agent is automatically initialized with:
# - 7 custom function tools
# - GitHub MCP toolset (if token available)
# - Google Search integration
# - RAG processor connection
```

### 2. **Content Discovery Process**
When you request a course on a topic (e.g., "Machine Learning with XGBoost on GCP"):

```
Input: "XGBoost deployment on GCP"
    ↓
1. 🎯 RAG Search (Internal Knowledge Base)
   ├── Searches preprocessed internal repos
   ├── Checks relevance threshold (0.7)
   └── Returns internal best practices
    ↓
2. 🔗 GitHub MCP (if RAG insufficient)
   ├── search_repositories("xgboost gcp")
   ├── get_file_contents("repo/deployment.py")
   ├── search_code("xgboost train")
   └── Returns live code examples
    ↓
3. 🌐 Google Search (if both insufficient)
   ├── Searches for tutorials & documentation
   ├── Filters educational content
   └── Returns web learning resources
    ↓
4. 📚 Course Generation
   ├── Combines all discovered content
   ├── Structures into modules/lessons
   ├── Includes real code examples
   └── Outputs JSON course with source tracking
```

### 3. **Intelligent Source Priority**
- **RAG_FIRST** (default): Internal knowledge → GitHub → Web
- **GITHUB_FIRST**: External code → Internal knowledge → Web
- **BALANCED**: Concurrent search across sources

## 🛠️ Tools & Components

### **Core Agent Tools**
| Tool | Purpose | Example |
|------|---------|---------|
| `analyze_tech_stack` | Determine complexity & tech category | ML, Cloud, Web Dev |
| `discover_sources` | Find relevant content from all sources | RAG + GitHub + Search |
| `extract_repository_content` | Get specific files from repos | `repo/src/model.py` |
| `generate_search_queries` | Create multiple search variations | "xgboost", "ml deployment" |
| `save_course_to_file` | Export course with tracking data | JSON with metadata |

### **GitHub MCP Tools** (Dynamic)
| Tool | Purpose |
|------|---------|
| `search_repositories` | Find GitHub repos by topic |
| `get_file_contents` | Extract actual code files |
| `search_code` | Find specific code patterns |
| `list_projects` | Browse organization repos |

### **Source Management**
```python
# Source Manager orchestrates all content discovery
class SourceManager:
    rag_tool: RAGTool           # Internal knowledge base
    github_tool: GitHubMCPTool  # Live GitHub integration
    search_tool: GoogleSearchTool # Web content discovery
```

## ⚙️ Configuration

### **Environment Variables** (Required)
```bash
# GitHub Integration
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_your_token"

# Google Cloud (for RAG/Vertex AI)
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### **Configuration Hierarchy**
1. **Dataclass Defaults** (`config/settings.py`)
2. **Environment Overrides** (optional)

```python
# Default Configuration
@dataclass
class AgentConfig:
    name: str = "course_generator"
    model_name: str = "gemini-2.5-flash"
    source_priority: SourcePriority = SourcePriority.RAG_FIRST

    # Sub-configurations
    mcp: MCPConfig              # GitHub settings
    rag: RAGConfig              # Vector search settings
    course: CourseConfig        # Course generation params
```

### **Optional Environment Overrides**
```bash
export COURSE_AGENT_SOURCE_PRIORITY="balanced"
export COURSE_AGENT_MAX_REPOSITORIES="10"
export COURSE_AGENT_RAG_MAX_RESULTS="8"
export COURSE_AGENT_LOG_LEVEL="DEBUG"
```

## 🗂️ Project Structure

```
course_agent/
├── agents/
│   └── course_agent.py       # Main agent implementation
├── config/
│   └── settings.py          # Configuration system
├── core/
│   ├── source_manager.py    # Content discovery orchestration
│   └── enhanced_source_tracker.py # Source validation & tracking
├── tools/
│   ├── rag_tool.py         # Internal knowledge search
│   ├── github_tool.py      # GitHub MCP integration
│   ├── search_tool.py      # Google Search integration
│   └── base.py             # Tool interfaces
├── utils/
│   ├── logger.py           # Logging system
│   └── json_encoder.py     # JSON serialization fixes
└── rag_processor.py        # RAG vector store integration
```

## 🚀 Usage Examples

### **1. REST API (Recommended)**
```bash
# Start the FastAPI server
python main.py

# Generate a course via HTTP
curl -X POST http://localhost:8000/course/generate \
  -H "Content-Type: application/json" \
  -d '{
    "token_github": "ghp_xxxxx",
    "token_drive": "",
    "prompt": "Create a course on XGBoost deployment on Vertex AI",
    "files_url": ""
  }'

# Response: Full course JSON (30K+ chars)
{
  "title": "XGBoost Deployment on Vertex AI",
  "modules": [...],
  "source_from": ["https://github.com/..."]
}
```

### **2. Python Library**
```python
from course_agent import CourseGenerationAgent

# Create agent with dynamic tokens
agent = CourseGenerationAgent(
    github_token="ghp_xxxxx",
    drive_token=""
)

# Analyze topic
analysis = agent.analyze_tech_stack("machine learning deployment")

# Discover sources (uses RAG + GitHub + Search)
sources = await agent.discover_sources("XGBoost GCP deployment")

# Get tracked sources
source_urls = agent.get_tracked_sources()
```

### **3. Configuration Status**
```python
from course_agent import get_agent_status

status = get_agent_status()
print(f"GitHub available: {status['github_available']}")
print(f"RAG available: {status['rag_available']}")
print(f"Source priority: {status['source_priority']}")
```

## 🔧 RAG Integration

### **Vector Store Backend**
- **BigQuery Vector Search** for scalable internal knowledge
- **Automatic chunking** with language-specific splitters
- **Relevance filtering** with configurable thresholds

### **Update Frequencies** (Recommended)
- **High-priority repos**: Daily updates
- **Medium-priority repos**: Weekly updates
- **Low-priority repos**: Monthly updates
- **Event-driven**: Webhook-triggered updates on commits

### **RAG Configuration**
```python
rag_config = RAGConfig(
    max_results=2,              # Optimized to avoid token limits
    relevance_threshold=0.7,
    chunk_size=1000,
    chunk_overlap=200
)
```

## 🔍 Source Tracking

All generated courses include comprehensive source tracking:

```json
{
  "title": "XGBoost Deployment on GCP",
  "source_from": [
    "https://github.com/org/ml-deployment",
    "internal/ml-practices.md"
  ],
  "source_tracking": {
    "rag_sources": 3,
    "github_sources": 2,
    "search_sources": 1,
    "total_confidence": 0.89
  },
  "generation_metadata": {
    "generated_at": "2025-09-28T10:00:00Z",
    "source_priority": "rag_first",
    "github_enabled": true
  }
}
```

## 🛡️ Security Features

- **No secrets in code**: All tokens via environment variables
- **JSON serialization fixes**: Handles Pydantic URL types
- **Source validation**: Relevance and quality checking
- **Configurable thresholds**: Minimum repository stars, relevance scores

## 🔧 Development

### **Installation**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
EOF

# 3. Test installation
python -c "from course_agent import course_generator; print('✅ Agent ready')"
```

### **Running the API Server**
```bash
# Development
python main.py

# Production with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### **Testing**
```bash
# Automated test
python test_api.py

# Manual test
curl http://localhost:8000/
```

## 📊 Architecture Benefits

1. **Multi-Source Intelligence**: Combines internal expertise with external innovation
2. **Fallback Reliability**: Never fails to find content (3-tier system)
3. **Real Code Examples**: Actual implementation from live repositories
4. **Source Transparency**: Full tracking of content origins
5. **Flexible Configuration**: Environment-based customization
6. **Scalable RAG**: BigQuery Vector Search for large-scale knowledge

## 🤝 Contributing

The agent uses a modular architecture making it easy to:
- Add new content sources (implement `ContentSource` interface)
- Customize search strategies (modify `SourceManager`)
- Extend course generation (enhance agent instructions)
- Improve source tracking (extend `EnhancedSourceTracker`)

---

**TARA Agent v2.0** - Intelligent course generation through multi-source content discovery.