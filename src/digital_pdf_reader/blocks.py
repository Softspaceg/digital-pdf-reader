from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockKind(Enum):
    TEXT = "text"
    TABLE = "table"


@dataclass(frozen=True)
class PageBlock:
    kind: BlockKind
    text: str
    table_rows: list[list[str]] | None = None


@dataclass(frozen=True)
class DocumentContent:
    blocks: list[PageBlock]

    @property
    def full_text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text.strip())

    @property
    def raw_tables(self) -> list[list[list[str]]]:
        return [block.table_rows for block in self.blocks if block.table_rows]
