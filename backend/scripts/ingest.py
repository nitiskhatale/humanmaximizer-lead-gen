"""
CLI wrapper for WebIngestor.

Usage:
    python scripts/ingest.py            # first-time ingest
    python scripts/ingest.py --refresh  # drop collection and re-ingest
"""
import argparse
import logging
import sys
import os

# Ensure backend/ is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest HumanMaximizer website into ChromaDB.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Drop the existing collection before ingesting.",
    )
    args = parser.parse_args()

    from rag.ingestor import WebIngestor

    ingestor = WebIngestor()
    count = ingestor.run(refresh=args.refresh)
    print(f"Ingestion complete. {count} chunks indexed.")


if __name__ == "__main__":
    main()
