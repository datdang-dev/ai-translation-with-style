"""Provider configuration models"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, SecretStr


class ProviderType(str, Enum):
    """Types of translation providers"""
    OPENROUTER = "openrouter"
    OPENAI = "openai" 
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE_TRANSLATE = "google_translate"
    CUSTOM = "custom"


class AuthenticationType(str, Enum):
    """Authentication methods for providers"""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    SERVICE_ACCOUNT = "service_account"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a provider"""
    
    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    requests_per_hour: Optional[int] = Field(default=None, ge=1)
    requests_per_day: Optional[int] = Field(default=None, ge=1)
    
    # Token-based limits
    tokens_per_minute: Optional[int] = Field(default=None, ge=1)
    tokens_per_hour: Optional[int] = Field(default=None, ge=1)
    tokens_per_day: Optional[int] = Field(default=None, ge=1)
    
    # Burst allowance
    burst_limit: Optional[int] = Field(default=None, ge=1)
    
    # Backoff settings
    backoff_base: float = Field(default=2.0, ge=1.0, le=10.0)
    max_backoff_seconds: int = Field(default=300, ge=1, le=3600)


class RetryConfig(BaseModel):
    """Retry configuration for failed requests"""
    
    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    exponential_base: float = Field(default=2.0, ge=1.0, le=10.0)
    jitter: bool = Field(default=True, description="Add random jitter to delays")
    
    # Which errors to retry
    retry_on_timeout: bool = Field(default=True)
    retry_on_rate_limit: bool = Field(default=True)
    retry_on_network_error: bool = Field(default=True)
    retry_on_server_error: bool = Field(default=True)  # 5xx errors


class ModelConfig(BaseModel):
    """Configuration for a specific model within a provider"""
    
    name: str = Field(..., description="Model identifier")
    display_name: Optional[str] = Field(default=None)
    
    # Model capabilities
    max_input_tokens: Optional[int] = Field(default=None, ge=1)
    max_output_tokens: Optional[int] = Field(default=None, ge=1)
    supports_streaming: bool = Field(default=False)
    
    # Cost information (per 1K tokens)
    input_cost_per_1k_tokens: Optional[float] = Field(default=None, ge=0.0)
    output_cost_per_1k_tokens: Optional[float] = Field(default=None, ge=0.0)
    
    # Model-specific parameters
    default_temperature: Optional[float] = Field(default=0.3, ge=0.0, le=2.0)
    default_top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    
    # Quality and performance hints
    quality_tier: str = Field(default="standard", regex="^(basic|standard|premium)$")
    response_time_tier: str = Field(default="standard", regex="^(fast|standard|slow)$")


class ProviderConfig(BaseModel):
    """
    Complete configuration for a translation provider.
    
    This includes authentication, rate limits, retry policies, and available models.
    """
    
    # Basic provider information
    name: str = Field(..., description="Unique provider name")
    type: ProviderType
    display_name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    
    # Connection settings
    base_url: str = Field(..., description="Provider API base URL")
    api_version: Optional[str] = Field(default=None)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    
    # Authentication
    auth_type: AuthenticationType = Field(default=AuthenticationType.API_KEY)
    api_keys: List[SecretStr] = Field(default_factory=list, min_items=0)
    
    # Additional auth parameters (for OAuth2, service accounts, etc.)
    auth_params: Dict[str, Any] = Field(default_factory=dict)
    
    # Rate limiting and retry policies
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    retry_config: RetryConfig = Field(default_factory=RetryConfig)
    
    # Available models
    models: List[ModelConfig] = Field(default_factory=list)
    default_model: Optional[str] = Field(default=None)
    
    # Provider-specific settings
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    custom_params: Dict[str, Any] = Field(default_factory=dict)
    
    # Feature flags
    enabled: bool = Field(default=True)
    supports_batch: bool = Field(default=False)
    supports_streaming: bool = Field(default=False)
    
    # Priority and selection
    priority: int = Field(default=5, ge=1, le=10, description="Provider priority (1=highest)")
    health_check_url: Optional[str] = Field(default=None)
    
    @validator('api_keys')
    def validate_api_keys(cls, v, values):
        """Validate that API keys are provided when using API key auth"""
        auth_type = values.get('auth_type')
        if auth_type == AuthenticationType.API_KEY and not v:
            raise ValueError("API keys are required when using API key authentication")
        return v
    
    @validator('default_model')
    def validate_default_model(cls, v, values):
        """Validate that default model exists in models list"""
        if v is not None:
            models = values.get('models', [])
            model_names = [m.name for m in models]
            if v not in model_names:
                raise ValueError(f"Default model '{v}' not found in available models")
        return v
    
    def get_model(self, model_name: Optional[str] = None) -> Optional[ModelConfig]:
        """Get a specific model configuration"""
        target_model = model_name or self.default_model
        if not target_model:
            return None
        
        for model in self.models:
            if model.name == target_model:
                return model
        return None
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names"""
        return [model.name for model in self.models]
    
    def is_healthy(self) -> bool:
        """Check if provider is enabled and has valid configuration"""
        return (
            self.enabled 
            and (not self.api_keys or len(self.api_keys) > 0)
            and len(self.models) > 0
        )
    
    def __str__(self) -> str:
        status = "✅" if self.is_healthy() else "❌"
        model_count = len(self.models)
        key_count = len(self.api_keys) if self.api_keys else 0
        return f"{status} {self.name} ({self.type}, {model_count} models, {key_count} keys)"


class ProvidersConfig(BaseModel):
    """
    Configuration for all translation providers.
    """
    
    providers: List[ProviderConfig] = Field(default_factory=list)
    default_provider: Optional[str] = Field(default=None)
    
    # Global fallback settings
    enable_fallback: bool = Field(default=True)
    fallback_order: List[str] = Field(default_factory=list)
    
    @validator('default_provider')
    def validate_default_provider(cls, v, values):
        """Validate that default provider exists"""
        if v is not None:
            providers = values.get('providers', [])
            provider_names = [p.name for p in providers]
            if v not in provider_names:
                raise ValueError(f"Default provider '{v}' not found in available providers")
        return v
    
    @validator('fallback_order')
    def validate_fallback_order(cls, v, values):
        """Validate that all providers in fallback order exist"""
        providers = values.get('providers', [])
        provider_names = [p.name for p in providers]
        
        for provider_name in v:
            if provider_name not in provider_names:
                raise ValueError(f"Fallback provider '{provider_name}' not found in available providers")
        return v
    
    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get a specific provider configuration"""
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None
    
    def get_healthy_providers(self) -> List[ProviderConfig]:
        """Get all healthy providers"""
        return [p for p in self.providers if p.is_healthy()]
    
    def get_fallback_providers(self, exclude: Optional[str] = None) -> List[ProviderConfig]:
        """Get providers in fallback order, optionally excluding one"""
        if not self.enable_fallback:
            return []
        
        fallback_providers = []
        for provider_name in self.fallback_order:
            if exclude and provider_name == exclude:
                continue
            provider = self.get_provider(provider_name)
            if provider and provider.is_healthy():
                fallback_providers.append(provider)
        
        return fallback_providers
    
    def __len__(self) -> int:
        return len(self.providers)
    
    def __str__(self) -> str:
        healthy_count = len(self.get_healthy_providers())
        total_count = len(self.providers)
        return f"ProvidersConfig({healthy_count}/{total_count} healthy providers)"