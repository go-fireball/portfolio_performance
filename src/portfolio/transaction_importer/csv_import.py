import csv
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from portfolio.models import InstrumentType, TransactionType
from portfolio.transaction_importer.parsers import (
    parse_date, parse_decimal, parse_json, parse_option_details,
    standardize_option_transaction_type, calculate_amount
)


def import_transactions_from_csv(filepath: str, column_mappings: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Parse CSV file into a list of transaction dictionaries.

    Args:
        filepath: Path to the CSV file
        column_mappings: Optional dictionary mapping application fields to CSV column names
    """
    try:
        # First load CSV to determine headers if mappings not provided
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames if reader.fieldnames else []

            # If no column mappings provided, return first few rows for preview
            if column_mappings is None:
                preview_data = []
                for i, row in enumerate(reader):
                    if i >= 10:  # Limit to 10 rows for preview
                        break
                    preview_data.append(dict(row))
                return headers, preview_data

        # Process with provided column mappings
        transactions = []
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            # Check that all mapped columns exist in the CSV
            for app_field, csv_col in column_mappings.items():
                if csv_col not in headers:
                    raise ValueError(f"Mapped column '{csv_col}' not found in CSV headers")

            # Process each row
            for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                # Create a new transaction with original data and placeholders for errors
                transaction = {
                    'row_num': row_num,
                    'errors': [],
                    'warnings': [],
                    'original': dict(row),
                }

                # Process date field
                date_column = column_mappings.get('date')
                if date_column and date_column in row:
                    trans_date = parse_date(row[date_column])
                    if trans_date:
                        transaction['transaction_date'] = trans_date
                    else:
                        transaction['errors'].append(f"Invalid date format: {row[date_column]}")
                else:
                    transaction['errors'].append("Date field is required but not mapped")

                # Process action/transaction type
                action_column = column_mappings.get('action')
                if action_column and action_column in row:
                    original_action = row[action_column].strip()
                    action = original_action.lower()

                    # Determine if this is an option transaction based on the action text
                    # or if we've already detected option details
                    is_option_transaction = False
                    option_indicators = ['call', 'put', 'option', 'bto', 'sto', 'btc', 'stc', 'exercise', 'assign']

                    if any(indicator in action for indicator in option_indicators) or transaction.get('instrument_type') == InstrumentType.OPTION:
                        is_option_transaction = True
                        transaction['instrument_type'] = InstrumentType.OPTION

                    # For expired options, set price and amount to zero
                    if 'expir' in action or 'worthless' in action:
                        transaction['price'] = Decimal('0')
                        transaction['amount'] = Decimal('0')

                    # Process quantity early if needed for transaction type determination
                    quantity_column = column_mappings.get('quantity')
                    if quantity_column and quantity_column in row:
                        transaction['quantity'] = parse_decimal(row[quantity_column])

                    # Extract broker from account name if available
                    broker = None
                    account_column = column_mappings.get('account_name')
                    if account_column and account_column in row and row[account_column].strip():
                        # Try to extract broker from account name (common format: "Account Name (Broker)")
                        account_name = row[account_column].strip()
                        if '(' in account_name and ')' in account_name:
                            broker = account_name.split('(')[-1].split(')')[0]

                    # Use the standardization function to get the correct transaction type
                    try:
                        transaction['transaction_type'] = standardize_option_transaction_type(
                            action, 
                            is_option_transaction,
                            transaction.get('quantity'),
                            broker
                        )
                    except Exception as e:
                        # If standardization fails, log the error and store the original action
                        transaction['errors'].append(f"Could not determine transaction type: {original_action}")
                        transaction['transaction_type_str'] = original_action
                else:
                    transaction['errors'].append("Action field is required but not mapped")

                # Process symbol and description to check for options
                symbol_column = column_mappings.get('symbol')
                description_column = column_mappings.get('notes')

                symbol = ""
                description = ""

                if symbol_column and symbol_column in row:
                    symbol = row[symbol_column].strip().upper()

                if description_column and description_column in row:
                    description = row[description_column].strip()

                # Store the original symbol
                transaction['symbol'] = symbol

                # Try to parse option details
                if symbol or description:
                    option_details = parse_option_details(symbol, description)

                    # If this is an option, update the transaction data
                    if option_details['is_option']:
                        # Set instrument type to OPTION
                        transaction['instrument_type'] = InstrumentType.OPTION

                        # Set option-specific fields
                        transaction['symbol'] = option_details['ticker']
                        transaction['option_type'] = option_details['option_type']
                        transaction['expiration_date'] = option_details['expiration_date']
                        transaction['strike_price'] = option_details['strike_price']

                        # Store original symbol and description for reference
                        transaction['original_symbol'] = symbol
                        if description:
                            transaction['notes'] = description

                # If symbol is still missing for relevant transaction types, add a warning
                if not transaction.get('symbol') and 'transaction_type' in transaction:
                    ttype = transaction['transaction_type']
                    if ttype not in [TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.INTEREST]:
                        transaction['warnings'].append("Symbol is recommended for this transaction type but not mapped")

                # Process instrument type
                instr_type_column = column_mappings.get('instrument_type')
                if instr_type_column and instr_type_column in row:
                    instr_type = row[instr_type_column].lower().strip()
                    if instr_type:
                        try:
                            transaction['instrument_type'] = InstrumentType(instr_type)
                        except ValueError:
                            transaction['errors'].append(f"Invalid instrument type: {instr_type}")
                            transaction['instrument_type_str'] = instr_type
                elif transaction.get('symbol'):  # Only require instrument type if symbol is provided
                    # For symbols without explicit instrument type, default to stock
                    transaction['instrument_type'] = InstrumentType.STOCK
                    transaction['warnings'].append("Instrument type not provided, defaulting to 'stock'")

                # Process account name
                account_column = column_mappings.get('account_name')
                if account_column and account_column in row:
                    transaction['account_name'] = row[account_column].strip()
                    if not transaction['account_name']:
                        transaction['errors'].append("Account name is empty")
                else:
                    transaction['errors'].append("Account name is required but not mapped")

                # Skip quantity parsing as it's already done above for transaction type detection
                # Just ensure it's correctly set
                if 'quantity' not in transaction and column_mappings.get('quantity') in row:
                    quantity_column = column_mappings.get('quantity')
                    transaction['quantity'] = parse_decimal(row[quantity_column])

                price_column = column_mappings.get('price')
                if price_column and price_column in row:
                    transaction['price'] = parse_decimal(row[price_column])

                fees_column = column_mappings.get('fees')
                if fees_column and fees_column in row:
                    transaction['fees'] = parse_decimal(row[fees_column] or '0')
                else:
                    # Default fees to 0 if not provided
                    transaction['fees'] = Decimal('0')

                # Process journal details (optional JSON)
                journal_column = column_mappings.get('journal_details')
                if journal_column and journal_column in row and row[journal_column].strip():
                    journal_details = parse_json(row[journal_column])
                    if journal_details:
                        transaction['journal_details'] = journal_details
                    else:
                        transaction['errors'].append(f"Invalid JSON in journal_details: {row[journal_column]}")
                        transaction['journal_details_str'] = row[journal_column]

                # Process notes
                notes_column = column_mappings.get('notes')
                if notes_column and notes_column in row:
                    transaction['notes'] = row[notes_column].strip()

                # Process amount or calculate it
                amount_column = column_mappings.get('amount')
                if amount_column and amount_column in row:
                    explicit_amount = parse_decimal(row[amount_column])
                    if explicit_amount is not None:
                        transaction['amount'] = explicit_amount

                # If amount not explicitly provided, try to calculate
                if 'amount' not in transaction and 'transaction_type' in transaction:
                    action = transaction['transaction_type'].value
                    # Try to calculate amount from quantity, price, and fees
                    calculated_amount = calculate_amount(
                        transaction.get('quantity'), 
                        transaction.get('price'),
                        transaction.get('fees'),
                        action
                    )
                    if calculated_amount is not None:
                        transaction['amount'] = calculated_amount

                # Validate required fields based on transaction type
                if 'transaction_type' in transaction:
                    ttype = transaction['transaction_type']
                    if ttype in [TransactionType.BUY, TransactionType.SELL]:
                        if transaction.get('quantity') is None:
                            transaction['errors'].append("Quantity is required for buy/sell transactions")
                        if transaction.get('price') is None:
                            transaction['errors'].append("Price is required for buy/sell transactions")
                    elif ttype in [TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.FEE]:
                        if transaction.get('amount') is None:
                            transaction['errors'].append("Amount is required for cash transactions")

                    # Check for missing amount across all transaction types
                    if 'amount' not in transaction:
                        transaction['errors'].append("Cannot determine transaction amount")

                transactions.append(transaction)

            return transactions

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")
