from decimal import Decimal
from datetime import date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from portfolio.models import InstrumentType, OptionType, TransactionType


# Base schemas with common attributes
class BaseSchema(BaseModel):
    id: Optional[UUID] = None


class UserBase(BaseSchema):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True


class AccountBase(BaseSchema):
    name: str
    broker: str
    account_number: Optional[str] = None
    description: Optional[str] = None
    is_taxable: bool = True
    is_active: bool = True


class AccountCreate(AccountBase):
    user_id: UUID


class Account(AccountBase):
    id: UUID
    user_id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True


class SymbolBase(BaseSchema):
    ticker: str
    name: Optional[str] = None
    instrument_type: InstrumentType
    option_type: Optional[OptionType] = None
    expiration_date: Optional[date] = None
    strike_price: Optional[Decimal] = None


class SymbolCreate(SymbolBase):
    pass


class Symbol(SymbolBase):
    id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True


class TransactionBase(BaseSchema):
    account_id: UUID
    symbol_id: Optional[UUID] = None
    transaction_type: TransactionType
    transaction_date: date
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Decimal
    fees: Decimal = Decimal("0.00")
    notes: Optional[str] = None
    related_transaction_id: Optional[UUID] = None


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: UUID
    created_at: date
    updated_at: date

    class Config:
        from_attributes = True


class PositionBase(BaseSchema):
    account_id: UUID
    symbol_id: UUID
    quantity: Decimal
    cost_basis: Decimal
    average_price: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    last_updated: date = Field(default_factory=date.today)


class PositionCreate(PositionBase):
    pass


class Position(PositionBase):
    id: UUID

    class Config:
        from_attributes = True


class PositionSnapshotBase(BaseSchema):
    account_id: UUID
    symbol_id: UUID
    snapshot_date: date
    quantity: Decimal
    cost_basis: Decimal
    average_price: Decimal
    close_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class PositionSnapshotCreate(PositionSnapshotBase):
    pass


class PositionSnapshot(PositionSnapshotBase):
    id: UUID

    class Config:
        from_attributes = True


class RealizedPnLBase(BaseSchema):
    account_id: UUID
    symbol_id: UUID
    transaction_id: UUID
    realized_date: date
    quantity: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    holding_period_days: Optional[int] = None


class RealizedPnLCreate(RealizedPnLBase):
    pass


class RealizedPnL(RealizedPnLBase):
    id: UUID

    class Config:
        from_attributes = True
