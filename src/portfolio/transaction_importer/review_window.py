from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Slot, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QTableView, QHeaderView,
                               QAbstractItemView, QFileDialog, QMessageBox)

from portfolio.models import TransactionType, InstrumentType
from portfolio.transaction_importer.column_mapper import ColumnMapperDialog
from portfolio.transaction_importer.account_selection import AccountSelectionDialog
from portfolio.transaction_importer.table_model import TransactionTableModel
from portfolio.transaction_importer.delegates import DateDelegate, ComboBoxDelegate, DecimalDelegate, JSONDelegate
from portfolio.transaction_importer.csv_import import import_transactions_from_csv
from portfolio.transaction_importer.db import save_transactions


class TransactionReviewWindow(QMainWindow):
    """Main window for reviewing and editing imported transactions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transaction Import Review")
        self.resize(1000, 600)

        # Set up central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Set up UI components
        self._setup_ui()

        # Initialize variables
        self.transactions = []
        self.filepath = ""
        self.column_mappings = None
        self.account_name_override = None
        self.decimal_validator = self._create_decimal_validator()

    def _setup_ui(self):
        """Set up the UI components."""
        # Header label
        self.header_label = QLabel("Review Transactions Before Import")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(self.header_label)

        # Status label
        self.status_label = QLabel("No file loaded")
        self.main_layout.addWidget(self.status_label)

        # Table view for transactions
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_layout.addWidget(self.table_view)

        # Buttons layout
        button_layout = QHBoxLayout()

        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        button_layout.addWidget(self.load_button)

        self.save_button = QPushButton("Save to Database")
        self.save_button.clicked.connect(self.save_to_database)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        self.discard_button = QPushButton("Discard")
        self.discard_button.clicked.connect(self.discard_data)
        self.discard_button.setEnabled(False)
        button_layout.addWidget(self.discard_button)

        self.main_layout.addLayout(button_layout)

    def _create_decimal_validator(self):
        """Create a validator for decimal inputs."""
        # Allow numbers with up to 8 decimal places
        regex = QRegularExpression(r"^-?\d*(\.\d{0,8})?$")
        return QRegularExpressionValidator(regex)

    def _setup_table_model(self, transactions):
        """Set up the table model and delegates."""
        # Define columns to display
        columns = [
            'transaction_date', 'symbol', 'transaction_type', 'instrument_type',
            'quantity', 'price', 'amount', 'fees', 'account_name', 
            'journal_details', 'notes', 'errors'
        ]

        # Create model
        self.model = TransactionTableModel(transactions, columns, self)
        self.table_view.setModel(self.model)

        # Set up delegates for different column types
        date_delegate = DateDelegate(self)
        self.table_view.setItemDelegateForColumn(
            columns.index('transaction_date'), date_delegate)

        # Transaction type delegate
        tx_type_options = [t.value for t in TransactionType]
        tx_type_delegate = ComboBoxDelegate(tx_type_options, self)
        self.table_view.setItemDelegateForColumn(
            columns.index('transaction_type'), tx_type_delegate)

        # Instrument type delegate
        instr_type_options = [t.value for t in InstrumentType]
        instr_type_delegate = ComboBoxDelegate(instr_type_options, self)
        self.table_view.setItemDelegateForColumn(
            columns.index('instrument_type'), instr_type_delegate)

        # Decimal delegates
        decimal_columns = ['quantity', 'price', 'amount', 'fees']
        decimal_delegate = DecimalDelegate(self)
        for col in decimal_columns:
            self.table_view.setItemDelegateForColumn(
                columns.index(col), decimal_delegate)

        # JSON delegate
        json_delegate = JSONDelegate(self)
        self.table_view.setItemDelegateForColumn(
            columns.index('journal_details'), json_delegate)

        # Update button states
        self.save_button.setEnabled(not self.model.hasErrors())
        self.discard_button.setEnabled(True)

        # Connect to dataChanged signal to update save button state
        self.model.dataChanged.connect(self._on_data_changed)

    @Slot()
    def load_csv(self):
        """Load and parse a CSV file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if not filepath:
            return

        try:
            self.filepath = filepath

            # First load the file to get headers and preview data
            headers, preview_data = import_transactions_from_csv(filepath)

            # Show column mapping dialog
            mapping_dialog = ColumnMapperDialog(headers, preview_data, self)
            if mapping_dialog.exec():
                # User confirmed the mapping
                self.column_mappings = mapping_dialog.get_mappings()

                # Check if account_name is mapped
                if 'account_name' not in self.column_mappings:
                    # Show account selection dialog
                    account_dialog = AccountSelectionDialog(self)
                    if account_dialog.exec():
                        selected_account = account_dialog.get_selected_account()
                        if selected_account:
                            # Use the selected account for all transactions
                            self.account_name_override = selected_account
                        else:
                            QMessageBox.warning(
                                self, "Warning", 
                                "No account selected. Cannot import transactions without an account."
                            )
                            return
                    else:
                        # User cancelled the dialog
                        return
                else:
                    self.account_name_override = None

                # Now parse the file with the mappings
                self.transactions = import_transactions_from_csv(filepath, self.column_mappings)

                # Apply account override if needed
                if self.account_name_override:
                    for transaction in self.transactions:
                        transaction['account_name'] = self.account_name_override

                # Show file info in status label
                filename = Path(filepath).name
                self.status_label.setText(
                    f"Loaded {filename} with {len(self.transactions)} transactions. "
                    f"Fix any highlighted errors before saving."
                )

                # Set up table model with the imported data
                self._setup_table_model(self.transactions)
            else:
                # User canceled the mapping
                self.filepath = ""

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    @Slot()
    def save_to_database(self):
        """Save valid transactions to the database."""
        if not self.transactions:
            return

        if self.model.hasErrors():
            QMessageBox.warning(
                self, "Validation Errors",
                "Please fix all validation errors before saving."
            )
            return

        try:
            # Get transactions from model as they may have been edited
            transactions_to_save = self.model.getTransactions()

            # Save to database
            save_transactions(transactions_to_save)

            # Show success message
            QMessageBox.information(
                self, "Success",
                f"Successfully imported {len(transactions_to_save)} transactions."
            )

            # Reset UI
            self.discard_data()

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to save transactions: {str(e)}"
            )

    @Slot()
    def discard_data(self):
        """Discard imported data and reset the UI."""
        self.transactions = []
        self.filepath = ""
        self.column_mappings = None
        self.account_name_override = None
        self.status_label.setText("No file loaded")

        # Clear table view
        self.table_view.setModel(None)

        # Update button states
        self.save_button.setEnabled(False)
        self.discard_button.setEnabled(False)

    @Slot()
    def _on_data_changed(self):
        """Update UI when data in the model changes."""
        # Enable/disable save button based on validation state
        has_errors = self.model.hasErrors()
        self.save_button.setEnabled(not has_errors)

        # Update status label
        if has_errors:
            self.status_label.setText(
                "Please fix highlighted errors before saving."
            )
        else:
            self.status_label.setText(
                f"Ready to import {len(self.transactions)} transactions."
            )

            # For option expiration, ensure amount is 0
            for transaction in self.transactions:
                if transaction.get('transaction_type') == TransactionType.OPTION_EXPIRATION:
                    transaction['price'] = Decimal('0')
                    transaction['amount'] = Decimal('0')
