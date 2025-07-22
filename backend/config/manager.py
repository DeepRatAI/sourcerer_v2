import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.config import ConfigModel, ProviderConfig, InferenceDefaults
from ..utils.security import load_master_key, encrypt_data, decrypt_data, save_master_key
from ..utils.file_utils import safe_write_yaml, safe_read_yaml, safe_write_json, create_backup
from ..utils.logging import get_logger
from .paths import get_config_dir, initialize_directories
from .exceptions import ConfigError, ConfigValidationError, ConfigEncryptionError


class ConfigManager:
    def __init__(self):
        self.logger = get_logger("sourcerer.config")
        self.config_dir = get_config_dir() / "config"
        self.config_file = self.config_dir / "config.yaml"
        self.encrypted_file = self.config_dir / "config.enc"
        self.master_key_file = self.config_dir / "master.key"
        
        self._config: Optional[ConfigModel] = None
        self._master_key: Optional[bytes] = None
        
        # Initialize directories
        initialize_directories()
        
    @property
    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return not self.config_file.exists()
    
    @property
    def config(self) -> ConfigModel:
        """Get current configuration"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    @property
    def master_key(self) -> bytes:
        """Get master encryption key"""
        if self._master_key is None:
            self._master_key = load_master_key(self.master_key_file)
        return self._master_key
    
    def _load_config(self) -> ConfigModel:
        """Load configuration from files"""
        if self.is_first_run:
            self.logger.info("First run detected, creating default configuration")
            return ConfigModel()
        
        try:
            config_data = safe_read_yaml(self.config_file)
            if not config_data:
                raise ConfigError("Failed to read configuration file")
            
            # Handle schema migrations
            config_data = self._migrate_config(config_data)
            
            return ConfigModel(**config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigError(f"Configuration load error: {e}")
    
    def _migrate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration to current schema version"""
        current_version = config_data.get("version", 1)
        target_version = 1
        
        if current_version < target_version:
            self.logger.info(f"Migrating config from v{current_version} to v{target_version}")
            # Create backup before migration
            create_backup(self.config_file, get_config_dir() / "backups")
            
            # Future migration logic would go here
            config_data["version"] = target_version
        
        return config_data
    
    def save_config(self) -> None:
        """Save configuration to files"""
        if self._config is None:
            raise ConfigError("No configuration to save")
        
        try:
            # Create backup if config exists
            if self.config_file.exists():
                create_backup(self.config_file, get_config_dir() / "backups")
            
            # Save main config (without sensitive data)
            config_dict = self._config.model_dump()
            self._clean_sensitive_data(config_dict)
            
            safe_write_yaml(config_dict, self.config_file)
            self.logger.info("Configuration saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise ConfigError(f"Configuration save error: {e}")
    
    def _clean_sensitive_data(self, config_dict: Dict[str, Any]) -> None:
        """Remove sensitive data from config dict before saving"""
        if "providers" in config_dict:
            for provider_id, provider_data in config_dict["providers"].items():
                if isinstance(provider_data, dict) and "api_key_enc" in provider_data:
                    # Keep encrypted key, remove any plain text keys
                    provider_data.pop("api_key", None)
        
        # Remove other sensitive fields
        config_dict.pop("master_password_hash", None)
    
    def add_provider(self, provider_id: str, provider_config: ProviderConfig) -> None:
        """Add a new provider"""
        if provider_id in self.config.providers:
            raise ConfigValidationError(f"Provider {provider_id} already exists")
        
        # Encrypt API key
        encrypted_key = self._encrypt_api_key(provider_config.api_key_enc)
        provider_config.api_key_enc = encrypted_key
        
        self.config.providers[provider_id] = provider_config
        
        # Set as active if it's the first provider
        if not self.config.active_provider:
            self.config.active_provider = provider_id
        
        self.save_config()
        self.logger.info(f"Added provider: {provider_id}")
    
    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> None:
        """Update existing provider"""
        if provider_id not in self.config.providers:
            raise ConfigValidationError(f"Provider {provider_id} not found")
        
        provider = self.config.providers[provider_id]
        
        # Handle API key encryption if updated
        if "api_key" in updates:
            updates["api_key_enc"] = self._encrypt_api_key(updates.pop("api_key"))
        
        # Update provider fields
        for key, value in updates.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        
        self.save_config()
        self.logger.info(f"Updated provider: {provider_id}")
    
    def remove_provider(self, provider_id: str) -> None:
        """Remove provider"""
        if provider_id not in self.config.providers:
            raise ConfigValidationError(f"Provider {provider_id} not found")
        
        del self.config.providers[provider_id]
        
        # Update active provider if necessary
        if self.config.active_provider == provider_id:
            remaining_providers = list(self.config.providers.keys())
            self.config.active_provider = remaining_providers[0] if remaining_providers else None
            self.config.active_model = None
        
        self.save_config()
        self.logger.info(f"Removed provider: {provider_id}")
    
    def get_provider_api_key(self, provider_id: str) -> str:
        """Get decrypted API key for provider"""
        if provider_id not in self.config.providers:
            raise ConfigValidationError(f"Provider {provider_id} not found")
        
        encrypted_key = self.config.providers[provider_id].api_key_enc
        return self._decrypt_api_key(encrypted_key)
    
    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key"""
        try:
            return encrypt_data(api_key, self.master_key)
        except Exception as e:
            raise ConfigEncryptionError(f"Failed to encrypt API key: {e}")
    
    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key"""
        try:
            return decrypt_data(encrypted_key, self.master_key)
        except Exception as e:
            raise ConfigEncryptionError(f"Failed to decrypt API key: {e}")
    
    def set_active_provider(self, provider_id: str, model_id: Optional[str] = None) -> None:
        """Set active provider and model"""
        if provider_id not in self.config.providers:
            raise ConfigValidationError(f"Provider {provider_id} not found")
        
        self.config.active_provider = provider_id
        self.config.active_model = model_id
        self.save_config()
        self.logger.info(f"Set active provider: {provider_id}, model: {model_id}")
    
    def update_inference_defaults(self, updates: Dict[str, Any]) -> None:
        """Update inference default parameters"""
        for key, value in updates.items():
            if hasattr(self.config.inference_defaults, key):
                setattr(self.config.inference_defaults, key, value)
        
        self.save_config()
        self.logger.info("Updated inference defaults")
    
    def enable_image_generation(self, enabled: bool = True) -> None:
        """Enable/disable image generation"""
        self.config.image_generation.enabled = enabled
        self.save_config()
        self.logger.info(f"Image generation enabled: {enabled}")
    
    def export_config(self, include_keys: bool = False, passphrase: Optional[str] = None) -> Dict[str, Any]:
        """Export configuration"""
        config_dict = self.config.model_dump()
        
        if not include_keys:
            # Remove all sensitive data
            self._clean_sensitive_data(config_dict)
        elif passphrase:
            # Encrypt sensitive data with passphrase
            # This would require additional encryption logic
            pass
        
        return {
            "schema_version": 1,
            "exported_at": datetime.now().isoformat(),
            "config": config_dict
        }
    
    def import_config(self, import_data: Dict[str, Any], overwrite: bool = False) -> None:
        """Import configuration"""
        if "config" not in import_data:
            raise ConfigValidationError("Invalid import data format")
        
        imported_config = ConfigModel(**import_data["config"])
        
        if overwrite:
            self._config = imported_config
        else:
            # Merge configurations (implement merge logic as needed)
            pass
        
        self.save_config()
        self.logger.info("Configuration imported successfully")
    
    def get_provider_status(self, provider_id: str) -> Dict[str, Any]:
        """Get provider status information"""
        if provider_id not in self.config.providers:
            return {"status": "not_found"}
        
        provider = self.config.providers[provider_id]
        return {
            "status": "ok",  # This would be determined by connectivity tests
            "type": provider.type,
            "alias": provider.alias or provider_id,
            "model_count": len(provider.models_cache.ids) if provider.models_cache else 0,
            "last_updated": provider.models_cache.fetched_at.isoformat() if provider.models_cache else None
        }
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any errors"""
        errors = []
        
        if not self.config.providers:
            errors.append("No providers configured")
        
        if self.config.active_provider and self.config.active_provider not in self.config.providers:
            errors.append(f"Active provider '{self.config.active_provider}' not found")
        
        # Validate each provider
        for provider_id, provider in self.config.providers.items():
            try:
                self._decrypt_api_key(provider.api_key_enc)
            except Exception:
                errors.append(f"Failed to decrypt API key for provider '{provider_id}'")
        
        return errors