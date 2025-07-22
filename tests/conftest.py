import pytest
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ["SOURCERER_ENV"] = "test"
os.environ["SOURCERER_DATA_DIR"] = str(project_root / "test_data")
os.environ["SOURCERER_LOGS_DIR"] = str(project_root / "test_logs")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config():
    """Test configuration fixture"""
    return {
        "test_mode": True,
        "log_level": "DEBUG",
        "test_data_dir": os.environ["SOURCERER_DATA_DIR"]
    }

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test items to add markers based on path"""
    for item in items:
        # Add markers based on test file location
        if "e2e" in item.fspath.basename:
            item.add_marker(pytest.mark.e2e)
        elif "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        elif "test_" in item.fspath.basename:
            item.add_marker(pytest.mark.unit)
        
        # Mark potentially slow tests
        if any(keyword in item.name.lower() for keyword in ["workflow", "complete", "system"]):
            item.add_marker(pytest.mark.slow)

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test"""
    # Ensure test directories exist
    test_data_dir = Path(os.environ["SOURCERER_DATA_DIR"])
    test_logs_dir = Path(os.environ["SOURCERER_LOGS_DIR"])
    
    test_data_dir.mkdir(parents=True, exist_ok=True)
    test_logs_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup can be added here if needed

@pytest.fixture
def cleanup_test_data():
    """Fixture to clean up test data after test completion"""
    yield
    
    # Clean up test data directory
    import shutil
    test_data_dir = Path(os.environ["SOURCERER_DATA_DIR"])
    if test_data_dir.exists():
        try:
            shutil.rmtree(test_data_dir)
        except:
            pass  # Ignore cleanup errors in tests