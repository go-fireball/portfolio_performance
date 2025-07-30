import json
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtGui import QColor

from portfolio.models import TransactionType, InstrumentType
from portfolio.transaction_importer.parsers import calculate_amount, parse_date


class TransactionTableModel(QAbstractTableModel):
    """Model for transaction data displayed in QTableView."""
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self.error_color = QColor(255, 200, 200)  # Light red for error rows

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        column_name = self._headers[col]

        # Set foreground color to ensure text is visible against background
        if role == Qt.ItemDataRole.ForegroundRole:
            # Use black text for all cells
            return Qt.black

        if role == Qt.ItemDataRole.BackgroundRole and self._data[row].get('errors'):
            return self.error_color

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            # Handle special display formatting
            value = self._data[row].get(column_name)

            if column_name == 'transaction_date' and isinstance(value, date):
                # Format date for display role, return date object for edit role
                if role == Qt.ItemDataRole.DisplayRole:
                    return value.strftime('%Y-%m-%d')  # Format date as string for display
                return value
            elif column_name == 'transaction_type' and isinstance(value, TransactionType):
                return value.value
            elif column_name == 'instrument_type' and isinstance(value, InstrumentType):
                return value.value
            elif column_name in ('quantity', 'price', 'fees', 'amount') and isinstance(value, Decimal):
                # Format decimal values for display
                if role == Qt.ItemDataRole.DisplayRole:
                    return str(value)  # Ensure string conversion for display
                return value
            elif column_name == 'journal_details' and isinstance(value, dict):
                return value if role == Qt.ItemDataRole.EditRole else json.dumps(value)
            elif column_name == 'errors':
                return "\n".join(value) if value else ""

            return value

        return None

    def setData(self, index, value, role):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row, col = index.row(), index.column()
        column_name = self._headers[col]

        # Validate and convert based on column type
        if column_name == 'transaction_date':
            if isinstance(value, date):
                self._data[row][column_name] = value
            else:
                parsed_date = parse_date(str(value))
                if parsed_date:
                    self._data[row][column_name] = parsed_date
                else:
                    return False

        elif column_name == 'transaction_type':
            try:
                if isinstance(value, str):
                    self._data[row][column_name] = TransactionType(value)
                else:
                    self._data[row][column_name] = value
            except ValueError:
                self._data[row]['transaction_type_str'] = value
                self._add_error(row, f"Invalid transaction type: {value}")
                return False

        elif column_name == 'instrument_type':
            try:
                if isinstance(value, str):
                    self._data[row][column_name] = InstrumentType(value)
                else:
                    self._data[row][column_name] = value
            except ValueError:
                self._data[row]['instrument_type_str'] = value
                self._add_error(row, f"Invalid instrument type: {value}")
                return False

        elif column_name in ('quantity', 'price', 'fees', 'amount'):
            try:
                if value is None or value == "":
                    self._data[row][column_name] = None
                elif isinstance(value, (Decimal, int, float)):
                    self._data[row][column_name] = Decimal(str(value))
                else:
                    self._data[row][column_name] = Decimal(value)
            except (InvalidOperation, ValueError):
                self._add_error(row, f"Invalid number for {column_name}: {value}")
                return False

        elif column_name == 'journal_details':
            if isinstance(value, dict):
                self._data[row][column_name] = value
            elif value is None or value == "":
                self._data[row][column_name] = None
            else:
                try:
                    self._data[row][column_name] = json.loads(value)
                except json.JSONDecodeError:
                    self._data[row]['journal_details_str'] = value
                    self._add_error(row, f"Invalid JSON: {value}")
                    return False

        else:  # Handle string columns (symbol, account_name, notes)
            self._data[row][column_name] = value

        # Recalculate amount if quantity, price, or fees changed
        if column_name in ('quantity', 'price', 'fees') and 'transaction_type' in self._data[row]:
            ttype = self._data[row]['transaction_type']
            if ttype in (TransactionType.BUY, TransactionType.SELL):
                calculated_amount = calculate_amount(
                    self._data[row].get('quantity'),
                    self._data[row].get('price'),
                    self._data[row].get('fees'),
                    ttype.value
                )
                if calculated_amount is not None:
                    self._data[row]['amount'] = calculated_amount

        # Re-validate the row
        self._validate_row(row)

        # Emit dataChanged signal for the whole row since validation might affect multiple columns
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, self.columnCount() - 1)
        )

        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def _add_error(self, row, error_message):
        """Add an error message to a row."""
        if 'errors' not in self._data[row]:
            self._data[row]['errors'] = []

        if error_message not in self._data[row]['errors']:
            self._data[row]['errors'].append(error_message)

    def _remove_error(self, row, error_message):
        """Remove an error message from a row."""
        if 'errors' in self._data[row] and error_message in self._data[row]['errors']:
            self._data[row]['errors'].remove(error_message)
            if not self._data[row]['errors']:
                del self._data[row]['errors']

    def _validate_row(self, row):
        """Validate all fields in a row and update error messages."""
        data = self._data[row]

        # Clear existing errors
        data['errors'] = []

        # Check required fields based on transaction type
        if 'transaction_date' not in data or not data['transaction_date']:
            self._add_error(row, "Date is required")

        if 'transaction_type' not in data or not data['transaction_type']:
            self._add_error(row, "Transaction type is required")

        if 'account_name' not in data or not data['account_name'] or data['account_name'].strip() == '':
            self._add_error(row, "Account name is required")
        else:
            # Explicitly remove any account-related errors when account is valid
            errors_to_remove = []
            for error in data.get('errors', []):
                if 'account name' in error.lower():
                    errors_to_remove.append(error)

            for error in errors_to_remove:
                self._remove_error(row, error)

        if 'transaction_type' in data:
            ttype = data['transaction_type']

            # Symbol requirements
            symbol_required = ttype in [
                TransactionType.BUY, TransactionType.SELL, 
                TransactionType.DIVIDEND, TransactionType.SPLIT
            ]

            if symbol_required:
                if 'symbol' not in data or not data['symbol']:
                    self._add_error(row, "Symbol is required for this transaction type")

                if 'instrument_type' not in data or not data['instrument_type']:
                    self._add_error(row, "Instrument type is required when symbol is provided")

            # Validate fields by transaction type
            if ttype in [TransactionType.BUY, TransactionType.SELL]:
                if 'quantity' not in data or data.get('quantity') is None:
                    self._add_error(row, "Quantity is required for buy/sell transactions")

                if 'price' not in data or data.get('price') is None:
                    self._add_error(row, "Price is required for buy/sell transactions")

            # Amount validation
            if 'amount' not in data or data.get('amount') is None:
                self._add_error(row, "Amount is required for all transactions")

        return len(data.get('errors', [])) == 0

    def hasErrors(self):
        """Check if any rows have validation errors."""
        return any(row.get('errors') for row in self._data)

    def getTransactions(self):
        """Get transaction data for saving."""
        return self._data
