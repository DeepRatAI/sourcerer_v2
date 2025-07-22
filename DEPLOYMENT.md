# Sourcerer Deployment Guide

## Quick Start

1. **Install Python dependencies:**
   ```bash
   pip install -e .
   ```

2. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Run the application:**
   ```bash
   # Option 1: Full production mode (builds frontend + runs backend)
   python run.py full
   
   # Option 2: Development mode (separate terminals)
   python run.py backend --reload &
   python run.py frontend
   ```

4. **Access the application:**
   - Open your browser to `http://localhost:8000`
   - Follow the onboarding flow to configure your first LLM provider

## Development

### Backend Development
```bash
# Run backend with auto-reload
python run.py backend --reload --debug

# Run tests
python run.py test

# Run diagnostics
python run.py doctor
```

### Frontend Development
```bash
# Run frontend dev server (with hot reload)
python run.py frontend

# Build frontend for production
python run.py build
```

## Configuration

### First Run
On first startup, Sourcerer will guide you through:
1. Configuring at least one LLM provider (OpenAI, Anthropic, Moonshot, HuggingFace, or Custom)
2. Optionally setting up image generation (requires OpenAI)
3. Basic system configuration

### Data Directory
Sourcerer stores all data in `~/.sourcerer/`:
```
~/.sourcerer/
├── config/
│   ├── config.yaml       # Main configuration
│   ├── config.enc        # Encrypted API keys
│   └── master.key        # Encryption key
├── chats/                # Chat sessions
├── sources/              # Content sources
├── memory/               # RAG vector store
├── logs/                 # Application logs
├── cache/                # Temporary files
├── outputs/              # Generated content
└── backups/              # Configuration backups
```

## Supported Providers

### Built-in Providers
- **OpenAI**: GPT-4, GPT-3.5-turbo, etc.
- **Anthropic**: Claude 3 Opus, Sonnet, Haiku
- **Moonshot**: Moonshot v1 models
- **HuggingFace**: Inference API models

### Custom Providers
Configure any OpenAI-compatible API endpoint with:
- Custom base URL
- Authentication headers
- Model discovery endpoints
- Payload schemas (OpenAI Chat, HuggingFace Text, Raw JSON)

## Production Deployment

### Environment Setup
```bash
# Create production environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .

# Build frontend
python run.py build

# Run in production mode
python run.py backend --host 0.0.0.0 --port 8000
```

### Docker (Optional)
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install -e .
RUN cd frontend && npm install && npm run build

EXPOSE 8000
CMD ["python", "run.py", "backend", "--host", "0.0.0.0"]
```

### Reverse Proxy
Example nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Security

- API keys are encrypted using Fernet (AES 128)
- Master encryption key stored with 600 permissions
- All sensitive files have restricted permissions
- No API keys are logged or transmitted in plain text
- Optional master password for additional security

## Monitoring

### Logs
- Application logs: `~/.sourcerer/logs/app.log`
- Inference logs: `~/.sourcerer/logs/inference.log`
- Content generation: `~/.sourcerer/logs/content_generation.log`
- Security events: `~/.sourcerer/logs/security.log`

### Diagnostics
```bash
python run.py doctor
```

## Troubleshooting

### Common Issues

1. **Backend won't start:**
   - Check Python version (3.10+ required)
   - Verify all dependencies installed: `pip install -e .`
   - Check logs in `~/.sourcerer/logs/`

2. **Frontend build fails:**
   - Ensure Node.js 16+ installed
   - Delete `node_modules` and run `npm install` again
   - Check for disk space

3. **Provider authentication fails:**
   - Verify API key is correct and active
   - Check provider-specific base URLs
   - Test with provider's official tools first

4. **Configuration corruption:**
   - Check `~/.sourcerer/backups/` for recent backups
   - Delete `~/.sourcerer/config/` to reset (will trigger first-run)
   - Use `python run.py doctor` to diagnose

### Performance

- Backend handles concurrent requests via FastAPI/uvicorn
- Frontend serves static files in production
- Large files cached appropriately
- Background tasks scheduled for optimal performance

### Backup & Recovery

Configuration is automatically backed up before changes:
```bash
# Manual backup
cp -r ~/.sourcerer ~/.sourcerer.backup

# Restore from backup
rm -rf ~/.sourcerer
cp -r ~/.sourcerer.backup ~/.sourcerer
```

## API Documentation

Once running, access API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For issues and questions:
1. Check logs in `~/.sourcerer/logs/`
2. Run diagnostics: `python run.py doctor`
3. Review this documentation
4. Check GitHub issues (if applicable)