import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Portfolio Tracker CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add db command - delegates to cli.main
    db_parser = subparsers.add_parser("db", help="Database management commands")

    # Add import command
    import_parser = subparsers.add_parser("import", help="Import transactions from CSV")

    args = parser.parse_args()

    if args.command == "db":
        # Import and run the database CLI
        from portfolio.cli import main as db_main
        sys.argv.pop(1)  # Remove the 'db' argument
        db_main()

    elif args.command == "import":
        # Import and run the transaction importer
        from portfolio.transaction_importer.main import main as import_main
        import_main()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

