"""Domain value objects — pure data, no external dependencies."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Chunk:
    doc_id: str
    text: str
    tenant_id: str
    source: str
    tokens: int = 0
