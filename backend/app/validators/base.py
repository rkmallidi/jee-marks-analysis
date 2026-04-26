from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RowError:
    row: int
    column: str
    message: str

    def as_dict(self) -> dict:
        return {"row": self.row, "column": self.column, "message": self.message}


@dataclass
class ValidationResult:
    errors: list[RowError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add(self, row: int, column: str, message: str) -> None:
        self.errors.append(RowError(row=row, column=column, message=message))

    def as_dicts(self) -> list[dict]:
        return [e.as_dict() for e in self.errors]
