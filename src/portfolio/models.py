import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(Date, nullable=False, default=date.today)
    updated_at = Column(Date, nullable=False, default=date.today, onupdate=date.today)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    broker = Column(String(100), nullable=False)
    account_number = Column(String(50), nullable=True)  # Last 4 digits or reference
    description = Column(Text, nullable=True)
    is_taxable = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(Date, nullable=False, default=date.today)
    updated_at = Column(Date, nullable=False, default=date.today, onupdate=date.today)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    position_snapshots = relationship("PositionSnapshot", back_populates="account", cascade="all, delete-orphan")

    # Unique constraint: one account per user/broker/account_number combination
    __table_args__ = (
        UniqueConstraint('user_id', 'broker', 'account_number', name='uix_user_broker_account'),
    )

    def __repr__(self):
        return f"<Account(name='{self.name}', broker='{self.broker}')>"


class InstrumentType(enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    CASH = "cash"
    OTHER = "other"


class OptionType(enum.Enum):
    CALL = "call"
    PUT = "put"


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(20), nullable=False)
    name = Column(String(255), nullable=True)
    instrument_type = Column(Enum(InstrumentType), nullable=False)
    option_type = Column(Enum(OptionType), nullable=True)
    expiration_date = Column(Date, nullable=True)  # For options
    strike_price = Column(Numeric(20, 8), nullable=True)  # For options
    created_at = Column(Date, nullable=False, default=date.today)
    updated_at = Column(Date, nullable=False, default=date.today, onupdate=date.today)

    # Relationships
    transactions = relationship("Transaction", back_populates="symbol")
    positions = relationship("Position", back_populates="symbol")
    position_snapshots = relationship("PositionSnapshot", back_populates="symbol")
    realized_pnls = relationship("RealizedPnL", back_populates="symbol")

    # Unique constraint for symbols
    __table_args__ = (
        UniqueConstraint(
            'ticker', 
            'instrument_type', 
            'option_type', 
            'expiration_date', 
            'strike_price', 
            name='uix_symbol_details'
        ),
    )

    def __repr__(self):
        if self.instrument_type == InstrumentType.OPTION and self.option_type and self.strike_price and self.expiration_date:
            return f"<Symbol(ticker='{self.ticker}', type='{self.instrument_type.value}', option_type='{self.option_type.value}', strike='{self.strike_price}', expiry='{self.expiration_date}')>"
        return f"<Symbol(ticker='{self.ticker}', type='{self.instrument_type.value}')>"


class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"
    OPTION_EXERCISE = "option_exercise"
    OPTION_ASSIGNMENT = "option_assignment"
    OPTION_EXPIRATION = "option_expiration"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE = "fee"
    SPLIT = "split"
    OTHER = "other"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=True)  # Nullable for cash transactions
    transaction_type = Column(Enum(TransactionType), nullable=False)
    transaction_date = Column(Date, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=True)  # Nullable for dividends/interest
    price = Column(Numeric(20, 8), nullable=True)  # Nullable for cash deposits/withdrawals
    amount = Column(Numeric(20, 8), nullable=False)  # Total transaction amount (quantity * price for trades)
    fees = Column(Numeric(20, 8), default=Decimal("0.00"), nullable=False)
    notes = Column(Text, nullable=True)

    # For internal transfers
    related_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)  # Self-reference for linked transfers
    created_at = Column(Date, nullable=False, default=date.today)
    updated_at = Column(Date, nullable=False, default=date.today, onupdate=date.today)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    symbol = relationship("Symbol", back_populates="transactions")
    related_transaction = relationship("Transaction", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<Transaction(date='{self.transaction_date}', type='{self.transaction_type.value}', amount='{self.amount}')>"


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    cost_basis = Column(Numeric(20, 8), nullable=False)  # Total cost basis for the position
    average_price = Column(Numeric(20, 8), nullable=False)  # Cost basis per share
    current_price = Column(Numeric(20, 8), nullable=True)  # Latest known price
    market_value = Column(Numeric(20, 8), nullable=True)  # quantity * current_price
    unrealized_pnl = Column(Numeric(20, 8), nullable=True)  # market_value - cost_basis
    last_updated = Column(Date, nullable=False, default=date.today)

    # Relationships
    account = relationship("Account", back_populates="positions")
    symbol = relationship("Symbol", back_populates="positions")

    # Unique constraint: one position per account/symbol combination
    __table_args__ = (
        UniqueConstraint('account_id', 'symbol_id', name='uix_account_symbol_position'),
    )

    def __repr__(self):
        return f"<Position(account='{self.account_id}', symbol='{self.symbol_id}', quantity='{self.quantity}', avg_price='{self.average_price}')>"


class PositionSnapshot(Base):
    __tablename__ = "position_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    cost_basis = Column(Numeric(20, 8), nullable=False)
    average_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    market_value = Column(Numeric(20, 8), nullable=False)
    unrealized_pnl = Column(Numeric(20, 8), nullable=False)

    # Relationships
    account = relationship("Account", back_populates="position_snapshots")
    symbol = relationship("Symbol", back_populates="position_snapshots")

    # Unique constraint: one snapshot per account/symbol/date combination
    __table_args__ = (
        UniqueConstraint('account_id', 'symbol_id', 'snapshot_date', name='uix_account_symbol_date_snapshot'),
    )

    def __repr__(self):
        return f"<PositionSnapshot(date='{self.snapshot_date}', account='{self.account_id}', symbol='{self.symbol_id}', quantity='{self.quantity}')>"


class RealizedPnL(Base):
    __tablename__ = "realized_pnl"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)  # The sell transaction
    realized_date = Column(Date, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)  # Quantity sold
    proceeds = Column(Numeric(20, 8), nullable=False)  # Amount received from sale (quantity * price - fees)
    cost_basis = Column(Numeric(20, 8), nullable=False)  # Original cost of the sold shares
    realized_pnl = Column(Numeric(20, 8), nullable=False)  # proceeds - cost_basis
    holding_period_days = Column(Integer, nullable=True)  # Optional tracking of holding period

    # Relationships
    account = relationship("Account")
    symbol = relationship("Symbol", back_populates="realized_pnls")
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<RealizedPnL(date='{self.realized_date}', symbol='{self.symbol_id}', pnl='{self.realized_pnl}')>"
