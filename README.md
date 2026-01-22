# Scoop AI Backend v2.0

Real-time AI assistant for Scoop.ge sports nutrition e-commerce platform. Features a **Unified Conversation Engine** with Georgian language support and live product recommendations.

## 🚀 What's New in v2.0

- **Unified Engine Architecture** - Single codebase for both streaming and non-streaming endpoints
- **Fail-Safe Error Handling** - Predictable error states with retry logic (no more fallback heuristics)
- **186+ Unit Tests** - Comprehensive test coverage for all components
- **46% Code Reduction** - main.py reduced from 3,162 to 1,710 lines

## Features

- 🧠 **Gemini 2.5 Flash** - Powered by Google's latest AI model
- 🔍 **Smart Product Search** - MongoDB + Vector Search integration
- 💬 **Session Management** - Persistent chat history
- ⚡ **SSE Streaming** - Real-time response streaming
- 🇬🇪 **Georgian Language** - Full Georgian language support
- 🔄 **Context Caching** - 85% token savings with cached system prompts

## Tech Stack

- **Framework:** FastAPI
- **AI:** Google Gemini 3 Flash (`gemini-3-flash-preview`)
- **Database:** MongoDB Atlas with Vector Search
- **Streaming:** Server-Sent Events (SSE)
- **Testing:** pytest (186+ tests)

## Quick Start

```bash
# Clone repository
git clone https://github.com/Maqashable-284/scoop-ai-backend.git
cd scoop-ai-backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-api-key"
export MONGODB_URI="your-mongodb-uri"

# Run development server
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Non-streaming chat endpoint |
| `/chat/stream` | POST | SSE streaming chat endpoint |
| `/reset` | POST | Reset user session |
| `/health` | GET | Health check |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI API key | Required |
| `MONGODB_URI` | MongoDB connection string | Required |
| `MODEL_NAME` | Gemini model to use | `gemini-3-flash-preview` |
| `THINKING_LEVEL` | Thinking depth (LOW/MEDIUM/HIGH) | `LOW` |
| `MAX_FUNCTION_CALLS` | Max function calls per request | `30` |

## Project Structure

```
backend/
├── main.py                  # FastAPI app (thin controller)
├── config.py                # Configuration settings
├── app/
│   ├── core/                # v2.0 Unified Engine
│   │   ├── engine.py        # ConversationEngine
│   │   ├── function_loop.py # Multi-round FC
│   │   ├── response_buffer.py # Thread-safe accumulator
│   │   ├── thinking_manager.py # Thinking UI strategy
│   │   └── tool_executor.py # Explicit context
│   ├── adapters/            # External service wrappers
│   │   ├── gemini_adapter.py
│   │   └── mongo_adapter.py
│   ├── tools/               # Gemini function tools
│   ├── memory/              # MongoDB session storage
│   ├── reasoning/           # Query orchestration
│   └── catalog/             # Product catalog
├── tests/                   # 186+ unit tests
│   ├── core/                # Core component tests
│   └── integration/         # Integration tests
└── requirements.txt
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/core/test_response_buffer.py -v
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and design decisions
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment and Docker instructions
- [CONTEXT.md](./CONTEXT.md) - Full development history and bug fixes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/ -v`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

MIT License - see [LICENSE](./LICENSE) for details.

## See Also

- [Frontend Repository](https://github.com/Maqashable-284/scoop-ai-frontend)
- [Scoop.ge Website](https://scoop.ge)