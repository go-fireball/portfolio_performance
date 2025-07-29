from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QLineEdit, QPushButton, QMessageBox)

from portfolio.database import SessionLocal
from portfolio.models import Account, User


class AccountSelectionDialog(QDialog):
    """Dialog for selecting an account when not present in the CSV."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Account")
        self.resize(400, 200)
        self.selected_account = None
        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Please select the account for these transactions:\n"
            "(The account name was not found in the CSV file)"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Account dropdown
        self.account_combo = QComboBox()
        layout.addWidget(self.account_combo)

        # Create new account option
        new_account_layout = QHBoxLayout()
        self.new_account_input = QLineEdit()
        self.new_account_input.setPlaceholderText("New account name")
        new_account_layout.addWidget(self.new_account_input)

        self.add_account_button = QPushButton("Create Account")
        self.add_account_button.clicked.connect(self._create_new_account)
        new_account_layout.addWidget(self.add_account_button)

        layout.addLayout(new_account_layout)

        # Broker field (for new accounts)
        broker_layout = QHBoxLayout()
        broker_layout.addWidget(QLabel("Broker:"))
        self.broker_input = QLineEdit()
        self.broker_input.setPlaceholderText("e.g., Fidelity, Schwab, etc.")
        broker_layout.addWidget(self.broker_input)
        layout.addLayout(broker_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    def _load_accounts(self):
        """Load existing accounts from the database."""
        db = SessionLocal()
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            self.account_combo.clear()

            # Add empty selection
            self.account_combo.addItem("-- Select an account --", None)

            # Add existing accounts
            for account in accounts:
                self.account_combo.addItem(f"{account.name} ({account.broker})", account.id)

            self.ok_button.setEnabled(False)
            self.account_combo.currentIndexChanged.connect(self._on_account_selected)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load accounts: {str(e)}")
        finally:
            db.close()

    def _on_account_selected(self, index):
        """Handle account selection from dropdown."""
        account_id = self.account_combo.currentData()
        self.ok_button.setEnabled(account_id is not None)
        if account_id is not None:
            self.selected_account = self.account_combo.currentText().split(' (')[0]

    def _create_new_account(self):
        """Create a new account."""
        account_name = self.new_account_input.text().strip()
        broker = self.broker_input.text().strip()

        if not account_name:
            QMessageBox.warning(self, "Warning", "Please enter an account name.")
            return

        if not broker:
            QMessageBox.warning(self, "Warning", "Please enter a broker name.")
            return

        # Create the new account
        db = SessionLocal()
        try:
            # Get first user (this is a single-user application)
            user = db.query(User).first()

            # Create account
            account = Account(
                user_id=user.id,
                name=account_name,
                broker=broker,
                is_taxable=True,  # Default
                is_active=True
            )
            db.add(account)
            db.commit()

            # Reload accounts and select the new one
            self._load_accounts()

            # Find and select the new account
            for i in range(self.account_combo.count()):
                if self.account_combo.itemText(i).startswith(account_name):
                    self.account_combo.setCurrentIndex(i)
                    break

            QMessageBox.information(self, "Success", f"Account '{account_name}' created successfully.")

        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to create account: {str(e)}")
        finally:
            db.close()

    def get_selected_account(self):
        """Return the selected account name."""
        return self.selected_account
