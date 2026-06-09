"""
Centralized Configuration
Uses pydantic-settings for validated environment variables.

A config.py file is not a Python requirement, but it is a very common pattern used 
to centralize application configuration.

Instead of scattering settings throughout the codebase, you keep them in one place.
"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# functools.lru_cache is used to cache the settings instance, ensuring that the configuration 
# is loaded only once and reused across the application.
from functools import lru_cache
import os

# Load .env into os.environ so LangChain/LangSmith SDK can read tracing config
# load_dotenv() is called in config.py to ensure that environment variables from 
# the .env file are loaded into os.environ before any settings are accessed. This 
# allows the application to read configuration values from the .env file, which 
# is especially useful for local development and testing.
load_dotenv()

# Define application settings using pydantic's BaseSettings
# This allows for type validation, default values, and easy loading from environment variables.  
# You can also add methods or properties to this class for derived settings or utility functions 
# related to configuration.
# print("****LangSmith Project from .env:", os.getenv("LANGSMITH_PROJECT"))
os.environ["LANGSMITH_PROJECT"] = "production-api"
print("****After LangSmith Project from .env:", os.getenv("LANGSMITH_PROJECT"))

class Settings(BaseSettings):
    
    # LLM Configuration
    openai_api_key: str
    primary_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-4.1-nano"
    
    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "production-api"
    langsmith_project: str = "production-api"
    
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    # Rate limit is for the purpose of demonstrating how to include such a setting. Implementing actual 
    # rate limiting logic would require additional code and is not shown here.
    rate_limit: str = "20/minute"   # Example: "20/minute", "100/hour", etc. This is for demonstration; implement actual rate limiting logic as needed.
    cache_ttl_seconds: int = 300    # Cache Time-To-Live in seconds for LLM responses
    max_retries: int = 3            # Maximum number of retries for failed LLM calls
    
    # Pydantic Settings Configuration 
    # The env_file option tells pydantic to load environment variables from a .env file, which is useful for 
    # local development.
    # The extra option set to "ignore" allows the application to ignore any additional environment variables 
    # that are not defined in the Settings class, preventing errors from unexpected variables.
    model_config = {"env_file": ".env", "extra": "ignore"}
    
    # Example of a derived property that checks if the application is running in production mode
    # This can be useful for conditional logic based on the environment, such as enabling debug logging 
    # or connecting to different databases.

    # derived properties like this can help keep your code clean and maintainable by centralizing environment 
    # checks in the settings class.
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
    
# The get_settings function is a common pattern for accessing the settings instance throughout the application.
# Using functools.lru_cache ensures that the settings are loaded only once and reused, improving performance.

# By calling get_settings() anywhere in your code, you can access the configuration settings without worrying about
# multiple instances or reloading the configuration. This promotes a clean and efficient way to manage application 
# settings.
@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()