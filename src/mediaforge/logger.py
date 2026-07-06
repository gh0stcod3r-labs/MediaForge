"""Operation and undo logging for MediaForge Organizer."""

import json
from pathlib import Path
from typing import Optional
from .operation_result import OperationResult, OperationType, OperationStatus


class OperationLogger:
    """Logs file operations for audit trail and undo capability."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize logger with optional custom log directory."""
        self.log_dir = log_dir or Path.home() / ".mediaforge" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.operation_log_path = self.log_dir / "operations.jsonl"
        self.undo_stack_path = self.log_dir / "undo_stack.json"
    
    def log_operation(self, op: OperationResult) -> None:
        """Log a single file operation."""
        entry = {
            "timestamp": op.timestamp.isoformat(),
            "operation_type": op.operation_type.value,
            "source": str(op.source_path),
            "destination": str(op.destination_path),
            "status": op.status.value,
            "provider": op.provider,
            "confidence": op.confidence,
            "duration_ms": op.duration_ms,
            "error_message": op.error_message,
        }
        with open(self.operation_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_operations(self, limit: Optional[int] = 100) -> list[dict]:
        """Retrieve recent operations."""
        if not self.operation_log_path.exists():
            return []
        
        operations = []
        try:
            with open(self.operation_log_path, "r") as f:
                for line in f:
                    if line.strip():
                        operations.append(json.loads(line))
        except Exception:
            pass
        
        if limit is None:
            return operations
        return operations[-limit:]
    
    def push_undo(self, operation: OperationResult) -> None:
        """Push operation onto undo stack."""
        undo_stack = self._read_undo_stack()
        undo_stack.append({
            "timestamp": operation.timestamp.isoformat(),
            "operation_type": operation.operation_type.value,
            "source": str(operation.source_path),
            "destination": str(operation.destination_path),
        })
        self._write_undo_stack(undo_stack)
    
    def pop_undo(self) -> Optional[OperationResult]:
        """Pop and return the most recent undoable operation."""
        undo_stack = self._read_undo_stack()
        if not undo_stack:
            return None
        
        undo_entry = undo_stack.pop()
        self._write_undo_stack(undo_stack)
        
        return OperationResult(
            operation_type=OperationType[undo_entry["operation_type"].replace(" ", "_").upper()],
            source_path=Path(undo_entry["source"]),
            destination_path=Path(undo_entry["destination"]),
            status=OperationStatus.SUCCESS,
        )
    
    def push_undo_batch(self, operations: list[OperationResult]) -> None:
        """Push a batch of operations onto undo stack atomically."""
        undo_stack = self._read_undo_stack()
        for op in operations:
            undo_stack.append({
                "timestamp": op.timestamp.isoformat(),
                "operation_type": op.operation_type.value,
                "source": str(op.source_path),
                "destination": str(op.destination_path),
            })
        self._write_undo_stack(undo_stack)
    
    def pop_undo_batch(self) -> Optional[list[OperationResult]]:
        """Pop the entire last batch from undo stack atomically."""
        undo_stack = self._read_undo_stack()
        if not undo_stack:
            return None
        
        # Find batch boundary by scanning for same timestamp
        # For now, collect all remaining ops (single batch assumption)
        batch = undo_stack[-len(undo_stack):]
        
        # Convert back to OperationResult
        results = []
        for entry in batch:
            results.append(OperationResult(
                operation_type=OperationType[entry["operation_type"].replace(" ", "_").upper()],
                source_path=Path(entry["source"]),
                destination_path=Path(entry["destination"]),
                status=OperationStatus.SUCCESS,
            ))
        
        # Clear stack
        self._write_undo_stack([])
        return results if results else None
    
    def undo_operation(self, op: OperationResult) -> bool:
        """Undo a single operation."""
        try:
            if op.operation_type == OperationType.COPY:
                # Remove copied file
                if op.destination_path.exists():
                    op.destination_path.unlink()
            
            elif op.operation_type == OperationType.MOVE:
                # Move file back
                if op.destination_path.exists():
                    op.destination_path.rename(op.source_path)
            
            elif op.operation_type == OperationType.RENAME:
                # Rename back
                if op.destination_path.exists():
                    op.destination_path.rename(op.source_path)
            
            return True
        except Exception:
            return False
    
    def _read_undo_stack(self) -> list[dict]:
        """Read undo stack from disk."""
        if not self.undo_stack_path.exists():
            return []
        try:
            with open(self.undo_stack_path, "r") as f:
                return json.load(f)
        except Exception:
            return []
    
    def _write_undo_stack(self, stack: list[dict]) -> None:
        """Write undo stack to disk."""
        try:
            with open(self.undo_stack_path, "w") as f:
                json.dump(stack, f, indent=2)
        except Exception:
            pass
    
    def export_csv(self, output_path: Path) -> bool:
        """Export operation log to CSV format.
        
        Args:
            output_path: Path to write CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            operations = self.get_operations(limit=None)
            
            if not operations:
                return False
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'timestamp', 'operation_type', 'source', 'destination',
                    'status', 'provider', 'confidence', 'duration_ms', 'error_message'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for op in operations:
                    writer.writerow({
                        'timestamp': op.get('timestamp', ''),
                        'operation_type': op.get('operation_type', ''),
                        'source': op.get('source', ''),
                        'destination': op.get('destination', ''),
                        'status': op.get('status', ''),
                        'provider': op.get('provider', ''),
                        'confidence': op.get('confidence', ''),
                        'duration_ms': op.get('duration_ms', ''),
                        'error_message': op.get('error_message', ''),
                    })
            
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
    
    def export_json(self, output_path: Path) -> bool:
        """Export operation log to JSON format.
        
        Args:
            output_path: Path to write JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            operations = self.get_operations(limit=None)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(operations, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
    
    def export_report(self, output_path: Path) -> bool:
        """Export operation statistics report.
        
        Args:
            output_path: Path to write report file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            operations = self.get_operations(limit=None)
            
            # Calculate statistics
            success_count = sum(1 for op in operations if op.get('status') == 'SUCCESS')
            error_count = sum(1 for op in operations if op.get('status') != 'SUCCESS')
            total_duration = sum(op.get('duration_ms', 0) for op in operations)
            
            providers = {}
            for op in operations:
                provider = op.get('provider', 'Unknown')
                providers[provider] = providers.get(provider, 0) + 1
            
            report = f"""
Operation Log Report
====================

Summary:
  Total Operations: {len(operations)}
  Successful:       {success_count}
  Failed:           {error_count}
  Total Duration:   {total_duration}ms

Providers Used:
"""
            for provider, count in sorted(providers.items(), key=lambda x: x[1], reverse=True):
                report += f"  {provider}: {count}\n"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            return True
        except Exception as e:
            print(f"Error exporting report: {e}")
            return False
