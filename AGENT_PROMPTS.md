# Agent Execution Prompts for Parallel Development

## Agent A: Backend Track Prompt
```
You are implementing the backend service for a Local Web Memory Chrome extension. 

CONTEXT: Build a FastAPI service that provides local indexing and search for web pages. The extension will send page content to be indexed with AI-generated keywords and vector embeddings.

TASK SEQUENCE:
1. **Phase 1A**: Build FastAPI backend with SQLite FTS5
   - FastAPI service on localhost:8000
   - SQLite database with FTS5 for keyword search
   - In-memory vector store (simple dot product similarity)
   - API endpoints: POST /index, GET /search/keyword, GET /search/vector, CRUD /pages
   - Mock data generator for testing

2. **Phase 4A**: Integrate ByteDance Ark APIs
   - LLM API for keyword/description generation
   - Embedding API for vector generation
   - Error handling and retry logic
   - Replace mock vectors with real embeddings

API CREDENTIALS:
export ARK_API_TOKEN="16997291-4771-4dc9-9a42-4acc930897fa"

LLM endpoint: https://ark-cn-beijing.bytedance.net/api/v3/chat/completions
Embedding endpoint: https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal

PROJECT PATH: /Users/bytedance/code/newtab
Use git for version control. Create backend/ directory with clean FastAPI structure.

DEMO GOALS:
- Phase 1A: Show API docs at /docs, index test data, search works
- Phase 4A: Show real AI-generated keywords improving search quality

Start with Phase 1A immediately. Build fast, test thoroughly.
```

## Agent B: Extension Track Prompt  
```
You are implementing the Chrome extension for a Local Web Memory system.

CONTEXT: Build a Chrome Extension (Manifest V3) that extracts content from visited web pages and sends it to a local backend for indexing. Users search their browsing history from a new tab interface.

TASK SEQUENCE:
1. **Phase 2B**: Chrome Extension Core
   - Manifest V3 with minimal permissions (tabs, activeTab, storage)
   - Content script for DOM content extraction
   - Service worker for background processing
   - Communication with localhost:8000 backend API
   - Basic popup showing indexing status

2. **Phase 3B**: Search Interface
   - New tab override with search bar
   - Real-time search as user types
   - Result cards showing title, description, URL
   - Click to open, delete actions
   - Settings panel for domain exclusions

PROJECT PATH: /Users/bytedance/code/newtab
Use git for version control. Create extension/ directory following MV3 best practices.

ARCHITECTURE:
- Content script extracts main content from web pages
- Service worker handles API calls to backend
- New tab page provides search interface
- All data stored via backend API (no extension storage)

DEMO GOALS:
- Phase 2B: Install extension, visit websites, show content indexed in backend
- Phase 3B: Open new tab, search for visited pages, results appear instantly

Start with Phase 2B immediately. Focus on clean MV3 architecture.
```

## Agent C: Integration & Testing Prompt
```
You are the integration engineer ensuring both tracks work together seamlessly.

CONTEXT: Monitor and test the backend service and Chrome extension as they're developed in parallel. Ensure proper integration and create comprehensive demos.

RESPONSIBILITIES:
1. **Integration Testing**: Verify extension communicates properly with backend
2. **Demo Preparation**: Create demo scripts showing each phase working
3. **Performance Testing**: Ensure <500ms search, <2s indexing targets
4. **Error Testing**: Test API failures, network issues, edge cases
5. **Documentation**: Update implementation progress and issues

PROJECT PATH: /Users/bytedance/code/newtab
Monitor both backend/ and extension/ directories.

INTEGRATION POINTS:
- Backend API must be CORS-enabled for extension
- Extension service worker must handle backend unavailability
- Search interface must handle both keyword and vector search types
- Error messages must be user-friendly

DEMO SCHEDULE:
- **Demo 1**: After Phase 1A + 2B complete (backend + basic extension)
- **Demo 2**: After all phases complete (full AI-powered search)

Test continuously, report issues immediately to respective agents.
```

## Execution Instructions
1. **Start 3 agents simultaneously** with above prompts
2. **Agent A**: Focus on backend implementation
3. **Agent B**: Focus on extension development  
4. **Agent C**: Monitor integration and prepare demos
5. **Sync points**: After Phase 1A+2B, and after all phases complete

Each agent should commit to git regularly and communicate progress through file updates.