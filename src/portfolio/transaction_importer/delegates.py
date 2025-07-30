import json
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QStyledItemDelegate, QDateEdit, QComboBox, QLineEdit)


class DateDelegate(QStyledItemDelegate):
    """Custom delegate for date editing."""
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value and isinstance(value, date):
            editor.setDate(QDate(value.year, value.month, value.day))
        else:
            editor.setDate(QDate.currentDate())

    def setModelData(self, editor, model, index):
        value = editor.date().toPython()
        model.setData(index, value, Qt.EditRole)

    def displayText(self, value, locale):
        """Format the display text for date values."""
        if value is None or value == '':
            return ''
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return str(value)


class ComboBoxDelegate(QStyledItemDelegate):
    """Custom delegate for enum dropdowns."""
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.options)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        try:
            idx = self.options.index(value) if value else 0
            editor.setCurrentIndex(idx)
        except ValueError:
            editor.setCurrentIndex(0)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)


class DecimalDelegate(QStyledItemDelegate):
    """Custom delegate for Decimal values."""
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(self.parent().decimal_validator)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value is not None:
            editor.setText(str(value))
        else:
            editor.setText("")

    def setModelData(self, editor, model, index):
        try:
            value = Decimal(editor.text()) if editor.text() else None
            model.setData(index, value, Qt.EditRole)
        except InvalidOperation:
            # Invalid decimal format, don't update the model
            pass

    def displayText(self, value, locale):
        """Format the display text for decimal values."""
        if value is None or value == '':
            return ''
        if isinstance(value, Decimal):
            # Format with appropriate number of decimal places
            if value == int(value):
                return str(int(value))  # Show whole numbers without decimal point
            return str(value)  # Use decimal's string representation
        return str(value)


class JSONDelegate(QStyledItemDelegate):
    """Custom delegate for JSON editing."""
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value:
            if isinstance(value, dict):
                editor.setText(json.dumps(value))
            else:
                editor.setText(str(value))
        else:
            editor.setText("")

    def setModelData(self, editor, model, index):
        text = editor.text()
        if not text:
            model.setData(index, None, Qt.EditRole)
            return

        try:
            value = json.loads(text)
            model.setData(index, value, Qt.EditRole)
        except json.JSONDecodeError:
            # Store as string if not valid JSON
            model.setData(index, text, Qt.EditRole)
