# Portfolio Tracker

A desktop-based personal portfolio tracker app for individual investors to privately track investments across multiple accounts, asset types, and time periods with full precision and without sending any data to the cloud.

![Transaction Import UI](docs/transaction_import_screenshot.png)

## Features

- Track multiple brokerage accounts (Fidelity, Schwab, etc.)
- Support fractional shares with accurate cost basis
- Asset types: Stocks, ETFs, Options (calls and puts), Cash
- Daily tracking of positions and realized/unrealized P&L
- Support internal transfers between accounts without triggering tax events
- Performance metrics: IRR, TWR (Money-Weighted and Time-Weighted Return)
- Completely offline / local-first desktop app
- CSV import only (no broker integrations)

## Technology Stack

- Python 3.12+
- PostgreSQL database
- SQLAlchemy ORM for database access
- Alembic for database migrations
- PySide6 for native GUI (future development)
- Poetry for dependency management
- Decimal arithmetic for financial calculations

## Setup

### Prerequisites

- Python 3.12 or higher
- PostgreSQL
- Poetry

### Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/portfolio-tracker.git
cd portfolio-tracker
```

2. Install dependencies

```bash
# Install core dependencies
poetry install

# Install GUI dependencies (PySide6)
poetry install --extras gui
```

3. Create a PostgreSQL database

```bash
psql -c "CREATE USER portfolio WITH PASSWORD 'secret';"
psql -c "CREATE DATABASE portfolio OWNER portfolio;"
```

4. Initialize the database

```bash
poetry run portfolio-db init
# Or alternatively
poetry run python -m portfolio.cli init
```

### Database Management

The application uses Alembic for database migrations. You can use the following commands to manage your database schema:

```bash
# Create a new migration after making model changes
poetry run portfolio-db makemigration "Description of changes"

# Apply pending migrations
poetry run portfolio-db upgrade

# Rollback the last migration
poetry run portfolio-db downgrade

# View migration history
poetry run portfolio-db showmigrations
```

### Importing Transactions

The application supports importing transactions from CSV files. Make sure you've installed the GUI dependencies first with `poetry install --extras gui`.

```bash
# Launch the transaction import UI
poetry run python -m portfolio import
```

The CSV should have the following columns:
- `date`: Transaction date (YYYY-MM-DD)
- `symbol`: Stock symbol/ticker
- `action`: Transaction type (buy, sell, dividend, deposit, withdrawal, etc.)
- `quantity`: Number of shares (for trades)
- `price`: Price per share (for trades)
- `fees`: Transaction fees
- `account_name`: Name of the account (must match an account in the database)
- `instrument_type`: Type of instrument (stock, etf, option, cash)
- `journal_details`: Optional JSON field for transfer details
- `notes`: Optional notes about the transaction
- `amount`: Optional total amount (will be calculated if not provided)

A sample CSV file is provided at `src/portfolio/examples/transactions_import_sample.csv`.

## Project Structure

- `src/portfolio/`: Main package directory
  - `models.py`: SQLAlchemy ORM models
  - `database.py`: Database connection configuration
  - `schema.py`: Pydantic models for data validation
  - `cli.py`: Command-line interface for database operations
- `migrations/`: Alembic migration scripts
- `tests/`: Test suite

## Development

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://portfolio:secret@localhost:5432/portfolio`)

## License

[MIT](LICENSE)