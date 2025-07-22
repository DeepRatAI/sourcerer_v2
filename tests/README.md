# Sourcerer Testing Suite

This directory contains the comprehensive testing suite for Sourcerer, including unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── run_tests.py               # Test runner script (in parent directory)
├── e2e/                       # End-to-end tests
│   ├── test_sources_workflow.py
│   ├── test_content_generation_workflow.py
│   ├── test_chat_workflow.py
│   └── test_system_integration.py
├── integration/               # Integration tests
└── unit/                      # Unit tests
```

## Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.py all

# Run only end-to-end tests
./run_tests.py e2e

# Run with verbose output
./run_tests.py all -v

# Run specific test file
./run_tests.py e2e -t tests/e2e/test_sources_workflow.py
```

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup:**
   The test runner automatically sets up test environment variables:
   - `SOURCERER_ENV=test`
   - `SOURCERER_DATA_DIR=./test_data`
   - `SOURCERER_LOGS_DIR=./test_logs`

### Test Server Management

The test runner automatically:
- Starts a test server on `localhost:8000`
- Waits for server to be ready
- Runs the tests
- Stops the server and cleans up

**Manual Server Control:**
```bash
# Skip server startup (use existing server)
./run_tests.py e2e --no-server

# Keep server running after tests
./run_tests.py e2e --keep-server

# Clean up test environment
./run_tests.py --cleanup
```

## Test Categories

### End-to-End Tests (`tests/e2e/`)

These tests verify complete user workflows across the entire system:

#### `test_sources_workflow.py`
- Complete source management lifecycle
- RSS and HTML source creation, configuration, and deletion
- Source ingestion and content parsing
- Scheduler integration
- Bulk operations
- Error handling and recovery

#### `test_content_generation_workflow.py`
- RAG system integration
- Content generation pipeline (summaries, scripts, images)
- Research engine functionality
- Package management and statistics
- Concurrent generation handling

#### `test_chat_workflow.py`
- Chat session lifecycle
- Message persistence with JSONL
- Conversation truncation
- RAG context integration
- Session management and archiving

#### `test_system_integration.py`
- Complete system workflow from source to chat
- Performance benchmarks
- Error resilience testing
- Data consistency verification
- Load testing

### Integration Tests (`tests/integration/`)

Tests for component integration (to be expanded):
- API endpoint integration
- Database integration
- External service integration

### Unit Tests (`tests/unit/`)

Tests for individual components (to be expanded):
- Model validation
- Utility functions
- Business logic

## Test Configuration

### Pytest Configuration (`pytest.ini`)

Key settings:
- **Coverage:** Minimum 70% code coverage required
- **Timeout:** 300 seconds max per test
- **Markers:** Tests categorized by type and requirements
- **Logging:** Comprehensive test logging enabled

### Test Markers

Tests are automatically marked based on their characteristics:

```python
@pytest.mark.e2e              # End-to-end tests
@pytest.mark.integration      # Integration tests
@pytest.mark.unit            # Unit tests
@pytest.mark.slow            # Slow-running tests
@pytest.mark.requires_llm    # Needs LLM provider configuration
@pytest.mark.requires_network # Needs internet access
```

**Running by markers:**
```bash
pytest -m "e2e and not slow"
pytest -m "unit"
pytest -m "not requires_network"
```

## Test Environment

### Isolated Test Data

Tests run in an isolated environment:
- Separate data directory (`test_data/`)
- Separate log directory (`test_logs/`)
- Test-specific configuration
- Automatic cleanup after tests

### Mock and Test Data

Tests handle various scenarios:
- **Real API calls:** For true end-to-end validation
- **Graceful degradation:** When LLM providers aren't configured
- **Error simulation:** Testing with invalid URLs and bad data
- **Concurrent operations:** Multi-threaded test scenarios

## Writing New Tests

### End-to-End Test Template

```python
import pytest
import httpx

class TestNewWorkflow:
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)
    
    def test_complete_workflow(self, client):
        """Test complete workflow"""
        
        # Step 1: Setup
        setup_data = {"key": "value"}
        response = client.post("/api/endpoint", json=setup_data)
        assert response.status_code == 200
        
        # Step 2: Main operation
        # ... test logic ...
        
        # Step 3: Verification
        # ... verification logic ...
        
        # Step 4: Cleanup
        # ... cleanup logic ...
```

### Test Best Practices

1. **Isolation:** Each test should be independent
2. **Cleanup:** Always clean up test data
3. **Assertions:** Use descriptive assertion messages
4. **Timeouts:** Handle async operations with appropriate timeouts
5. **Error Handling:** Test both success and failure scenarios

### Test Data Management

```python
def setup_test_data(self, client):
    """Helper to create test data"""
    # Create test resources
    response = client.post("/api/resource", json=test_data)
    return response.json()["data"]["id"]

def cleanup_test_data(self, client, resource_id):
    """Helper to clean up test data"""
    try:
        client.delete(f"/api/resource/{resource_id}")
    except:
        pass  # Ignore cleanup errors
```

## Troubleshooting

### Common Issues

1. **Server Start Failure:**
   ```bash
   # Check if port 8000 is already in use
   lsof -i :8000
   
   # Kill existing process
   kill -9 <PID>
   ```

2. **Test Timeouts:**
   - Check server logs for slow operations
   - Increase timeout in pytest.ini if needed
   - Use `--no-server` if server is slow to start

3. **Network-Dependent Test Failures:**
   ```bash
   # Skip network tests
   pytest -m "not requires_network"
   ```

4. **LLM Provider Errors:**
   - Tests gracefully handle missing LLM configuration
   - Configure providers in test environment if needed
   - Use `--no-server` and mock responses for pure unit tests

### Debug Mode

```bash
# Run with maximum verbosity
./run_tests.py all -v

# Run single test with pytest directly
pytest tests/e2e/test_sources_workflow.py::TestSourcesWorkflow::test_complete_sources_workflow -v -s

# Keep server running for debugging
./run_tests.py e2e --keep-server
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Continuous Integration

These tests are designed to work in CI/CD environments:

- **Automatic server management:** No manual setup required
- **Environment isolation:** Tests don't interfere with each other
- **Comprehensive coverage:** All major workflows tested
- **Performance monitoring:** Built-in benchmarking
- **Error resilience:** Tests system recovery capabilities

### CI Configuration Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: ./run_tests.py all
```

## Contributing

When adding new features:

1. **Add corresponding tests** to appropriate test files
2. **Update test documentation** if introducing new patterns
3. **Ensure tests pass** before submitting changes
4. **Maintain coverage** above minimum threshold

For questions or issues with testing, please refer to the main project documentation or open an issue.