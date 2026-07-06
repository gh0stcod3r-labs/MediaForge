"""Friendly error handling and user-facing messages."""

from enum import Enum
from typing import Optional
from pathlib import Path


class ErrorType(Enum):
    """Categories of errors users might encounter."""
    
    # Provider errors
    PROVIDER_NO_KEY = "provider_no_key"
    PROVIDER_INVALID_KEY = "provider_invalid_key"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    PROVIDER_NO_INTERNET = "provider_no_internet"
    PROVIDER_NOT_FOUND = "provider_not_found"
    PROVIDER_BAD_RESPONSE = "provider_bad_response"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    
    # File operation errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_IN_USE = "file_in_use"
    FILE_PERMISSION_DENIED = "file_permission_denied"
    FILE_ALREADY_EXISTS = "file_already_exists"
    FILE_PATH_TOO_LONG = "file_path_too_long"
    FILE_INVALID_CHARS = "file_invalid_chars"
    FILE_RESERVED_NAME = "file_reserved_name"
    
    # Drive errors
    DRIVE_NOT_AVAILABLE = "drive_not_available"
    DRIVE_NO_SPACE = "drive_no_space"
    DRIVE_NO_PERMISSION = "drive_no_permission"
    
    # Matching errors
    MATCH_NO_RESULTS = "match_no_results"
    MATCH_AMBIGUOUS = "match_ambiguous"
    MATCH_LOW_CONFIDENCE = "match_low_confidence"
    
    # General errors
    GENERAL_ERROR = "general_error"


