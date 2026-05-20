"""Recruitment module configuration.

Loads recruitment module settings from environment variables with the RECRUITMENT_ prefix.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RecruitmentSettings(BaseSettings):
    """Recruitment module configuration loaded from environment variables.

    All environment variables are prefixed with ``RECRUITMENT_``. For example,
    ``llm_base_url`` maps to ``RECRUITMENT_LLM_BASE_URL``.

    Attributes:
        llm_base_url: Base URL for the LLM OpenAI-compatible API endpoint.
        llm_api_key: API key for LLM authentication (empty if not required).
        llm_model: Model name to use for LLM requests.
        llm_intent_timeout_seconds: Timeout for intent classification LLM calls.
        llm_parse_timeout_seconds: Timeout for CV parse LLM calls.
        llm_max_retries: Maximum retry attempts for failed LLM calls.
        olmocr_endpoint_url: URL for the olmOCR text extraction endpoint.
        olmocr_timeout_seconds: Timeout per olmOCR request (accommodates large PDFs).
        olmocr_max_retries: Maximum retry attempts for failed olmOCR calls.
        olmocr_max_pages_per_chunk: Maximum pages per PDF chunk sent to olmOCR.
        minio_bucket_name: MinIO bucket name for CV file storage.
        presigned_url_expiry_seconds: Expiry duration for MinIO presigned URLs.
        max_parallel_tasks: Maximum concurrent CV processing tasks.
        pipeline_timeout_seconds: Overall pipeline timeout for a single CV.
        max_file_size_bytes: Maximum allowed file size per attachment.
        retention_days: Days to retain rejected candidate data before deletion.
        auto_accept_threshold: Confidence score threshold for automatic candidate creation.
    """

    model_config = SettingsConfigDict(env_prefix="RECRUITMENT_")

    # LLM
    llm_base_url: str = "http://127.0.0.1:20128/v1"
    llm_api_key: str = ""
    llm_model: str = "NullNyx-Combo"
    llm_intent_timeout_seconds: int = Field(default=15, gt=0)
    llm_parse_timeout_seconds: int = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=3, ge=1)

    # olmOCR
    olmocr_endpoint_url: str = "https://olmocr.aibuddy.vn/ocr"
    olmocr_timeout_seconds: int = Field(default=600, gt=0)
    olmocr_max_retries: int = Field(default=3, ge=1)
    olmocr_max_pages_per_chunk: int = Field(default=20, ge=1)

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "recruitment-cv"
    presigned_url_expiry_seconds: int = Field(default=900, gt=0)  # 15 minutes

    # Processing
    max_parallel_tasks: int = Field(default=3, ge=1)
    pipeline_timeout_seconds: int = Field(default=660, gt=0)  # 11 minutes
    max_file_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)  # 10MB

    # Data retention
    retention_days: int = Field(default=90, ge=30, le=365)

    # Confidence threshold
    auto_accept_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
