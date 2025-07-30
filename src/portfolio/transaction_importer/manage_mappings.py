import sys
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                              QTableWidgetItem, QPushButton, QComboBox, QLabel, QLineEdit,
                              QHeaderView, QMessageBox)
from PySide6.QtCore import Qt

from portfolio.models import TransactionType
from portfolio.transaction_importer.utils import transaction_type_mapper


class ManageMappingsDialog(QDialog):
    """Dialog for managing transaction type mappings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Transaction Type Mappings")
        self.resize(800, 600)
        self._setup_ui()
        self._load_mappings()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Manage transaction type mappings for brokers. These mappings help automatically detect "
            "transaction types when importing CSV files. For transfers, the direction (in/out) will "
            "be determined automatically based on the quantity (positive = in, negative = out)."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Broker selector
        broker_layout = QHBoxLayout()
        broker_layout.addWidget(QLabel("Broker:"))
        self.broker_combo = QComboBox()
        self.broker_combo.currentIndexChanged.connect(self._on_broker_changed)
        broker_layout.addWidget(self.broker_combo)
        layout.addLayout(broker_layout)

        # Table for mappings
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Action Text", "Transaction Type"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Add new mapping controls
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("New Action Text:"))
        self.new_action_text = QLineEdit()
        add_layout.addWidget(self.new_action_text)

        add_layout.addWidget(QLabel("Transaction Type:"))
        self.new_transaction_type = QComboBox()
        # Add all possible transaction types
        for ttype in TransactionType:
            self.new_transaction_type.addItem(ttype.value)
        add_layout.addWidget(self.new_transaction_type)

        self.add_button = QPushButton("Add Mapping")
        self.add_button.clicked.connect(self._add_mapping)
        add_layout.addWidget(self.add_button)

        layout.addLayout(add_layout)

        # Buttons at bottom
        button_layout = QHBoxLayout()
        self.new_broker_button = QPushButton("Add New Broker")
        self.new_broker_button.clicked.connect(self._add_new_broker)
        button_layout.addWidget(self.new_broker_button)

        button_layout.addStretch()

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_selected)
        button_layout.addWidget(self.delete_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    def _load_mappings(self):
        """Load all broker mappings and populate the UI."""
        # Clear and refill broker combo
        self.broker_combo.clear()
        for broker in sorted(transaction_type_mapper.mappings.keys()):
            self.broker_combo.addItem(broker)

        # Select first broker if available
        if self.broker_combo.count() > 0:
            self.broker_combo.setCurrentIndex(0)
            self._on_broker_changed(0)

    def _on_broker_changed(self, index):
        """Load mappings for the selected broker."""
        if index < 0:
            return

        broker = self.broker_combo.currentText()
        self._load_broker_mappings(broker)

    def _load_broker_mappings(self, broker):
        """Load mappings for a specific broker into the table."""
        self.table.setRowCount(0)  # Clear table

        if broker not in transaction_type_mapper.mappings:
            return

        mappings = transaction_type_mapper.mappings[broker]
        self.table.setRowCount(len(mappings))

        for i, (action_text, ttype) in enumerate(mappings.items()):
            # Action text
            action_item = QTableWidgetItem(action_text)
            self.table.setItem(i, 0, action_item)

            # Transaction type dropdown
            type_combo = QComboBox()
            for tt in TransactionType:
                type_combo.addItem(tt.value)

            # Set current transaction type
            try:
                index = type_combo.findText(ttype)
                if index >= 0:
                    type_combo.setCurrentIndex(index)
            except:
                pass

            # Connect change signal
            type_combo.currentIndexChanged.connect(
                lambda idx, row=i, combo=type_combo: self._on_type_changed(row, combo)
            )
            self.table.setCellWidget(i, 1, type_combo)

    def _on_type_changed(self, row, combo):
        """Handle transaction type changes in the table."""
        broker = self.broker_combo.currentText()
        action_text = self.table.item(row, 0).text()
        new_type = combo.currentText()

        # Update the mapping
        if broker in transaction_type_mapper.mappings:
            transaction_type_mapper.mappings[broker][action_text] = new_type
            transaction_type_mapper._save_mappings()

    def _add_mapping(self):
        """Add a new mapping for the current broker."""
        broker = self.broker_combo.currentText()
        action_text = self.new_action_text.text().strip().lower()
        ttype = self.new_transaction_type.currentText()

        if not action_text:
            QMessageBox.warning(self, "Warning", "Please enter action text")
            return

        # Add the mapping
        transaction_type_mapper.add_mapping(broker, action_text, ttype)

        # Reload the table
        self._load_broker_mappings(broker)

        # Clear the input field
        self.new_action_text.clear()

    def _delete_selected(self):
        """Delete the selected mapping."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        broker = self.broker_combo.currentText()
        for row in sorted(selected_rows, reverse=True):
            action_text = self.table.item(row, 0).text()
            if broker in transaction_type_mapper.mappings and action_text in transaction_type_mapper.mappings[broker]:
                del transaction_type_mapper.mappings[broker][action_text]

        # Save changes and reload
        transaction_type_mapper._save_mappings()
        self._load_broker_mappings(broker)

    def _add_new_broker(self):
        """Add a new broker category."""
        # Simple dialog to get broker name
        from PySide6.QtWidgets import QInputDialog
        broker, ok = QInputDialog.getText(self, "Add Broker", "Enter broker name:")

        if ok and broker.strip():
            broker = broker.strip().lower()
            if broker not in transaction_type_mapper.mappings:
                transaction_type_mapper.mappings[broker] = {}
                transaction_type_mapper._save_mappings()
                self._load_mappings()
                # Select the new broker
                index = self.broker_combo.findText(broker)
                if index >= 0:
                    self.broker_combo.setCurrentIndex(index)
            else:
                QMessageBox.information(self, "Info", f"Broker '{broker}' already exists")


def main():
    """Run the mapping manager as a standalone application."""
    app = QApplication(sys.argv)
    dialog = ManageMappingsDialog()
    dialog.exec()


if __name__ == "__main__":
    main()