class FriendlyError:
    """User-friendly error message with context."""
    
    def __init__(
        self,
        error_type: ErrorType,
        title: str,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        self.error_type = error_type
        self.title = title
        self.message = message
        self.details = details
        self.suggestion = suggestion
    
    def full_message(self) -> str:
        """Get full error message for display."""
        parts = [self.message]
        if self.suggestion:
            parts.append(f"\n💡 Suggestion: {self.suggestion}")
        if self.details:
            parts.append(f"\nDetails: {self.details}")
        return "".join(parts)


class ErrorHandler:
    """Convert exceptions and error conditions to friendly messages."""
    
    @staticmethod
    def provider_no_key(provider_name: str) -> FriendlyError:
        """Provider API key not set."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_NO_KEY,
            title=f"{provider_name} API Key Missing",
            message=f"Please configure your {provider_name} API key to use this provider.",
            suggestion=f"Go to Settings → Providers → {provider_name} and add your API key.",
        )
    
    @staticmethod
    def provider_invalid_key(provider_name: str) -> FriendlyError:
        """Provider API key is invalid."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_INVALID_KEY,
            title=f"{provider_name} API Key Invalid",
            message=f"Your {provider_name} API key is invalid or has expired.",
            suggestion=f"Check your API key at {provider_name}'s website and update it in Settings.",
        )
    
    @staticmethod
    def provider_timeout(provider_name: str, seconds: int = 5) -> FriendlyError:
        """Provider request timed out."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_TIMEOUT,
            title=f"{provider_name} Timeout",
            message=f"{provider_name} didn't respond within {seconds} seconds.",
            suggestion="Check your internet connection or try again later.",
        )
    
    @staticmethod
    def provider_rate_limit(provider_name: str) -> FriendlyError:
        """Provider rate limit exceeded."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_RATE_LIMIT,
            title=f"{provider_name} Rate Limited",
            message=f"Too many requests to {provider_name}. Please try again in a few minutes.",
            suggestion="If this happens often, consider increasing the delay between requests.",
        )
    
    @staticmethod
    def provider_no_internet() -> FriendlyError:
        """No internet connection."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_NO_INTERNET,
            title="No Internet Connection",
            message="Can't reach any metadata providers.",
            suggestion="Check your internet connection, or use Offline mode to match files by name only.",
        )
    
    @staticmethod
    def provider_not_found(provider_name: str, query: str) -> FriendlyError:
        """Provider found no match."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_NOT_FOUND,
            title="No Match Found",
            message=f"{provider_name} couldn't find '{query}'.",
            suggestion="Try with a shorter or different title, or manually verify the match.",
        )
    
    @staticmethod
    def provider_bad_response(provider_name: str) -> FriendlyError:
        """Provider returned malformed response."""
        return FriendlyError(
            error_type=ErrorType.PROVIDER_BAD_RESPONSE,
            title=f"{provider_name} Response Error",
            message=f"{provider_name} returned an unexpected response format.",
            suggestion="Try again later, or report this to the MediaForge team.",
        )
    
    @staticmethod
    def file_not_found(filepath: Path) -> FriendlyError:
        """Source file not found."""
        return FriendlyError(
            error_type=ErrorType.FILE_NOT_FOUND,
            title="File Not Found",
            message=f"'{filepath.name}' no longer exists.",
            details=str(filepath),
            suggestion="The file may have been moved or deleted since scanning.",
        )
    
    @staticmethod
    def file_in_use(filepath: Path) -> FriendlyError:
        """File is locked by another process."""
        return FriendlyError(
            error_type=ErrorType.FILE_IN_USE,
            title="File In Use",
            message=f"'{filepath.name}' is open in another program.",
            suggestion="Close the file and try again.",
        )
    
    @staticmethod
    def file_permission_denied(filepath: Path) -> FriendlyError:
        """Permission denied on file."""
        return FriendlyError(
            error_type=ErrorType.FILE_PERMISSION_DENIED,
            title="Permission Denied",
            message=f"No permission to access '{filepath.name}'.",
            suggestion="Check file permissions or try running as administrator (Windows).",
        )
    
    @staticmethod
    def file_already_exists(filepath: Path) -> FriendlyError:
        """Destination file already exists."""
        return FriendlyError(
            error_type=ErrorType.FILE_ALREADY_EXISTS,
            title="File Already Exists",
            message=f"'{filepath.name}' already exists at destination.",
            suggestion="Choose Skip, Replace, or Rename Automatically from the options.",
        )
    
    @staticmethod
    def file_path_too_long(filepath: Path) -> FriendlyError:
        """Resulting path would be too long."""
        return FriendlyError(
            error_type=ErrorType.FILE_PATH_TOO_LONG,
            title="Path Too Long",
            message="The destination path is too long for your filesystem.",
            details=f"Length: {len(str(filepath))} (max ~260 on Windows, ~4096 on Unix)",
            suggestion="Try a shorter series name or destination root.",
        )
    
    @staticmethod
    def file_invalid_chars(filename: str, invalid_chars: str) -> FriendlyError:
        """Filename contains invalid characters."""
        return FriendlyError(
            error_type=ErrorType.FILE_INVALID_CHARS,
            title="Invalid Filename",
            message=f"'{filename}' contains invalid characters: {invalid_chars}",
            suggestion="These characters can't be used in filenames on your OS.",
        )
    
    @staticmethod
    def file_reserved_name(name: str) -> FriendlyError:
        """Filename is a reserved Windows name."""
        return FriendlyError(
            error_type=ErrorType.FILE_RESERVED_NAME,
            title="Reserved Name",
            message=f"'{name}' is a reserved system name (Windows).",
            suggestion="Try a different title or series name.",
        )
    
    @staticmethod
    def drive_not_available(path: Path) -> FriendlyError:
        """Destination drive not available."""
        return FriendlyError(
            error_type=ErrorType.DRIVE_NOT_AVAILABLE,
            title="Drive Not Available",
            message=f"The destination drive '{path.drive}' is not available.",
            suggestion="Check that external drives are connected or network drives are accessible.",
        )
    
    @staticmethod
    def drive_no_space(path: Path, needed_mb: float, available_mb: float) -> FriendlyError:
        """Insufficient disk space."""
        return FriendlyError(
            error_type=ErrorType.DRIVE_NO_SPACE,
            title="Insufficient Disk Space",
            message=f"Not enough space on '{path.drive}': need {needed_mb:.1f} MB, have {available_mb:.1f} MB.",
            suggestion="Free up space or choose a different destination drive.",
        )
    
    @staticmethod
    def drive_no_permission(path: Path) -> FriendlyError:
        """No write permission on drive."""
        return FriendlyError(
            error_type=ErrorType.DRIVE_NO_PERMISSION,
            title="Permission Denied",
            message=f"No permission to write to '{path.drive}'.",
            suggestion="Check drive permissions or try a different destination.",
        )
    
    @staticmethod
    def match_no_results(query: str) -> FriendlyError:
        """No matching results found."""
        return FriendlyError(
            error_type=ErrorType.MATCH_NO_RESULTS,
            title="No Match Found",
            message=f"Couldn't find a match for '{query}'.",
            suggestion="You can manually edit the title and season/episode before proceeding.",
        )
    
    @staticmethod
    def match_low_confidence(title: str, confidence: float) -> FriendlyError:
        """Match result is low confidence."""
        return FriendlyError(
            error_type=ErrorType.MATCH_LOW_CONFIDENCE,
            title="Low Confidence Match",
            message=f"Found '{title}' but only {confidence*100:.0f}% confident.",
            suggestion="Review the match before proceeding, or search manually.",
        )
    
    @staticmethod
    def from_exception(exception: Exception, context: Optional[str] = None) -> FriendlyError:
        """Convert generic exception to friendly error."""
        error_msg = str(exception)
        
        # Try to categorize based on exception type
        if isinstance(exception, FileNotFoundError):
            return FriendlyError(
                error_type=ErrorType.FILE_NOT_FOUND,
                title="File Not Found",
                message=error_msg,
                suggestion="The file may have been moved or deleted.",
            )
        elif isinstance(exception, PermissionError):
            return FriendlyError(
                error_type=ErrorType.FILE_PERMISSION_DENIED,
                title="Permission Denied",
                message=error_msg,
                suggestion="Check permissions or try running as administrator.",
            )
        elif isinstance(exception, TimeoutError):
            return FriendlyError(
                error_type=ErrorType.PROVIDER_TIMEOUT,
                title="Request Timeout",
                message="The request took too long to complete.",
                suggestion="Try again, or check your internet connection.",
            )
        else:
            return FriendlyError(
                error_type=ErrorType.GENERAL_ERROR,
                title="An Error Occurred",
                message=error_msg,
                details=context or None,
                suggestion="Check the logs for more details.",
            )
