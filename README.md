# TARA Course Generation Agent

AI-powered course generator using RAG, GitHub MCP, and web search to create comprehensive technical courses with quizzes and skills tracking.

## 🚀 Quick Start

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

# 3. Start API server
python main.py

# 4. Generate a course
curl -X POST http://localhost:8000/course/generate \
  -H "Content-Type: application/json" \
  -d '{"token_github":"","token_drive":"","prompt":"Create a Python basics course","files_url":""}'
```

## 📋 API Endpoint

**POST** `/course/generate`

**Request:**
```json
{
  "token_github": "ghp_xxxxx",
  "token_drive": "",
  "prompt": "Create a course on XGBoost deployment on Vertex AI",
  "files_url": ""
}
```

**Response:**
```json
{
  "title": "Course Title",
  "description": "Course overview",
  "difficulty": "Beginner|Intermediate|Advanced",
  "estimated_duration": 10,
  "learning_objectives": ["objective1", "objective2"],
  "skills": ["Python", "XGBoost", "Vertex AI", "MLOps"],
  "modules": [
    {
      "title": "Module 1",
      "index": 1,
      "lessons": [
        {
          "title": "Lesson 1",
          "index": 1,
          "content": "# Lesson content in Markdown..."
        }
      ],
      "quiz": [
        {
          "question": "What is...?",
          "choices": {"A": "Option A", "B": "Option B", "C": "Option C"},
          "answer": "B"
        }
      ]
    }
  ],
  "source_from": ["https://github.com/org/repo"]
}
```

## 🏗️ How It Works

```
User Request → Agent
    ↓
1. RAG Search (Internal Knowledge) - Priority
    ↓
2. GitHub MCP (Code Examples) - Fallback
    ↓
3. Google Search (Web Resources) - Final Fallback
    ↓
Generated Course (JSON with quiz + skills)
```

**Key Features:**
- ✅ Multi-source content discovery (RAG → GitHub → Web)
- ✅ Real code examples from discovered repositories
- ✅ Automatic quiz generation (2-4 questions per module)
- ✅ Skills extraction (8-12 relevant skills)
- ✅ Source tracking and attribution

## ⚙️ Configuration

### Required Environment Variables
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx  # Optional for GitHub MCP
```

### Optional Overrides
```bash
COURSE_AGENT_SOURCE_PRIORITY=rag_first  # rag_first|github_first|balanced
COURSE_AGENT_MAX_REPOSITORIES=5
COURSE_AGENT_RAG_MAX_RESULTS=2
COURSE_AGENT_LOG_LEVEL=INFO
```

## 🗂️ Project Structure

```
tara-ai-ml-agent/
├── main.py                      # FastAPI server
├── course_agent/
│   ├── agents/
│   │   └── course_agent.py      # Main agent with ADK
│   ├── config/
│   │   └── settings.py          # Configuration
│   ├── tools/
│   │   ├── rag_tool.py         # RAG search
│   │   ├── github_tool.py      # GitHub MCP
│   │   └── search_tool.py      # Google Search
│   ├── core/
│   │   └── source_manager.py    # Source orchestration
│   └── rag_processor.py        # BigQuery Vector Search
└── requirements.txt
```

## 🧪 Testing

```bash
# Test new format with quiz and skills
python test_new_format.py

# Health check
curl http://localhost:8000/
```

## 📚 Documentation

- **[API_DEV_SUMMARY.md](API_DEV_SUMMARY.md)** - Complete API implementation details

## 🔧 Technologies

- **Google ADK** - Agent framework with tool orchestration
- **Vertex AI** - Gemini 2.5 Flash model
- **BigQuery Vector Search** - RAG knowledge base
- **GitHub MCP** - Repository and code search
- **FastAPI** - REST API server
- **LlamaIndex** - Document parsing and chunking
- **LangChain** - Vector store integration

---

**Version:** 2.1.0 | Updated: 2025-01-03
