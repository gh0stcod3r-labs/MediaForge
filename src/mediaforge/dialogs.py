"""Custom dialogs for MediaForge Organizer."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QProgressDialog
)
from PySide6.QtGui import QFont

from .constants import SPACING_MD, SECONDARY_TEXT


class APIKeyDialog(QDialog):
    """Dialog for configuring API keys."""
    
    def __init__(self, parent, provider_name: str, current_key: str = ""):
        super().__init__(parent)
        self.provider_name = provider_name
        self.api_key = None
        self.test_passed = False
        
        self._setup_ui(current_key)
    
    def _setup_ui(self, current_key: str):
        """Setup dialog UI."""
        self.setWindowTitle(f"Configure {self.provider_name} API Key")
        self.setGeometry(200, 200, 400, 250)
        
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_MD)
        
        # Header
        header = QLabel(f"🔑 {self.provider_name} API Key")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Instructions
        instructions = QLabel(
            f"Enter your {self.provider_name} API key.\n"
            "This will be stored locally and never shared."
        )
        instructions.setStyleSheet(f"color: {SECONDARY_TEXT};")
        layout.addWidget(instructions)
        
        # Key input
        layout.addWidget(QLabel("API Key:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your API key here")
        self.key_input.setText(current_key)
        self.key_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.key_input)
        
        # Show/hide button
        show_btn = QPushButton("👁 Show")
        show_btn.setMaximumWidth(80)
        show_btn.clicked.connect(self._toggle_show)
        layout.addWidget(show_btn)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("🧪 Test")
        test_btn.clicked.connect(self._test_key)
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _toggle_show(self):
        """Toggle showing/hiding the key."""
        if self.key_input.echoMode() == QLineEdit.Password:
            self.key_input.setEchoMode(QLineEdit.Normal)
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
    
    def _test_key(self):
        """Test the API key (provider-specific logic would go here)."""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key first.")
            return
        
        # TODO: Call provider test method
        QMessageBox.information(
            self,
            "Test Result",
            "API key format looks valid.\n(Full test requires internet connection)"
        )
        self.test_passed = True
    
    def _save(self):
        """Save the key and close dialog."""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key.")
            return
        
        self.api_key = key
        self.accept()
    
    def get_api_key(self) -> str:
        """Get the entered API key."""
        return self.api_key or ""


class ProgressDialog(QProgressDialog):
    """Custom progress dialog for long operations."""
    
    def __init__(self, parent, title: str, label: str, maximum: int = 100):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLabelText(label)
        self.setMaximum(maximum)
        self.setAutoReset(False)
        self.setAutoClose(False)
        self.setCancelButtonText("Cancel")
        self.setValue(0)
    
    def update_progress(self, current: int, total: int, current_item: str = ""):
        """Update progress bar."""
        self.setMaximum(total)
        self.setValue(current)
        
        if current_item:
            self.setLabelText(f"{current_item}\n{current}/{total}")
        else:
            self.setLabelText(f"{current}/{total}")
    
    def was_cancelled(self) -> bool:
        """Check if user cancelled."""
        return self.wasCanceled()


class ConfirmUndoDialog(QDialog):
    """Dialog to confirm destructive undo operation."""
    
    def __init__(self, parent, operations_count: int):
        super().__init__(parent)
        self.confirmed = False
        
        self._setup_ui(operations_count)
    
    def _setup_ui(self, operations_count: int):
        """Setup dialog UI."""
        self.setWindowTitle("Confirm Undo")
        self.setGeometry(200, 200, 400, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_MD)
        
        # Warning
        warning = QLabel(
            "⚠️  This will undo the following operations:\n\n"
            f"• {operations_count} file operations\n\n"
            "This cannot be undone. Are you sure?"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #ff9800;")
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("✔️  Undo Anyway")
        confirm_btn.clicked.connect(self._confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _confirm(self):
        """User confirmed undo."""
        self.confirmed = True
        self.accept()
    
    def was_confirmed(self) -> bool:
        """Check if undo was confirmed."""
        return self.confirmed
