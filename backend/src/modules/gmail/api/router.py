"""FastAPI router for the Gmail Integration module.

Defines the /api/gmail/* endpoints for Gmail OAuth2 connection management,
email synchronization, message body fetching, label management, email
sending, and attachment retrieval. All endpoints require authentication.
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.modules.gmail.api.schemas import (
    ConnectionStatusResponse,
    ConnectResponse,
    ErrorResponse,
    LabelRemoveRequest,
    MessageBodyResponse,
    MessageListItem,
    MessageListResponse,
    SendEmailRequest,
    SendEmailResponse,
    SyncResponse,
)
from src.modules.gmail.application.attachment_service import (
    AttachmentMetadata,
    AttachmentService,
)
from src.modules.gmail.application.connection_service import (
    ConnectionService,
)
from src.modules.gmail.application.email_sync_service import EmailSyncService
from src.modules.gmail.application.label_service import LabelService
from src.modules.gmail.application.send_service import (
    AttachmentData,
    SendEmailParams,
    SendService,
)
from src.modules.gmail.container import (
    get_attachment_service,
    get_connection_service,
    get_email_repository,
    get_email_sync_service,
    get_gmail_adapter,
    get_label_service,
    get_send_service,
)
from src.modules.gmail.infrastructure.email_repository import EmailRepository
from src.modules.gmail.infrastructure.gmail_adapter import GmailAdapter
from src.modules.identity.container import get_current_user
from src.modules.identity.domain.entities import User


# ---------------------------------------------------------------------------
# Type aliases for injected dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
ConnectionServiceDep = Annotated[ConnectionService, Depends(get_connection_service)]
EmailSyncServiceDep = Annotated[EmailSyncService, Depends(get_email_sync_service)]
EmailRepositoryDep = Annotated[EmailRepository, Depends(get_email_repository)]
SendServiceDep = Annotated[SendService, Depends(get_send_service)]
LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
GmailAdapterDep = Annotated[GmailAdapter, Depends(get_gmail_adapter)]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


# ---------------------------------------------------------------------------
# Connection endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=ConnectionStatusResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_connection_status(
    current_user: CurrentUserDep,
    connection_service: ConnectionServiceDep,
) -> ConnectionStatusResponse:
    """Check the current Gmail connection status.

    Returns the connection state (connected, disconnected, or token_expired)
    along with the connected Gmail email address if available.

    Args:
        current_user: The authenticated user.
        connection_service: The connection service.

    Returns:
        ConnectionStatusResponse with current status.
    """
    result = await connection_service.get_status(current_user.id)
    return ConnectionStatusResponse(
        status=result.status,
        email=result.email,
    )


@router.post(
    "/connect",
    response_model=ConnectResponse,
    responses={401: {"model": ErrorResponse}},
)
async def initiate_connect(
    current_user: CurrentUserDep,
    connection_service: ConnectionServiceDep,
) -> ConnectResponse:
    """Initiate Gmail OAuth2 connection.

    If already connected with valid credentials, returns the connected status.
    Otherwise, returns a redirect URL to the Google OAuth2 consent screen.

    Args:
        current_user: The authenticated user.
        connection_service: The connection service.

    Returns:
        ConnectResponse with either connected status or redirect_url.
    """
    result = await connection_service.initiate_connect(current_user.id)
    return ConnectResponse(
        status=result.status,
        redirect_url=result.redirect_url,
    )


@router.get(
    "/callback",
    response_model=ConnectionStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
async def oauth_callback(
    current_user: CurrentUserDep,
    connection_service: ConnectionServiceDep,
    code: str = Query(..., description="Authorization code from Google OAuth2"),
    state: str = Query(default="", description="OAuth2 state parameter"),
) -> ConnectionStatusResponse:
    """Handle the OAuth2 callback from Google.

    Exchanges the authorization code for tokens, validates scopes,
    stores encrypted credentials, and triggers label initialization.

    Args:
        current_user: The authenticated user.
        connection_service: The connection service.
        code: The authorization code from Google.
        state: The OAuth2 state parameter for CSRF protection.

    Returns:
        ConnectionStatusResponse with connected status on success.
    """
    result = await connection_service.handle_callback(current_user.id, code)
    return ConnectionStatusResponse(
        status=result.status,
        email=result.email,
    )


@router.post(
    "/disconnect",
    response_model=ConnectionStatusResponse,
    responses={401: {"model": ErrorResponse}},
)
async def disconnect(
    current_user: CurrentUserDep,
    connection_service: ConnectionServiceDep,
) -> ConnectionStatusResponse:
    """Disconnect Gmail from the system.

    Revokes the OAuth2 token via Google's revocation endpoint (with 10s
    timeout), marks the OAuth grant as invalid, and removes Gmail scopes.
    Proceeds with disconnect even if revocation fails.

    Args:
        current_user: The authenticated user.
        connection_service: The connection service.

    Returns:
        ConnectionStatusResponse with disconnected status.
    """
    result = await connection_service.disconnect(current_user.id)
    return ConnectionStatusResponse(
        status=result.status,
        email=result.email,
    )


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/sync",
    response_model=SyncResponse,
    responses={
        401: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def manual_sync(
    current_user: CurrentUserDep,
    sync_service: EmailSyncServiceDep,
) -> SyncResponse:
    """Trigger a manual email synchronization.

    Performs an immediate email fetch (same logic as the scheduled poll)
    outside the regular schedule. Rate limited to 1 request per 30 seconds.

    Args:
        current_user: The authenticated user.
        sync_service: The email sync service.

    Returns:
        SyncResponse with the count of new emails fetched.
    """
    synced_count = await sync_service.manual_sync(current_user.id)
    return SyncResponse(
        synced_count=synced_count,
        status="ok",
    )


# ---------------------------------------------------------------------------
# Message endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/messages",
    response_model=MessageListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def list_messages(
    current_user: CurrentUserDep,
    email_repo: EmailRepositoryDep,
    limit: int = Query(default=50, ge=1, le=100, description="Max messages to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> MessageListResponse:
    """List email messages for the authenticated user.

    Returns messages ordered by received_at descending (most recent first).
    Supports pagination via limit/offset parameters.

    Args:
        current_user: The authenticated user.
        email_repo: The email repository.
        limit: Maximum number of messages to return (1-100, default 50).
        offset: Number of messages to skip for pagination.

    Returns:
        MessageListResponse with list of messages and total count.
    """
    messages = await email_repo.list_by_user(
        user_id=current_user.id, limit=limit, offset=offset
    )

    items = [
        MessageListItem(
            id=str(msg.id),
            gmail_message_id=msg.gmail_message_id,
            gmail_thread_id=msg.gmail_thread_id,
            subject=msg.subject,
            sender_email=msg.sender_email,
            sender_name=msg.sender_name,
            recipient_emails=msg.recipient_emails,
            cc_emails=msg.cc_emails,
            received_at=msg.received_at.isoformat(),
            snippet=msg.snippet,
            label_ids=msg.label_ids,
            has_attachments=msg.has_attachments,
            category=msg.category,
        )
        for msg in messages
    ]

    return MessageListResponse(messages=items, total=len(items))


@router.get(
    "/messages/{message_id}/body",
    response_model=MessageBodyResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def get_message_body(
    message_id: str,
    current_user: CurrentUserDep,
    gmail_adapter: GmailAdapterDep,
    connection_service: ConnectionServiceDep,
) -> MessageBodyResponse:
    """Fetch the full email body content for a message.

    Retrieves both plain text and HTML versions of the email body
    from Gmail API. Requires an active Gmail connection.

    Args:
        message_id: The Gmail message ID.
        current_user: The authenticated user.
        gmail_adapter: The Gmail API adapter.
        connection_service: The connection service for token access.

    Returns:
        MessageBodyResponse with plain_text and/or html content.
    """
    from src.modules.gmail.domain.exceptions import GmailNotConnectedException

    # Verify connection and get access token
    status_result = await connection_service.get_status(current_user.id)
    if status_result.status != "connected":
        raise GmailNotConnectedException()

    # Get access token from OAuth grant
    access_token = await _get_user_access_token(
        current_user.id, connection_service
    )

    body = await gmail_adapter.get_message_body(access_token, message_id)
    return MessageBodyResponse(
        plain_text=body.plain_text,
        html=body.html,
    )


# ---------------------------------------------------------------------------
# Label endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/messages/{message_id}/labels/remove",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def remove_label(
    message_id: str,
    body: LabelRemoveRequest,
    current_user: CurrentUserDep,
    label_service: LabelServiceDep,
    connection_service: ConnectionServiceDep,
) -> dict[str, str]:
    """Remove a VroomHR label from an email message.

    Only labels within the VroomHR/ namespace can be removed.
    Requires an active Gmail connection.

    Args:
        message_id: The Gmail message ID.
        body: Request body with the label name to remove.
        current_user: The authenticated user.
        label_service: The label service.
        connection_service: The connection service for token access.

    Returns:
        Success confirmation message.
    """
    from src.modules.gmail.domain.exceptions import GmailNotConnectedException

    # Verify connection
    status_result = await connection_service.get_status(current_user.id)
    if status_result.status != "connected":
        raise GmailNotConnectedException()

    # Get access token
    access_token = await _get_user_access_token(
        current_user.id, connection_service
    )

    await label_service.remove_label(
        user_id=current_user.id,
        message_id=message_id,
        label_name=body.label_name,
        access_token=access_token,
    )

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Send endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/send",
    response_model=SendEmailResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def send_email(
    body: SendEmailRequest,
    current_user: CurrentUserDep,
    send_service: SendServiceDep,
) -> SendEmailResponse:
    """Send an email via the user's connected Gmail account.

    Composes and sends an email with support for HTML/plain text body,
    CC recipients, reply threading, and file attachments.

    Args:
        body: The email send request with recipients, subject, and body.
        current_user: The authenticated user.
        send_service: The send service.

    Returns:
        SendEmailResponse with the sent message_id and thread_id.
    """
    # Convert request schema to service params
    attachments: list[AttachmentData] = []
    if body.attachments:
        for att in body.attachments:
            attachments.append(
                AttachmentData(
                    filename=att.filename,
                    content=base64.b64decode(att.content),
                    mime_type=att.mime_type,
                )
            )

    params = SendEmailParams(
        to=body.to,
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        cc=body.cc or [],
        reply_to_message_id=body.reply_to_message_id,
        attachments=attachments,
    )

    result = await send_service.send_email(current_user.id, params)
    return SendEmailResponse(
        message_id=result.message_id,
        thread_id=result.thread_id,
    )


# ---------------------------------------------------------------------------
# Attachment endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/messages/{message_id}/attachments",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def fetch_attachments(
    message_id: str,
    current_user: CurrentUserDep,
    attachment_service: AttachmentServiceDep,
    connection_service: ConnectionServiceDep,
    gmail_adapter: GmailAdapterDep,
) -> dict:
    """Fetch and validate attachments for an email message.

    Downloads attachments from Gmail API, validates MIME types and file
    sizes against configured limits, and returns metadata about fetched
    and skipped attachments.

    Args:
        message_id: The Gmail message ID containing attachments.
        current_user: The authenticated user.
        attachment_service: The attachment service.
        connection_service: The connection service for token access.
        gmail_adapter: The Gmail API adapter.

    Returns:
        Dictionary with fetched_count, skipped_count, and attachment metadata.
    """
    from src.modules.gmail.domain.exceptions import GmailNotConnectedException

    # Verify connection
    status_result = await connection_service.get_status(current_user.id)
    if status_result.status != "connected":
        raise GmailNotConnectedException()

    # Get access token
    access_token = await _get_user_access_token(
        current_user.id, connection_service
    )

    # Fetch the full message to get attachment parts
    response = await gmail_adapter._http_client.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"},
    )
    response.raise_for_status()
    msg_data = response.json()

    # Extract attachment metadata from message parts
    attachments_meta = _extract_attachment_metadata(msg_data.get("payload", {}))

    # Fetch attachments via the service
    result = await attachment_service.fetch_attachments(
        user_id=current_user.id,
        message_id=message_id,
        access_token=access_token,
        attachments=attachments_meta,
    )

    return {
        "fetched_count": result.fetched_count,
        "skipped_count": result.skipped_count,
        "total_count": result.total_count,
        "attachments": [
            {
                "attachment_id": att.attachment_id,
                "filename": att.filename,
                "mime_type": att.mime_type,
                "size_bytes": att.size_bytes,
            }
            for att in result.fetched
        ],
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def _get_user_access_token(
    user_id, connection_service: ConnectionService
) -> str:
    """Retrieve the decrypted access token for a user.

    Uses the connection service's internal OAuth grant repository
    to fetch and decrypt the user's Gmail access token.

    Args:
        user_id: The UUID of the user.
        connection_service: The connection service with access to OAuth grants.

    Returns:
        The decrypted access token string.

    Raises:
        GmailNotConnectedException: If no valid token is available.
    """
    from src.modules.gmail.domain.exceptions import GmailNotConnectedException
    from src.modules.identity.container import get_crypto_utils

    crypto = get_crypto_utils()
    grant = await connection_service._oauth_grant_repo.get_by_user_id(user_id)

    if grant is None or not grant.is_valid:
        raise GmailNotConnectedException()

    return crypto.decrypt(grant.access_token_enc)


def _extract_attachment_metadata(payload: dict) -> list[AttachmentMetadata]:
    """Extract attachment metadata from a Gmail message payload.

    Recursively searches the message parts for attachments (parts with
    a filename and body.attachmentId).

    Args:
        payload: The message payload from Gmail API.

    Returns:
        List of AttachmentMetadata objects for each attachment found.
    """
    attachments: list[AttachmentMetadata] = []
    _walk_parts_for_attachments(payload, attachments)
    return attachments


def _walk_parts_for_attachments(
    part: dict, attachments: list[AttachmentMetadata]
) -> None:
    """Recursively walk message parts to find attachments.

    Args:
        part: A message part from the Gmail API payload.
        attachments: Accumulator list for found attachments.
    """
    filename = part.get("filename", "")
    body = part.get("body", {})
    attachment_id = body.get("attachmentId")

    if filename and attachment_id:
        attachments.append(
            AttachmentMetadata(
                attachment_id=attachment_id,
                filename=filename,
                mime_type=part.get("mimeType", "application/octet-stream"),
                size_bytes=body.get("size", 0),
            )
        )

    # Recurse into nested parts
    for sub_part in part.get("parts", []):
        _walk_parts_for_attachments(sub_part, attachments)
