"""Tests for the Recruitment API error handler."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.modules.recruitment.api.error_handler import (
    register_recruitment_error_handlers,
)
from src.modules.recruitment.application.candidate_service import (
    CandidateValidationError,
)
from src.modules.recruitment.application.review_service import (
    ReviewValidationError,
)
from src.modules.recruitment.domain.exceptions import (
    CandidateNotFoundError,
    CVDocumentNotFoundError,
    CVFileNotFoundError,
    GmailNotConnectedError,
    InvalidStatusTransitionError,
    LLMParseError,
    OCRExtractionError,
    PipelineTimeoutError,
    RecruitmentError,
    StorageServiceUnavailableError,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with recruitment error handlers registered."""
    app = FastAPI()
    register_recruitment_error_handlers(app)
    return app


@pytest.fixture
def app_with_routes(app: FastAPI) -> FastAPI:
    """Add test routes that raise each exception type."""

    @app.get("/test/candidate-not-found")
    async def raise_candidate_not_found():
        raise CandidateNotFoundError()

    @app.get("/test/cv-document-not-found")
    async def raise_cv_document_not_found():
        raise CVDocumentNotFoundError()

    @app.get("/test/invalid-status-transition")
    async def raise_invalid_status_transition():
        raise InvalidStatusTransitionError(
            current_status="rejected", attempted_action="accept"
        )

    @app.get("/test/cv-file-not-found")
    async def raise_cv_file_not_found():
        raise CVFileNotFoundError()

    @app.get("/test/storage-unavailable")
    async def raise_storage_unavailable():
        raise StorageServiceUnavailableError()

    @app.get("/test/gmail-not-connected")
    async def raise_gmail_not_connected():
        raise GmailNotConnectedError()

    @app.get("/test/pipeline-timeout")
    async def raise_pipeline_timeout():
        raise PipelineTimeoutError()

    @app.get("/test/ocr-extraction-error")
    async def raise_ocr_extraction_error():
        raise OCRExtractionError()

    @app.get("/test/llm-parse-error")
    async def raise_llm_parse_error():
        raise LLMParseError()

    @app.get("/test/base-error")
    async def raise_base_error():
        raise RecruitmentError("Something went wrong")

    @app.get("/test/candidate-validation-error")
    async def raise_candidate_validation_error():
        raise CandidateValidationError(
            [{"field": "email", "reason": "Invalid email format"}]
        )

    @app.get("/test/review-validation-error")
    async def raise_review_validation_error():
        raise ReviewValidationError(
            [{"field": "name", "reason": "Name is required"}]
        )

    @app.get("/test/value-error")
    async def raise_value_error():
        raise ValueError("Invalid page number")

    @app.get("/test/custom-message")
    async def raise_custom_message():
        raise CandidateNotFoundError("Candidate abc123 not found")

    return app


