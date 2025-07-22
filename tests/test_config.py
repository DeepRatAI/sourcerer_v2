import pytest
import tempfile
import os
from pathlib import Path

from backend.config.manager import ConfigManager
from backend.models.config import ConfigModel, ProviderConfig


class TestConfigManager:
    
    def test_first_run_detection(self):
        """Test first run detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock config directory
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir) / "config"
            config_manager.config_file = config_manager.config_dir / "config.yaml"
            
            # Should be first run
            assert config_manager.is_first_run == True
            
            # Create config file
            config_manager.config_dir.mkdir(parents=True)
            config_manager.config_file.touch()
            
            # Should no longer be first run
            assert config_manager.is_first_run == False
    
    def test_config_validation(self):
        """Test configuration validation"""
        config_manager = ConfigManager()
        config_manager._config = ConfigModel()
        
        # Empty config should have validation errors
        errors = config_manager.validate_config()
        assert "No providers configured" in errors
    
    def test_provider_operations(self):
        """Test provider CRUD operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.config_dir = Path(temp_dir) / "config"
            config_manager.config_file = config_manager.config_dir / "config.yaml"
            config_manager.master_key_file = config_manager.config_dir / "master.key"
            config_manager._config = ConfigModel()
            
            # Test add provider
            provider_config = ProviderConfig(
                type="built_in",
                api_key_enc="test-key",
                base_url="https://api.openai.com/v1"
            )
            
            config_manager.add_provider("openai", provider_config)
            
            assert "openai" in config_manager.config.providers
            assert config_manager.config.active_provider == "openai"
    
    def test_encryption_decryption(self):
        """Test API key encryption/decryption"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager()
            config_manager.master_key_file = Path(temp_dir) / "master.key"
            
            # Test encryption/decryption
            original_key = "sk-test123456789"
            encrypted = config_manager._encrypt_api_key(original_key)
            decrypted = config_manager._decrypt_api_key(encrypted)
            
            assert decrypted == original_key
            assert encrypted != original_key


if __name__ == "__main__":
    pytest.main([__file__])