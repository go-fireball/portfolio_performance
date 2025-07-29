import sys
from PySide6.QtWidgets import QApplication
from portfolio.transaction_importer.review_window import TransactionReviewWindow


def main():
    app = QApplication(sys.argv)
    window = TransactionReviewWindow()
    window.show()
    sys.exit(app.exec())
