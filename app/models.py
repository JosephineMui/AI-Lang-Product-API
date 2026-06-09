"""
API Request and Response Models
Pydantic models for input validation and response structure.

models.py usually contains the definitions of the application's core data structures or domain objects. 
In the context of a web application, this often includes request and response models that define the 
expected structure of incoming data and outgoing responses. These models help ensure that the data 
your application processes is well-structured and validated, making it easier to maintain and debug.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str = Field(
        # Ellipsis indicates that this field is required, so requests without a message will be rejected with 
        # a validation error.
        ...,                    
        min_length=1,           # Minimum length of 1 character to prevent empty messages
        max_length=10000,       # Maximum length to prevent excessively long inputs that could cause performance issues
        description="The user's message to the agent",
    )
    thread_id: str = Field(
        default="default",
        description="Conversation thread ID",
    )   


class ChatResponse(BaseModel):
    """Chat response returned to the client."""

    response: str                # The agent's response to the user's message
    thread_id: str               # The conversation thread ID
    model_used: str              # The model used to generate the response
    cached: bool = False         # Indicates if the response was retrieved from cache
    processing_time_ms: float    # Time taken to process the request in milliseconds
    # default_factory is used to set the default value of security_notes to an empty list. 
    # This allows you to avoid mutable default arguments, which can lead to unexpected behavior.
    security_notes: list[str] = Field(default_factory=list)  # Security-related notes
    # Timestamp of when the response was generated, in ISO 8601 format. Using a default 
    # factory to set it to the current time when the model is instantiated.
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy" # Default to "healthy", but can be set to "unhealthy" if checks fail
    environment: str        # The application environment (e.g., development, staging, production)
    version: str = "1.1.0"  # Application version, can be set from environment variable or hardcoded
    checks: dict = {}       # A dictionary to hold the results of various health checks (e.g., database connectivity, LLM availability).


class MetricsResponse(BaseModel):
    """Metrics endpoint response."""

    total_requests: int         # Total number of requests received by the API
    total_errors: int           # Total number of errors encountered while processing requests
    error_rate: str             # Error rate as a percentage
    avg_latency_ms: float       # Average latency in milliseconds
    cache_hit_rate: str         # Cache hit rate as a percentage
    total_input_tokens: int     # Total number of input tokens processed
    total_output_tokens: int    # Total number of output tokens generated


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str                      # A brief error message describing what went wrong

    # This field can either be a string or None. If detail is not provided, it will default to None. 
    # This allows you to include additional error information when available, such as stack traces or 
    # validation errors, without making it mandatory for every error response.
    detail: str | None = None       # Optional detailed error information, such as stack traces or validation errors
    
    # This field can either be a string or None. If request_id is not provided, it will default to None.
    # This allows you to include a request ID for tracing errors in logs when available, without making it 
    # mandatory for every error response.
    request_id: str | None = None   # Optional request ID for tracing errors in logs
