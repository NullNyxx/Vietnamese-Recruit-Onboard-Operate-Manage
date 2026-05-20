"""Pydantic request/response schemas for the Gmail Integration API.

Defines data transfer objects used by the Gmail router endpoints
for structured data validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator

from src.modules.gmail.domain.enums import ConnectionStatus


# ---------------------------------------------------------------------------
# Connection schemas
# ---------------------------------------------------------------------------


class ConnectionStatusResponse(BaseModel):
    """Response schema for Gmail connection status check.

    Attributes:
        status: Current connection state (connected, disconnected, token_expired).
        email: Connected Gmail address, if available.
    """

    status: ConnectionStatus
    email: str | None = None


class ConnectResponse(BaseModel):
    """Response schema for Gmail connect initiation.

    Returns either a connected status (already connected) or a redirect URL
    to the Google OAuth2 consent screen.

    Attributes:
        status: Connection status if already connected.
        redirect_url: Google OAuth2 consent URL if connection flow needed.
    """

    status: ConnectionStatus | None = None
    redirect_url: str | None = None


# ---------------------------------------------------------------------------
# Email send schemas
# ---------------------------------------------------------------------------


class AttachmentPayload(BaseModel):
    """Attachment data for outgoing emails.

    Attributes:
        filename: Original filename of the attachment.
        content: Base64-encoded file content.
        mime_type: MIME type of the attachment.
    """

    filename: str
    content: str
    mime_type: str


class SendEmailRequest(BaseModel):
    """Request schema for sending an email via Gmail.

    Attributes:
        to: List of recipient email addresses (1-50).
        cc: Optional list of CC email addresses (max 50).
        subject: Email subject line (max 500 characters).
        body_html: HTML body content (optional, at least one body required).
        body_text: Plain text body content (optional, at least one body required).
        reply_to_message_id: Gmail message ID for threading (optional).
        attachments: List of file attachments (optional, max 10).
    """

    to: list[str] = Field(..., min_length=1, max_length=50)
    cc: list[str] | None = Field(default=None, max_length=50)
    subject: str = Field(..., max_length=500)
    body_html: str | None = None
    body_text: str | None = None
    reply_to_message_id: str | None = None
    attachments: list[AttachmentPayload] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def at_least_one_body(self) -> "SendEmailRequest":
        """Ensure at least one of body_html or body_text is provided."""
        if self.body_html is None and self.body_text is None:
            msg = "At least one of body_html or body_text must be provided"
            raise ValueError(msg)
        return self


class SendEmailResponse(BaseModel):
    """Response schema after successfully sending an email.

    Attributes:
        message_id: Gmail message ID of the sent email.
        thread_id: Gmail thread ID of the sent email.
    """

    message_id: str
    thread_id: str


# ---------------------------------------------------------------------------
# Message body schema
# ---------------------------------------------------------------------------


class MessageBodyResponse(BaseModel):
    """Response schema for fetching full email body content.

    Attributes:
        plain_text: Plain text version of the email body.
        html: HTML version of the email body.
    """

    plain_text: str | None = None
    html: str | None = None


# ---------------------------------------------------------------------------
# Label schemas
# ---------------------------------------------------------------------------


class LabelRemoveRequest(BaseModel):
    """Request schema for removing a label from an email.

    Attributes:
        label_name: Name of the label to remove (must be in VroomHR/ namespace).
    """

    label_name: str

    @field_validator("label_name")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Ensure label is within the VroomHR/ namespace."""
        if not v.startswith("VroomHR/"):
            msg = "Label must be within the VroomHR/ namespace"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# Sync schemas
# ---------------------------------------------------------------------------


class SyncResponse(BaseModel):
    """Response schema for manual sync trigger.

    Attributes:
        synced_count: Number of new emails fetched during sync.
        status: Result status description.
    """

    synced_count: int
    status: str


class MessageListItem(BaseModel):
    """Response schema for a single email in the messages list.

    Attributes:
        id: Internal UUID of the email record.
        gmail_message_id: Gmail's unique message identifier.
        gmail_thread_id: Gmail's thread identifier.
        subject: Email subject line.
        sender_email: Sender's email address.
        sender_name: Sender's display name.
        recipient_emails: List of recipient email addresses.
        cc_emails: List of CC email addresses.
        received_at: When the email was received.
        snippet: Short preview of the email body.
        label_ids: Gmail label IDs applied to this message.
        has_attachments: Whether the email has attachments.
        category: AI-assigned category, if any.
    """

    id: str
    gmail_message_id: str
    gmail_thread_id: str
    subject: str
    sender_email: str
    sender_name: str
    recipient_emails: list[str]
    cc_emails: list[str]
    received_at: str
    snippet: str
    label_ids: list[str]
    has_attachments: bool
    category: str | None = None


class MessageListResponse(BaseModel):
    """Response schema for listing email messages.

    Attributes:
        messages: List of email message summaries.
        total: Total number of messages returned.
    """

    messages: list[MessageListItem]
    total: int


# ---------------------------------------------------------------------------
# Error schemas
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response schema for Gmail API endpoints.

    Attributes:
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
        details: Optional additional error context.
    """

    error_code: str
    message: str
    details: dict | None = None
