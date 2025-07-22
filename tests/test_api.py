import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from backend.main import app


class TestAPI:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["data"]["status"] == "healthy"
    
    def test_first_run_check(self, client):
        """Test first run check endpoint"""
        with patch("backend.api.config.ConfigManager") as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.is_first_run = True
            
            response = client.get("/api/v1/config/first-run")
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["first_run"] == True
    
    def test_list_available_providers(self, client):
        """Test list available provider types"""
        response = client.get("/api/v1/providers/available")
        
        assert response.status_code == 200
        data = response.json()
        available_providers = data["data"]
        
        assert "openai" in available_providers
        assert "anthropic" in available_providers
        assert "custom" in available_providers
    
    def test_create_provider_validation(self, client):
        """Test provider creation validation"""
        # Test missing required fields
        response = client.post("/api/v1/providers", json={
            "type": "custom"
            # Missing name and api_key
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_config_endpoint_without_providers(self, client):
        """Test config endpoint with no providers"""
        with patch("backend.api.config.ConfigManager") as mock_config:
            mock_instance = mock_config.return_value
            mock_instance.config.model_dump.return_value = {
                "version": 1,
                "providers": {},
                "active_provider": None
            }
            
            response = client.get("/api/v1/config")
            
            assert response.status_code == 200
            data = response.json()
            assert "providers" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__])