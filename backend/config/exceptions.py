class ConfigError(Exception):
    """Base configuration error"""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation error"""
    pass


class ConfigEncryptionError(ConfigError):
    """Configuration encryption/decryption error"""
    pass


class ConfigMigrationError(ConfigError):
    """Configuration migration error"""
    pass


class ProviderNotFoundError(ConfigError):
    """Provider not found error"""
    pass


class InvalidProviderError(ConfigError):
    """Invalid provider configuration error"""
    pass