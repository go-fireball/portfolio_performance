import logging
import json
import os
from pathlib import Path
from typing import Dict, Optional, Union
from decimal import Decimal

from portfolio.models import TransactionType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TransactionTypeMapper:
    """Maps broker-specific transaction descriptions to standardized transaction types.

    This class manages the mapping of transaction descriptions from various brokers
    to the application's standardized TransactionType enum values. It can load and save
    mappings to a JSON file, making it easier for users to import transactions without
    manually mapping each time.
    """

    def __init__(self, mapping_file: Optional[str] = None):
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.mapping_file = mapping_file or self._get_default_mapping_path()
        self._load_mappings()

    @staticmethod
    def _get_default_mapping_path() -> str:
        """Returns the default path for the transaction type mappings file."""
        # Store in user's home directory to persist across application updates
        home_dir = Path.home()
        app_dir = home_dir / ".portfolio-tracker"
        app_dir.mkdir(exist_ok=True)
        return str(app_dir / "transaction_type_mappings.json")

    def _load_mappings(self) -> None:
        """Load mappings from the JSON file."""
        if not os.path.exists(self.mapping_file):
            # Initialize with default mappings if file doesn't exist
            self._init_default_mappings()
            self._save_mappings()
            return

        try:
            with open(self.mapping_file, 'r') as f:
                self.mappings = json.load(f)
            logger.info(f"Loaded transaction type mappings from {self.mapping_file}")
        except Exception as e:
            logger.error(f"Error loading transaction type mappings: {str(e)}")
            # Initialize with defaults on error
            self._init_default_mappings()

    def _save_mappings(self) -> None:
        """Save current mappings to the JSON file."""
        try:
            with open(self.mapping_file, 'w') as f:
                json.dump(self.mappings, f, indent=2)
            logger.info(f"Saved transaction type mappings to {self.mapping_file}")
        except Exception as e:
            logger.error(f"Error saving transaction type mappings: {str(e)}")

    def _init_default_mappings(self) -> None:
        """Initialize with default mappings for common brokers."""
        self.mappings = {
            # Common transaction type mappings
            "general": {
                "buy": TransactionType.BUY.value,
                "sell": TransactionType.SELL.value,
                "dividend": TransactionType.DIVIDEND.value,
                "interest": TransactionType.INTEREST.value,
                "deposit": TransactionType.DEPOSIT.value,
                "withdrawal": TransactionType.WITHDRAWAL.value,
                "fee": TransactionType.FEE.value,
                "split": TransactionType.SPLIT.value,
                # Transfer-specific mappings
                "transfer": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "journal": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "transfer shares": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "journal shares": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "transfer securities": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "transfer funds": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
                "securities transferred": TransactionType.TRANSFER_IN.value,  # Default, will be adjusted based on quantity
            },
            # Fidelity-specific mappings
            "fidelity": {
                "bought": TransactionType.BUY.value,
                "sold": TransactionType.SELL.value,
                "cash contribution": TransactionType.DEPOSIT.value,
                "dividend received": TransactionType.DIVIDEND.value,
                "reinvestment": TransactionType.BUY.value,
                "transferred in": TransactionType.TRANSFER_IN.value,
                "transferred out": TransactionType.TRANSFER_OUT.value,
                "journaled": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
            },
            # Schwab-specific mappings
            "schwab": {
                "bought": TransactionType.BUY.value,
                "sold": TransactionType.SELL.value,
                "qualified dividend": TransactionType.DIVIDEND.value,
                "non-qualified dividend": TransactionType.DIVIDEND.value,
                "bank interest": TransactionType.INTEREST.value,
                "service fee": TransactionType.FEE.value,
                "journal": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
                "MoneyLink Transfer": TransactionType.TRANSFER_IN.value,
            },
            # Robinhood-specific mappings
            "robinhood": {
                "market buy": TransactionType.BUY.value,
                "market sell": TransactionType.SELL.value,
                "limit buy": TransactionType.BUY.value,
                "limit sell": TransactionType.SELL.value,
                "dividend": TransactionType.DIVIDEND.value,
                "deposit": TransactionType.DEPOSIT.value,
                "withdrawal": TransactionType.WITHDRAWAL.value,
                "transfer": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
            },
            # Interactive Brokers-specific mappings
            "ibkr": {
                "buy": TransactionType.BUY.value,
                "sell": TransactionType.SELL.value,
                "dividend": TransactionType.DIVIDEND.value,
                "deposit": TransactionType.DEPOSIT.value,
                "withdrawal": TransactionType.WITHDRAWAL.value,
                "transfer": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
                "cash transfer": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
            },
            # TD Ameritrade-specific mappings
            "tdameritrade": {
                "bought": TransactionType.BUY.value,
                "sold": TransactionType.SELL.value,
                "reinvestment": TransactionType.BUY.value,
                "dividend": TransactionType.DIVIDEND.value,
                "transfer": TransactionType.TRANSFER_IN.value,  # Will be adjusted based on quantity
            }
        }

    def add_mapping(self, broker: str, action_text: str, transaction_type: Union[TransactionType, str]) -> None:
        """Add a new mapping for a specific broker.

        Args:
            broker: The broker name (lowercase) or 'general' for all brokers
            action_text: The action text from the broker's CSV (lowercase)
            transaction_type: The TransactionType enum or string value to map to
        """
        if broker not in self.mappings:
            self.mappings[broker] = {}

        # Convert TransactionType enum to string value if needed
        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value

        self.mappings[broker][action_text.lower()] = transaction_type
        self._save_mappings()

    def get_transaction_type(self, 
                              action_text: str, 
                              broker: Optional[str] = None, 
                              quantity: Optional[Decimal] = None) -> Optional[TransactionType]:
        """Get the mapped transaction type for the given action text.

        Args:
            action_text: The action text from the broker's CSV
            broker: Optional broker name to check broker-specific mappings first
            quantity: Optional quantity to determine direction for transfers

        Returns:
            The mapped TransactionType or None if no mapping found
        """
        action_lower = action_text.lower()
        result = None

        # Check broker-specific mapping first if provided
        if broker and broker.lower() in self.mappings:
            for key, value in self.mappings[broker.lower()].items():
                if key in action_lower:
                    result = value
                    break

        # If no match found, check general mappings
        if result is None and "general" in self.mappings:
            for key, value in self.mappings["general"].items():
                if key in action_lower:
                    result = value
                    break

        # If we found a transfer type and have quantity info, determine direction
        if result in [TransactionType.TRANSFER_IN.value, TransactionType.TRANSFER_OUT.value] and quantity is not None:
            # For transfers, if quantity is negative, it's a transfer out
            # if quantity is positive, it's a transfer in
            if quantity < 0:
                result = TransactionType.TRANSFER_OUT.value
            else:
                result = TransactionType.TRANSFER_IN.value

        # Convert string value to TransactionType enum
        if result is not None:
            try:
                return TransactionType(result)
            except ValueError:
                logger.warning(f"Invalid transaction type mapping: {result}")
                return None

        return None


# Create a singleton instance for global use
transaction_type_mapper = TransactionTypeMapper()
