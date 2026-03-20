import hashlib
import hmac
import json
import logging
from time import time
from typing import Any, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.dependencies import get_session
from app.adapters.db.sql_user_repository import SQLUserRepository
from app.db.models import WebhookEventRecord
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def shorten_floats(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: shorten_floats(value) for key, value in data.items()}
    if isinstance(data, list):
        return [shorten_floats(item) for item in data]
    if isinstance(data, float) and data.is_integer():
        return int(data)
    return data


def _is_recent_timestamp(timestamp_header: str) -> bool:
    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError):
        return False
    return abs(int(time()) - timestamp) <= 300


def verify_webhook_signature_v2(
    request_body_json: dict,
    signature_header: str,
    timestamp_header: str,
    secret_key: str,
) -> bool:
    if not _is_recent_timestamp(timestamp_header):
        return False

    encoded_data = json.dumps(
        shorten_floats(request_body_json),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected_signature)


def verify_webhook_signature_simple(
    request_body_json: dict,
    signature_header: str,
    timestamp_header: str,
    secret_key: str,
) -> bool:
    if not _is_recent_timestamp(timestamp_header):
        return False

    canonical_string = ":".join(
        [
            str(request_body_json.get("timestamp", "")),
            str(request_body_json.get("session_id", "")),
            str(request_body_json.get("status", "")),
            str(request_body_json.get("webhook_type", "")),
        ]
    )
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected_signature)


def _get_didit_session_decision(session_id: str) -> Optional[str]:
    if not session_id:
        return None
    try:
        response = requests.get(
            f"{settings.DIDIT_BASE_URL}/session/{session_id}/",
            headers={"X-API-Key": settings.DIDIT_API_KEY, "accept": "application/json"},
            timeout=10,
        )
        if response.status_code not in (200, 201):
            logger.warning("Didit session lookup failed: %s", response.status_code)
            return None
        data = response.json()
        return data.get("decision")
    except Exception as exc:
        logger.warning("Didit session lookup error: %s", exc)
        return None


def _normalize_decision_value(decision: Any) -> str:
    if isinstance(decision, str):
        return decision.strip().lower()
    if isinstance(decision, dict):
        for key in ("status", "decision", "result"):
            value = decision.get(key)
            if isinstance(value, str):
                return value.strip().lower()
    return ""


def _normalize_status_value(status: Any) -> str:
    if not isinstance(status, str):
        return ""
    return status.strip().lower().replace("_", " ")


def _extract_status_from_payload(payload: dict, decision: Any) -> str:
    direct_status = _normalize_status_value(payload.get("status"))
    if direct_status:
        return direct_status

    if isinstance(decision, dict):
        for key in ("status", "decision", "result"):
            nested_status = _normalize_status_value(decision.get(key))
            if nested_status:
                return nested_status
    return ""


def _is_approved(status: Any, decision: Any) -> bool:
    decision_value = _normalize_decision_value(decision)
    status_value = _extract_status_from_payload({"status": status}, decision)
    return decision_value == "approved" or status_value == "approved"


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    headers = dict(request.headers)
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    logger.info(f"[WEBHOOK] Headers recibidos: {headers}")
    logger.info(f"[WEBHOOK] Body recibido: {body_str}")
    print(f"[WEBHOOK] Headers recibidos: {headers}")
    print(f"[WEBHOOK] Body recibido: {body_str}")

    try:
        json_body = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    signature_v2 = request.headers.get("x-signature-v2")
    signature_simple = request.headers.get("x-signature-simple")
    timestamp = request.headers.get("x-timestamp")
    secret = settings.DIDIT_WEBHOOK_SECRET

    if not timestamp or not secret:
        raise HTTPException(status_code=401, detail="Missing required headers")

    verified = False
    if signature_v2 and verify_webhook_signature_v2(json_body, signature_v2, timestamp, secret):
        verified = True
    elif signature_simple and verify_webhook_signature_simple(json_body, signature_simple, timestamp, secret):
        verified = True

    if not verified:
        raise HTTPException(status_code=401, detail="Invalid signature")

    session_id = json_body.get("session_id")
    vendor_data = json_body.get("vendor_data")
    status = _extract_status_from_payload(json_body, json_body.get("decision"))
    decision = json_body.get("decision") or _get_didit_session_decision(session_id)

    event_id = hashlib.sha256(
        f"{timestamp}:{json_body.get('webhook_type')}:{session_id}:{body_str}".encode("utf-8")
    ).hexdigest()
    event_timestamp = int(timestamp) if timestamp and timestamp.isdigit() else None
    existing_event = await session.execute(
        select(WebhookEventRecord.id).where(WebhookEventRecord.event_id == event_id)
    )
    if existing_event.scalar_one_or_none() is not None:
        logger.info("Duplicate webhook ignored event_id=%s", event_id)
        return {"message": "Duplicate webhook ignored", "event_id": event_id}

    session.add(
        WebhookEventRecord(
            event_id=event_id,
            provider="didit",
            webhook_type=json_body.get("webhook_type"),
            session_id=session_id,
            vendor_data=vendor_data,
            event_timestamp=event_timestamp,
            payload=json_body,
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        logger.info("Duplicate webhook ignored on race condition event_id=%s", event_id)
        return {"message": "Duplicate webhook ignored", "event_id": event_id}

    logger.info("Webhook accepted event_id=%s session_id=%s", event_id, session_id)

    if vendor_data:
        user_repository = SQLUserRepository(session)
        user_tuple = await user_repository.get_by_email(vendor_data)
        if user_tuple and user_tuple[0]:
            user = user_tuple[0]
            user.is_kyc_verified = _is_approved(status, decision)
            await user_repository.update(user)
            logger.info(
                "KYC updated for user=%s is_kyc_verified=%s",
                user.email,
                user.is_kyc_verified,
            )
        else:
            logger.info("Webhook vendor_data did not match user email: %s", vendor_data)

    return {"message": "Webhook processed", "event_id": event_id}
