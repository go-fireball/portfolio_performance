import json
import logging
import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton, QFileDialog,
                               QMessageBox, QScrollArea, QWidget, QTableView, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ColumnMapperDialog(QDialog):
    """Dialog for mapping CSV columns to application fields."""
    def __init__(self, csv_headers, preview_data, parent=None):
        super().__init__(parent)
        self.csv_headers = csv_headers
        self.preview_data = preview_data[:5]  # Use first 5 rows for preview
        self.column_mappings = {}
        self.required_fields = [
            'date', 'action'
        ]
        self.transaction_type_specific_fields = {
            'buy': ['symbol', 'quantity', 'price', 'instrument_type'],
            'sell': ['symbol', 'quantity', 'price', 'instrument_type'],
            'dividend': ['symbol', 'amount', 'instrument_type'],
            'deposit': ['amount'],
            'withdrawal': ['amount'],
            'fee': ['amount'],
            'transfer_in': ['symbol', 'quantity', 'instrument_type'],
            'transfer_out': ['symbol', 'quantity', 'instrument_type'],
        }
        self.all_possible_fields = [
            'date', 'symbol', 'action', 'quantity', 'price', 'amount', 
            'fees', 'account_name', 'instrument_type', 'notes', 'journal_details'
        ]

        self.setWindowTitle("Map CSV Columns")
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Please map the columns from your CSV file to the fields needed by the application. \n"
            "Required fields are marked with *. Other fields may be required based on transaction type.")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        # Create a scroll area for the mappings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Attempt to detect common patterns in headers
        self._detect_column_patterns()

        # Add mapping rows for each field
        for field in self.all_possible_fields:
            is_required = field in self.required_fields
            row_layout = QHBoxLayout()

            # Field label
            label_text = f"{field}{'*' if is_required else ''}:"
            label = QLabel(label_text)
            label.setMinimumWidth(150)

            # Add tooltips to explain each field
            tooltips = {
                'date': "Transaction date in any common format (YYYY-MM-DD, MM/DD/YYYY, etc.)",
                'symbol': "Stock ticker symbol (e.g., AAPL, MSFT)",
                'action': "Transaction type (buy, sell, dividend, deposit, withdrawal, etc.)",
                'quantity': "Number of shares or units",
                'price': "Price per share/unit",
                'amount': "Total transaction amount (or dividend amount, deposit amount, etc.)",
                'fees': "Transaction fees or commissions",
                'account_name': "Name of the brokerage account",
                'instrument_type': "Type of instrument (stock, etf, option, cash)",
                'notes': "Additional notes about the transaction",
                'journal_details': "JSON data for transfers between accounts"
            }
            if field in tooltips:
                label.setToolTip(tooltips[field])

            row_layout.addWidget(label)

            # Dropdown for selecting CSV column
            combo = QComboBox()
            combo.addItem("-- Not Mapped --", None)
            for header in self.csv_headers:
                combo.addItem(header, header)

            # Set mapped column if one was detected
            if field in self.column_mappings:
                mapped_header = self.column_mappings[field]
                idx = self.csv_headers.index(mapped_header) + 1  # +1 for "Not Mapped"
                combo.setCurrentIndex(idx)

            combo.currentIndexChanged.connect(lambda idx, f=field, cb=combo: self._on_mapping_changed(f, cb))
            row_layout.addWidget(combo)

            scroll_layout.addLayout(row_layout)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Preview section
        preview_label = QLabel("Data Preview:")
        preview_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(preview_label)

        # Preview table
        preview_table = QTableView()
        preview_table.setAlternatingRowColors(True)
        preview_model = QStandardItemModel(len(self.preview_data), len(self.csv_headers))

        # Set headers
        for i, header in enumerate(self.csv_headers):
            preview_model.setHorizontalHeaderItem(i, QStandardItem(header))

        # Set data
        for row_idx, row in enumerate(self.preview_data):
            for col_idx, header in enumerate(self.csv_headers):
                item = QStandardItem(str(row.get(header, '')))
                preview_model.setItem(row_idx, col_idx, item)

        preview_table.setModel(preview_model)
        preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_table.setMaximumHeight(200)
        main_layout.addWidget(preview_table)

        # Buttons
        button_layout = QHBoxLayout()

        # Add save/load mapping buttons
        self.save_mapping_button = QPushButton("Save Mapping")
        self.save_mapping_button.clicked.connect(self._save_mapping)
        self.load_mapping_button = QPushButton("Load Mapping")
        self.load_mapping_button.clicked.connect(self._load_mapping)

        button_layout.addWidget(self.save_mapping_button)
        button_layout.addWidget(self.load_mapping_button)
        button_layout.addStretch()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout.addLayout(button_layout)

        # Check initial mappings
        self._validate_mappings()

    def _on_mapping_changed(self, field, combo_box):
        """Handle changes to the column mapping."""
        selected_value = combo_box.currentData()

        if selected_value:
            self.column_mappings[field] = selected_value
        elif field in self.column_mappings:
            del self.column_mappings[field]

        self._validate_mappings()

    def _validate_mappings(self):
        """Check if all required mappings are present."""
        # Check that all required fields are mapped
        missing_required = [f for f in self.required_fields if f not in self.column_mappings]

        # Highlight missing required fields
        labels = self.findChildren(QLabel)
        for label in labels:
            text = label.text().rstrip(':*')
            if text in self.all_possible_fields:
                if text in missing_required:
                    label.setStyleSheet("color: red; font-weight: bold;")
                elif text in self.required_fields:
                    label.setStyleSheet("color: black; font-weight: bold;")
                else:
                    label.setStyleSheet("color: black; font-weight: normal;")

        # Enable/disable OK button based on validation
        self.ok_button.setEnabled(len(missing_required) == 0)

    def get_mappings(self):
        """Return the column mappings."""
        return self.column_mappings

    def _save_mapping(self):
        """Save the current column mapping to a JSON file."""
        if not self.column_mappings:
            QMessageBox.warning(self, "Warning", "No mappings to save.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Mapping", "", "JSON Files (*.json);;All Files (*)"
        )

        if not filepath:
            return

        # Ensure .json extension
        if not filepath.lower().endswith('.json'):
            filepath += '.json'

        try:
            with open(filepath, 'w') as f:
                json.dump(self.column_mappings, f, indent=2)
            QMessageBox.information(self, "Success", "Mapping saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save mapping: {str(e)}")

    def _load_mapping(self):
        """Load a column mapping from a JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Mapping", "", "JSON Files (*.json);;All Files (*)"
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                mappings = json.load(f)

            # Validate mappings
            if not isinstance(mappings, dict):
                raise ValueError("Invalid mapping format")

            # Check that mapped columns exist in the CSV
            missing_cols = [col for col in mappings.values() if col not in self.csv_headers]
            if missing_cols:
                QMessageBox.warning(
                    self, "Warning",
                    f"Some mapped columns don't exist in this CSV: {', '.join(missing_cols)}\n"
                    "These mappings will be ignored."
                )

            # Update mappings, ignoring those with missing columns
            valid_mappings = {k: v for k, v in mappings.items() if v in self.csv_headers}
            self.column_mappings = valid_mappings

            # Update UI to reflect loaded mappings
            self._update_ui_from_mappings()

            QMessageBox.information(self, "Success", "Mapping loaded successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load mapping: {str(e)}")

    def _update_ui_from_mappings(self):
        """Update the UI dropdowns to reflect the current mappings."""
        # Find all QComboBox widgets in our scroll area
        combo_boxes = self.findChildren(QComboBox)

        for combo in combo_boxes:
            # Get the field name from the parent layout's first widget (label)
            parent_layout = combo.parent().layout()
            if parent_layout and parent_layout.count() > 0:
                label_widget = parent_layout.itemAt(0).widget()
                if isinstance(label_widget, QLabel):
                    # Extract field name from label text (remove trailing colon and asterisk)
                    field_text = label_widget.text().rstrip(':*')

                    # If this field is in our mappings, update the combo box
                    if field_text in self.column_mappings:
                        mapped_col = self.column_mappings[field_text]
                        # Find the index of this column in the combo box
                        for i in range(combo.count()):
                            if combo.itemData(i) == mapped_col:
                                combo.setCurrentIndex(i)
                                break

        # Validate the mappings after updating
        self._validate_mappings()

    def _detect_special_formats(self):
        """Detect special CSV formats from common brokers."""
        # Check for Fidelity format
        fidelity_headers = ['Run Date', 'Action', 'Symbol', 'Description', 'Quantity', 'Price ($)', 'Commission ($)', 'Fees ($)', 'Accrued Interest ($)', 'Amount ($)', 'Settlement Date']
        if all(h in self.csv_headers for h in ['Run Date', 'Action', 'Symbol', 'Amount ($)']):
            # This looks like a Fidelity export
            self.column_mappings.update({
                'date': 'Run Date',
                'action': 'Action',
                'symbol': 'Symbol',
                'amount': 'Amount ($)',
                'quantity': 'Quantity',
                'price': 'Price ($)',
                'fees': 'Fees ($)'
            })
            # Try to detect account name from the filename or data
            if not self.column_mappings.get('account_name'):
                self.column_mappings['account_name'] = 'Description'  # Use Description as fallback

            # Add instrument_type default if not present
            if 'instrument_type' not in self.column_mappings:
                # Will default to stock in the importer
                pass

        # Check for TD Ameritrade / Charles Schwab format
        if all(h in self.csv_headers for h in ['Date', 'Symbol', 'Description', 'Quantity', 'Price', 'Amount']):
            # This looks like a TD Ameritrade or Schwab export
            self.column_mappings.update({
                'date': 'Date',
                'symbol': 'Symbol',
                'quantity': 'Quantity',
                'price': 'Price',
                'amount': 'Amount'
            })
            # Try to detect action from Description field
            self.column_mappings['action'] = 'Description'

            # Add account_name default if not present
            if 'account_name' not in self.column_mappings:
                # Will need manual mapping
                pass

        # Check for Robinhood format (buy/sell transactions)
        if all(h in self.csv_headers for h in ['Date', 'Symbol', 'Action', 'Quantity', 'Price', 'Fees & Comm', 'Amount']):
            # This looks like a Robinhood export
            self.column_mappings.update({
                'date': 'Date',
                'symbol': 'Symbol',
                'action': 'Action',
                'quantity': 'Quantity',
                'price': 'Price',
                'fees': 'Fees & Comm',
                'amount': 'Amount'
            })
            # Add account_name default if not present
            if 'account_name' not in self.column_mappings:
                # Will need manual mapping
                pass

        # Check for AAPL Lot Details format (example 3)
        if all(h in self.csv_headers for h in ['Open Date', 'Quantity', 'Price', 'Cost/Share', 'Market Value', 'Holding Period']):
            # This looks like a lot details export
            self.column_mappings.update({
                'date': 'Open Date',
                'quantity': 'Quantity',
                'price': 'Cost/Share',  # Use cost basis as price
                'amount': 'Market Value'
            })
            # Since this is position data not transactions, we need special handling
            # Default to 'buy' action
            if 'action' not in self.column_mappings:
                # Will need manual mapping
                pass

            # Extract symbol from the file header or first row data
            # For this type of export, the symbol is often in the header text
            if 'symbol' not in self.column_mappings:
                # Check the first few rows for symbol information
                for row in self.preview_data:
                    for header, value in row.items():
                        if isinstance(value, str) and value.strip().isalpha() and 1 <= len(value.strip()) <= 5:
                            self.column_mappings['symbol'] = header
                            break

    def _detect_column_patterns(self):
        """Attempt to detect common patterns in CSV headers and map them to application fields."""
        # Mapping of common CSV column names to our application fields
        common_patterns = {
            'date': ['date', 'transaction date', 'trade date', 'activity date', 'run date', 'open date'],
            'symbol': ['symbol', 'ticker', 'security', 'security symbol'],
            'action': ['action', 'activity', 'transaction type', 'type', 'description'],
            'quantity': ['quantity', 'qty', 'shares', 'amount'],
            'price': ['price', 'price ($)', 'price/share', 'share price'],
            'amount': ['amount', 'amount ($)', 'value', 'total', 'net amount', 'proceeds', 'total amount'],
            'fees': ['fees', 'commission', 'fees & comm', 'commission ($)', 'fees ($)'],
            'account_name': ['account', 'account name', 'acct'],
            'instrument_type': ['instrument type', 'security type', 'asset class', 'type'],
            'notes': ['notes', 'description', 'comments', 'memo', 'memo_desc'],
        }

        # Check for description-like fields that could contain option information
        description_fields = ['description', 'transaction description', 'security description', 'details']
        notes_mapped = False
        for header in self.csv_headers:
            if any(pattern in header.lower() for pattern in description_fields):
                if 'notes' not in self.column_mappings:
                    self.column_mappings['notes'] = header
                    notes_mapped = True
                    break

        # For each CSV header, check if it matches any of our patterns
        for header in self.csv_headers:
            header_lower = header.lower()

            # Skip headers that look like metadata or instructions
            if header_lower.startswith('"') or len(header_lower) > 50:
                continue

            # Try to match with our application fields
            for app_field, patterns in common_patterns.items():
                if any(pattern in header_lower for pattern in patterns):
                    # Check if we already have a mapping for this field
                    if app_field not in self.column_mappings:
                        self.column_mappings[app_field] = header
                        break

        # Additional detection for specific file formats based on preview data
        # Try to determine what type of transactions these are and make intelligent guesses

        # If we have action column but need to map symbol
        if 'action' in self.column_mappings and 'symbol' not in self.column_mappings:
            action_col = self.column_mappings['action']

            # Look for a column that might contain symbols
            for header in self.csv_headers:
                # Skip already mapped columns
                if header in self.column_mappings.values():
                    continue

                # Check preview data for this column
                values = [row.get(header, '').strip().upper() for row in self.preview_data]
                # Look for typical stock symbols (all caps, 1-5 letters)
                if any(v and v.isalpha() and 1 <= len(v) <= 5 for v in values):
                    self.column_mappings['symbol'] = header
                    break

        # If we have detected date column, try to intelligently map action
        if 'date' in self.column_mappings and 'action' not in self.column_mappings:
            # Look for columns with values like "BUY", "SELL", "DIVIDEND", etc.
            for header in self.csv_headers:
                # Skip already mapped columns
                if header in self.column_mappings.values():
                    continue

                # Check preview data for this column
                values = [row.get(header, '').lower() for row in self.preview_data]
                # Look for common transaction types
                common_actions = ['buy', 'sell', 'dividend', 'deposit', 'withdrawal']
                if any(any(action in v for action in common_actions) for v in values):
                    self.column_mappings['action'] = header
                    break

        # Look for option data in preview
        found_options = False

        # Check mapped symbol column for option indicators
        if 'symbol' in self.column_mappings:
            symbol_col = self.column_mappings['symbol']
            symbols = [row.get(symbol_col, '') for row in self.preview_data if row.get(symbol_col, '')]

            # Look for option patterns in symbols
            for symbol in symbols:
                if ' ' in symbol and any(x in symbol.upper() for x in ['CALL', 'PUT', 'C', 'P']) and re.search(r'[0-9]', symbol):
                    found_options = True
                    break

        # Check description/notes column for option indicators if we have one
        if 'notes' in self.column_mappings and not found_options:
            notes_col = self.column_mappings['notes']
            descriptions = [row.get(notes_col, '') for row in self.preview_data if row.get(notes_col, '')]

            # Look for option-related terms
            option_terms = ['call', 'put', 'option', 'strike', 'exp', 'expiry', 'expiration']
            for desc in descriptions:
                desc_lower = desc.lower()
                if any(term in desc_lower for term in option_terms) and re.search(r'\$[0-9]+|[0-9]{1,2}/[0-9]{1,2}', desc):
                    found_options = True
                    break

        # If we found options and instrument_type isn't mapped, map to a default field
        if found_options and 'instrument_type' not in self.column_mappings:
            # We'll use this as a signal to automatically detect options
            # The actual parsing is done in import_transactions_from_csv
            logger.info("Detected options data in the CSV. Will auto-detect options.")

        # Special case detection for common broker formats
        self._detect_special_formats()