@pytest.fixture
async def client(app_with_routes: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app_with_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCandidateNotFoundError:
    @pytest.mark.anyio
    async def test_returns_404(self, client: AsyncClient):
        response = await client.get("/test/candidate-not-found")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/candidate-not-found")
        data = response.json()
        assert data["error_code"] == "CANDIDATE_NOT_FOUND"
        assert data["message"] == "Candidate not found"


class TestCVDocumentNotFoundError:
    @pytest.mark.anyio
    async def test_returns_404(self, client: AsyncClient):
        response = await client.get("/test/cv-document-not-found")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/cv-document-not-found")
        data = response.json()
        assert data["error_code"] == "CV_DOCUMENT_NOT_FOUND"
        assert data["message"] == "CV document not found"


class TestInvalidStatusTransitionError:
    @pytest.mark.anyio
    async def test_returns_409(self, client: AsyncClient):
        response = await client.get("/test/invalid-status-transition")
        assert response.status_code == 409

    @pytest.mark.anyio
    async def test_returns_error_code_and_message(self, client: AsyncClient):
        response = await client.get("/test/invalid-status-transition")
        data = response.json()
        assert data["error_code"] == "INVALID_STATUS_TRANSITION"
        assert "rejected" in data["message"]
        assert "accept" in data["message"]


class TestCVFileNotFoundError:
    @pytest.mark.anyio
    async def test_returns_404(self, client: AsyncClient):
        response = await client.get("/test/cv-file-not-found")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/cv-file-not-found")
        data = response.json()
        assert data["error_code"] == "CV_FILE_MISSING"


class TestStorageServiceUnavailableError:
    @pytest.mark.anyio
    async def test_returns_502(self, client: AsyncClient):
        response = await client.get("/test/storage-unavailable")
        assert response.status_code == 502

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/storage-unavailable")
        data = response.json()
        assert data["error_code"] == "STORAGE_SERVICE_UNAVAILABLE"


class TestGmailNotConnectedError:
    @pytest.mark.anyio
    async def test_returns_409(self, client: AsyncClient):
        response = await client.get("/test/gmail-not-connected")
        assert response.status_code == 409

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/gmail-not-connected")
        data = response.json()
        assert data["error_code"] == "GMAIL_NOT_CONNECTED"


class TestPipelineTimeoutError:
    @pytest.mark.anyio
    async def test_returns_504(self, client: AsyncClient):
        response = await client.get("/test/pipeline-timeout")
        assert response.status_code == 504

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/pipeline-timeout")
        data = response.json()
        assert data["error_code"] == "PIPELINE_TIMEOUT"


class TestOCRExtractionError:
    @pytest.mark.anyio
    async def test_returns_502(self, client: AsyncClient):
        response = await client.get("/test/ocr-extraction-error")
        assert response.status_code == 502

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/ocr-extraction-error")
        data = response.json()
        assert data["error_code"] == "OCR_EXTRACTION_FAILED"


class TestLLMParseError:
    @pytest.mark.anyio
    async def test_returns_502(self, client: AsyncClient):
        response = await client.get("/test/llm-parse-error")
        assert response.status_code == 502

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/llm-parse-error")
        data = response.json()
        assert data["error_code"] == "LLM_PARSE_FAILED"


class TestBaseRecruitmentError:
    @pytest.mark.anyio
    async def test_returns_500(self, client: AsyncClient):
        response = await client.get("/test/base-error")
        assert response.status_code == 500

    @pytest.mark.anyio
    async def test_returns_error_code(self, client: AsyncClient):
        response = await client.get("/test/base-error")
        data = response.json()
        assert data["error_code"] == "RECRUITMENT_ERROR"
        assert data["message"] == "Something went wrong"


class TestCandidateValidationError:
    @pytest.mark.anyio
    async def test_returns_422(self, client: AsyncClient):
        response = await client.get("/test/candidate-validation-error")
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_returns_error_code_and_details(self, client: AsyncClient):
        response = await client.get("/test/candidate-validation-error")
        data = response.json()
        assert data["error_code"] == "CANDIDATE_VALIDATION_ERROR"
        assert data["message"] == "Candidate validation failed"
        assert data["details"] == {
            "errors": [{"field": "email", "reason": "Invalid email format"}]
        }


class TestReviewValidationError:
    @pytest.mark.anyio
    async def test_returns_422(self, client: AsyncClient):
        response = await client.get("/test/review-validation-error")
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_returns_error_code_and_details(self, client: AsyncClient):
        response = await client.get("/test/review-validation-error")
        data = response.json()
        assert data["error_code"] == "REVIEW_VALIDATION_ERROR"
        assert data["message"] == "Review validation failed"
        assert data["details"] == {
            "errors": [{"field": "name", "reason": "Name is required"}]
        }


class TestValueError:
    @pytest.mark.anyio
    async def test_returns_422(self, client: AsyncClient):
        response = await client.get("/test/value-error")
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_returns_error_code_and_message(self, client: AsyncClient):
        response = await client.get("/test/value-error")
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["message"] == "Invalid page number"
        assert data["details"] is None


class TestCustomMessage:
    @pytest.mark.anyio
    async def test_custom_message_in_response(self, client: AsyncClient):
        response = await client.get("/test/custom-message")
        data = response.json()
        assert data["message"] == "Candidate abc123 not found"


class TestResponseFormat:
    @pytest.mark.anyio
    async def test_response_matches_error_schema(self, client: AsyncClient):
        """Verify response body matches ErrorResponse schema structure."""
        response = await client.get("/test/candidate-not-found")
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "details" in data
        assert data["details"] is None
