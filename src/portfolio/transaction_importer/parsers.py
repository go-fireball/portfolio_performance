import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, List

from portfolio.models import OptionType, TransactionType


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string in various formats.

    If date string contains 'as of' (e.g., "07/22/2024 as of 07/19/2024"),
    use the 'as of' date instead of the main date.
    """
    # Check for 'as of' pattern
    as_of_match = re.search(r'as of ([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})', date_str, re.IGNORECASE)
    if as_of_match:
        # Use the 'as of' date instead
        date_str = as_of_match.group(1)

    # Try standard formats
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d-%m-%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # If nothing worked, try more aggressive cleaning and parsing
    try:
        # Remove any text and keep only the first date-like pattern
        date_pattern = re.search(r'([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})', date_str)
        if date_pattern:
            clean_date_str = date_pattern.group(1)
            for fmt in formats:
                try:
                    return datetime.strptime(clean_date_str, fmt).date()
                except ValueError:
                    continue
    except Exception:
        pass

    return None


def standardize_option_transaction_type(action_str: str, is_option: bool = False, quantity: Optional[Decimal] = None, broker: Optional[str] = None) -> TransactionType:
    """Standardize option transaction types from various formats.

    Maps various broker-specific formats to our standard TransactionType enum values.
    Uses the transaction_type_mapper if available for customizable mappings.

    Args:
        action_str: The action string from the CSV file
        is_option: Whether this is known to be an option transaction
        quantity: Optional quantity to help determine transfer direction
        broker: Optional broker name for broker-specific mappings

    Returns:
        The standardized TransactionType enum value

    Examples:
        - "Buy to Open" → TransactionType.BUY_TO_OPEN
        - "STO" → TransactionType.SELL_TO_OPEN
        - "BTC" → TransactionType.BUY_TO_CLOSE
        - "Sell to Close" → TransactionType.SELL_TO_CLOSE
        - "Journal Shares" → TransactionType.TRANSFER_IN or TransactionType.TRANSFER_OUT (based on quantity)
    """
    # First try to use the transaction type mapper if available
    from portfolio.transaction_importer.utils import transaction_type_mapper

    action = action_str.lower().strip()
    mapped_type = transaction_type_mapper.get_transaction_type(action, broker, quantity)
    if mapped_type:
        return mapped_type

    # Fallback to hardcoded mappings if no match found in the mapper
    # or if the mapper isn't available

    # Check for standard option transaction formats
    option_action_mapping = {
        # Buy to Open variations
        'buy to open': TransactionType.BUY_TO_OPEN,
        'bto': TransactionType.BUY_TO_OPEN,
        'open buy': TransactionType.BUY_TO_OPEN,
        'opening purchase': TransactionType.BUY_TO_OPEN,

        # Sell to Open variations
        'sell to open': TransactionType.SELL_TO_OPEN,
        'sto': TransactionType.SELL_TO_OPEN,
        'open sell': TransactionType.SELL_TO_OPEN,
        'opening sale': TransactionType.SELL_TO_OPEN,
        'option writing': TransactionType.SELL_TO_OPEN,
        'write': TransactionType.SELL_TO_OPEN,

        # Buy to Close variations
        'buy to close': TransactionType.BUY_TO_CLOSE,
        'btc': TransactionType.BUY_TO_CLOSE,
        'close buy': TransactionType.BUY_TO_CLOSE,
        'closing purchase': TransactionType.BUY_TO_CLOSE,

        # Sell to Close variations
        'sell to close': TransactionType.SELL_TO_CLOSE,
        'stc': TransactionType.SELL_TO_CLOSE,
        'close sell': TransactionType.SELL_TO_CLOSE,
        'closing sale': TransactionType.SELL_TO_CLOSE,

        # Exercise/Assignment
        'exercise': TransactionType.OPTION_EXERCISE,
        'exercised': TransactionType.OPTION_EXERCISE,
        'assignment': TransactionType.OPTION_ASSIGNMENT,
        'assigned': TransactionType.OPTION_ASSIGNMENT,

        # Expiration
        'expiration': TransactionType.OPTION_EXPIRATION,
        'expired': TransactionType.OPTION_EXPIRATION,
        'worthless': TransactionType.OPTION_EXPIRATION
    }

    # Direct mapping if action is in our dictionary
    for key, value in option_action_mapping.items():
        if key in action:
            return value

    # For option transactions with generic action descriptions
    if is_option:
        if 'buy' in action or 'purchase' in action:
            # Default to opening transaction for generic buys
            return TransactionType.BUY_TO_OPEN
        elif 'sell' in action:
            # Default to closing transaction for generic sells
            return TransactionType.SELL_TO_CLOSE

    # For non-options or unrecognized formats, fallback to standard transaction types
    if 'buy' in action:
        return TransactionType.BUY
    elif 'sell' in action:
        return TransactionType.SELL
    elif 'dividend' in action:
        return TransactionType.DIVIDEND
    elif 'interest' in action:
        return TransactionType.INTEREST
    elif 'deposit' in action:
        return TransactionType.DEPOSIT
    elif 'withdrawal' in action:
        return TransactionType.WITHDRAWAL
    elif 'transfer' in action or 'journal' in action:
        # Determine direction based on quantity if available
        if quantity is not None:
            return TransactionType.TRANSFER_OUT if quantity < 0 else TransactionType.TRANSFER_IN
        return TransactionType.TRANSFER_IN  # Default to transfer in if no quantity info
    elif 'fee' in action:
        return TransactionType.FEE
    elif 'split' in action:
        return TransactionType.SPLIT
    else:
        return TransactionType.OTHER


def parse_decimal(value_str: str) -> Optional[Decimal]:
    """Parse string to Decimal, handling commas and currency symbols."""
    if not value_str or value_str.strip() == '':
        return None

    # Remove common currency symbols and commas
    cleaned = value_str.replace('$', '').replace('€', '').replace(',', '').strip()

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_json(json_str: str) -> Optional[Dict[str, Any]]:
    """Parse JSON string to dict."""
    if not json_str or json_str.strip() == '':
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def parse_option_details(symbol: str, description: str = None) -> Dict[str, Any]:
    """Parse option details from symbol and description.

    Attempts to extract ticker, option type, strike price and expiration date.
    Returns a dictionary with extracted information.

    Example inputs:
    - MSFT 12/18/2026 400.00 C
    - CALL MICROSOFT CORP $400 EXP 12/18/26
    - MSFT211217C00340000 (OCC format)
    """
    result = {
        'is_option': False,
        'ticker': symbol,
        'option_type': None,
        'expiration_date': None,
        'strike_price': None
    }

    # If no symbol or description, return early
    if not symbol and not description:
        return result

    # Try to parse OCC standard format (e.g., MSFT211217C00340000)
    occ_pattern = r'^([A-Z]+)([0-9]{6})([CP])([0-9]{8})$'
    occ_match = re.match(occ_pattern, symbol)

    if occ_match:
        result['is_option'] = True
        ticker, date_str, option_type_str, strike_str = occ_match.groups()

        # Parse date (YYMMDD)
        try:
            year = 2000 + int(date_str[0:2])  # Assuming 20xx years
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            result['expiration_date'] = date(year, month, day)
        except ValueError:
            pass

        # Parse option type
        if option_type_str == 'C':
            result['option_type'] = OptionType.CALL
        elif option_type_str == 'P':
            result['option_type'] = OptionType.PUT

        # Parse strike price (divide by 1000 to get actual price)
        try:
            result['strike_price'] = Decimal(strike_str) / 1000
        except (ValueError, InvalidOperation):
            pass

        result['ticker'] = ticker
        return result

    # Try to parse from description if available
    if description:
        # Look for option indicators
        option_indicators = ['call', 'put', 'exp', '$', 'strike']
        if any(indicator in description.lower() for indicator in option_indicators):
            result['is_option'] = True

            # Try to find ticker at the beginning of description
            if not symbol:
                ticker_match = re.search(r'^(?:CALL|PUT)\s+([A-Z\s]+)\s', description)
                if ticker_match:
                    result['ticker'] = ticker_match.group(1).strip()

            # Try to determine option type
            if 'call' in description.lower():
                result['option_type'] = OptionType.CALL
            elif 'put' in description.lower():
                result['option_type'] = OptionType.PUT

            # Try to extract strike price
            price_patterns = [
                r'\$([0-9]+(?:\.[0-9]+)?)',  # $400 or $400.50
                r'([0-9]+(?:\.[0-9]+)?)\s*(?:strike|put|call)',  # 400 strike or 400 put
                r'([0-9]+(?:\.[0-9]+)?)'  # Just a number
            ]

            for pattern in price_patterns:
                price_match = re.search(pattern, description)
                if price_match:
                    try:
                        result['strike_price'] = Decimal(price_match.group(1))
                        break
                    except (ValueError, InvalidOperation):
                        pass

            # Try to extract expiration date
            date_patterns = [
                r'exp\s+([0-9]{1,2}/[0-9]{1,2}/(?:[0-9]{2}|[0-9]{4}))',  # exp 12/18/26 or exp 12/18/2026
                r'([0-9]{1,2}/[0-9]{1,2}/(?:[0-9]{2}|[0-9]{4}))' # 12/18/26 or 12/18/2026
            ]

            for pattern in date_patterns:
                date_match = re.search(pattern, description, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        result['expiration_date'] = parse_date(date_str)
                        break
                    except ValueError:
                        pass

    # If symbol has a space and potentially contains option information
    # Example: "MSFT 12/18/2026 400.00 C"
    if ' ' in symbol:
        parts = symbol.split()
        if len(parts) >= 3:
            # First part is likely the ticker
            result['ticker'] = parts[0]
            result['is_option'] = True

            # Look for date, strike price, and option type
            for part in parts[1:]:
                # Check if part is a date
                date_val = parse_date(part)
                if date_val and not result['expiration_date']:
                    result['expiration_date'] = date_val
                    continue

                # Check if part is a strike price
                try:
                    # Strip currency symbol if present
                    price_str = part.replace('$', '').replace(',', '')
                    price_val = Decimal(price_str)
                    if not result['strike_price']:
                        result['strike_price'] = price_val
                        continue
                except (ValueError, InvalidOperation):
                    pass

                # Check if part indicates option type
                if part.upper() in ['C', 'CALL'] and not result['option_type']:
                    result['option_type'] = OptionType.CALL
                elif part.upper() in ['P', 'PUT'] and not result['option_type']:
                    result['option_type'] = OptionType.PUT

    # If we've determined this is an option but don't have an option type,
    # default to CALL (most common)
    if result['is_option'] and not result['option_type']:
        result['option_type'] = OptionType.CALL

    return result


def calculate_amount(quantity: Optional[Decimal], price: Optional[Decimal], 
                    fees: Optional[Decimal], action: str) -> Optional[Decimal]:
    """Calculate transaction amount based on quantity, price, and fees."""
    if action in ['buy', 'sell'] and quantity is not None and price is not None:
        amount = quantity * price
        if fees is not None:
            # For buys, fees increase the total amount paid
            # For sells, fees decrease the total amount received
            if action == 'buy':
                amount += fees
            else:  # sell
                amount -= fees
        return amount

    # For non-trade transactions, amount needs to be provided explicitly
    return None
