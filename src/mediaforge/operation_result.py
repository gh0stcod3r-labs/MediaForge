"""File operation results and status tracking."""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
from enum import Enum
from datetime import datetime


class OperationType(Enum):
    """File operation types."""
    RENAME = "Rename"
    MOVE = "Move"
    COPY = "Copy"
    FOLDER_CREATE = "Folder Create"


class OperationStatus(Enum):
    """Operation execution status."""
    SUCCESS = "Success"
    SKIPPED = "Skipped"
    FAILED = "Failed"
    DUPLICATE_PROMPT = "Duplicate Prompt"


class DuplicateAction(Enum):
    """User action when duplicate is encountered."""
    SKIP = "Skip"
    REPLACE = "Replace"
    RENAME_AUTO = "Rename Automatically"


@dataclass
class OperationResult:
    """Result of a single file operation."""
    
    operation_type: OperationType
    source_path: Path
    destination_path: Path
    status: OperationStatus
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Details
    provider: str = ""
    confidence: float = 0.0
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    
    # Undo info
    undo_action: Optional[DuplicateAction] = None
    
    def is_success(self) -> bool:
        """Check if operation succeeded."""
        return self.status == OperationStatus.SUCCESS
    
    def __str__(self) -> str:
        """String representation."""
        status_icon = "✔" if self.is_success() else "✗" if self.status == OperationStatus.FAILED else "⊘"
        return f"{status_icon} {self.operation_type.value}: {self.source_path.name} → {self.destination_path.name}"


@dataclass
class OperationPlan:
    """Complete plan of operations before execution."""
    
    operations: List[OperationResult] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    folders_to_create: List[Path] = field(default_factory=list)
    is_dry_run: bool = False
    
    # Summary
    warnings: List[str] = field(default_factory=list)
    
    def add_operation(self, op: OperationResult) -> None:
        """Add operation to plan."""
        self.operations.append(op)
    
    def add_warning(self, warning: str) -> None:
        """Add warning to plan."""
        self.warnings.append(warning)
    
    def get_summary(self) -> dict:
        """Get plan summary."""
        return {
            "total_operations": len(self.operations),
            "total_files": self.total_files,
            "total_size_mb": self.total_size_bytes / 1024 / 1024,
            "folders_to_create": len(self.folders_to_create),
            "is_dry_run": self.is_dry_run,
            "warnings": len(self.warnings),
        }


@dataclass
class ExecutionResult:
    """Result of batch operation execution."""
    
    successful: List[OperationResult] = field(default_factory=list)
    failed: List[OperationResult] = field(default_factory=list)
    skipped: List[OperationResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    
    def get_summary(self) -> dict:
        """Get execution summary."""
        return {
            "successful": len(self.successful),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "total_duration_ms": self.total_duration_ms,
        }
