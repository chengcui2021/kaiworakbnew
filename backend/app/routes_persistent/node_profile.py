from __future__ import annotations
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/kaiwora", tags=["kaiwora-node"])


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@router.get("/node-profile")
def node_profile() -> dict:
    """Describe the role of this KB deployment without exposing customer data."""
    role = os.getenv("KAIWORA_NODE_ROLE", "internal").strip().lower()
    if role not in {"internal", "customer"}:
        role = "internal"
    return {
        "product": "kaiwora",
        "role": role,
        "full_admin_ui": _flag("KAIWORA_FULL_ADMIN_UI", role == "internal"),
        "knowledge_sources_enabled": _flag("KAIWORA_KNOWLEDGE_SOURCES_ENABLED", True),
        "local_learning_enabled": _flag("KAIWORA_LOCAL_LEARNING_ENABLED", True),
        "shared_baseline_enabled": _flag("KAIWORA_SHARED_BASELINE_ENABLED", True),
        "private_customer_data_upload": False,
        "description": (
            "Kaiwora internal intelligence factory and runtime" if role == "internal"
            else "Customer-controlled Kaiwora KB runtime with private local learning"
        ),
    }
