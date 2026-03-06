"""CLI entry point for landRAG ingestion pipeline."""

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(description="landRAG ingestion pipeline")
    parser.add_argument(
        "--projects",
        nargs="*",
        help="Specific project references to ingest (e.g. EN010012). If omitted, ingests all energy projects.",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Maximum documents to process per project (useful for testing)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from landrag.ingestion.pipeline import run_pipeline

    run_pipeline(
        project_references=args.projects,
        max_documents_per_project=args.max_docs,
    )


if __name__ == "__main__":
    main()
