# Sourcerer

AI-powered content aggregation and generation system that sources information from multiple channels and generates comprehensive content packages.

## Features

- **Multi-Provider LLM Support**: OpenAI, Anthropic, Moonshot, HuggingFace, and custom providers
- **Content Sources**: RSS feeds, HTML pages, and extensible source types
- **RAG System**: Vector-based retrieval for enhanced context
- **Content Generation**: Summaries, scripts, and images for multiple platforms
- **Secure Configuration**: Encrypted API key storage
- **Chat Interface**: Conversational interaction with persistent memory

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Run the application:**
   ```bash
   sourcerer
   ```

3. **First run setup:**
   - Configure at least one LLM provider
   - Optionally set up OpenAI for image generation
   - Add content sources

## Architecture

- **Backend**: FastAPI with async support
- **Frontend**: React with modern UI components
- **Storage**: Local file system with encryption
- **Vector Store**: FAISS for RAG functionality
- **Scheduling**: APScheduler for content ingestion

## Configuration

Configuration files are stored in `~/.sourcerer/`:
- `config/config.yaml` - Main configuration
- `config/config.enc` - Encrypted API keys
- `sources/sources.json` - Content sources
- `chats/` - Chat history
- `outputs/` - Generated content packages

## Development

1. **Install dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run tests:**
   ```bash
   pytest
   ```

3. **Format code:**
   ```bash
   black backend/ tests/
   ```

## API Documentation

Once running, access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License