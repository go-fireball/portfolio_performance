from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from portfolio.database import SessionLocal
from portfolio.models import Account, Symbol, Transaction, InstrumentType, OptionType
from portfolio.transaction_importer.utils import logger


def get_account_by_name(db: Session, account_name: str) -> Optional[Account]:
    """Find account by name."""
    return db.query(Account).filter(Account.name == account_name).first()


def get_or_create_symbol(db: Session, ticker: str, instrument_type: InstrumentType, 
                       option_type=None, expiration_date=None, 
                       strike_price=None) -> Symbol:
    """Find or create a symbol record."""
    # Handle missing data for options
    if instrument_type == InstrumentType.OPTION:
        if not ticker:
            raise ValueError("Ticker is required for option symbols")

        # If option_type is a string, convert to enum
        if isinstance(option_type, str):
            try:
                option_type = OptionType(option_type.lower())
            except ValueError:
                # Default to CALL if can't determine
                option_type = OptionType.CALL

        # If option_type is not set, default to CALL
        if not option_type:
            option_type = OptionType.CALL

        # If strike_price is a string, convert to Decimal
        if isinstance(strike_price, str):
            try:
                strike_price = Decimal(strike_price.replace('$', ''))
            except (InvalidOperation, ValueError):
                raise ValueError(f"Invalid strike price: {strike_price}")

    # Build the query
    query = db.query(Symbol).filter(
        Symbol.ticker == ticker,
        Symbol.instrument_type == instrument_type
    )

    # Add option-specific filters if applicable
    if instrument_type == InstrumentType.OPTION:
        query = query.filter(
            Symbol.option_type == option_type
        )

        # Only filter on date and strike if they're provided
        if expiration_date:
            query = query.filter(Symbol.expiration_date == expiration_date)

        if strike_price:
            query = query.filter(Symbol.strike_price == strike_price)

    symbol = query.first()

    if not symbol:
        # Create new symbol
        symbol = Symbol(
            ticker=ticker,
            instrument_type=instrument_type,
            option_type=option_type,
            expiration_date=expiration_date,
            strike_price=strike_price
        )
        db.add(symbol)
        db.flush()  # Generate ID without committing

    return symbol


def save_transactions(transactions: List[Dict[str, Any]]) -> bool:
    """Save validated transactions to the database."""
    db = SessionLocal()
    try:
        for transaction in transactions:
            # Skip transactions with errors
            if transaction.get('errors'):
                continue

            # Resolve account_id from account_name
            account = get_account_by_name(db, transaction['account_name'])
            if not account:
                raise ValueError(f"Account not found: {transaction['account_name']}")

            # Resolve or create symbol if applicable
            symbol_id = None
            if transaction.get('symbol'):
                # Determine instrument type
                instrument_type = transaction.get('instrument_type', InstrumentType.STOCK)

                # Set to OPTION if option details are present, regardless of what was specified
                if transaction.get('option_type') or transaction.get('expiration_date') or transaction.get('strike_price'):
                    instrument_type = InstrumentType.OPTION

                try:
                    symbol = get_or_create_symbol(
                        db,
                        transaction['symbol'],
                        instrument_type,
                        # Add option details if present
                        option_type=transaction.get('option_type'),
                        expiration_date=transaction.get('expiration_date'),
                        strike_price=transaction.get('strike_price')
                    )
                    symbol_id = symbol.id
                except ValueError as e:
                    # If symbol creation fails, log the error and skip this transaction
                    logger.error(f"Error creating symbol: {str(e)}")
                    continue

            # Create transaction record
            db_transaction = Transaction(
                account_id=account.id,
                symbol_id=symbol_id,
                transaction_type=transaction['transaction_type'],
                transaction_date=transaction['transaction_date'],
                quantity=transaction.get('quantity'),
                price=transaction.get('price'),
                amount=transaction['amount'],
                fees=transaction.get('fees') or Decimal('0'),
                notes=transaction.get('notes')
            )

            # Handle related transaction for transfers
            if transaction.get('related_transaction_id'):
                db_transaction.related_transaction_id = transaction['related_transaction_id']

            db.add(db_transaction)

        # Commit all transactions in a single transaction
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving transactions: {str(e)}")
        raise

    finally:
        db.close()
