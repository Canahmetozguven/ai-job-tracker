#!/usr/bin/env python3
"""Job scraper CLI using JobSpy and LinkedIn-scraper."""

import asyncio
import json
import sys
from typing import Optional

def prompt_search_query() -> str:
    """Prompt for job search query."""
    return input("Enter job search query: ").strip()

def prompt_location() -> str:
    """Prompt for location."""
    return input("Enter location (city, state/country): ").strip()

def prompt_source() -> int:
    """Prompt for source selection."""
    print("\nSelect source:")
    print("  [1] JobSpy only (default)")
    print("  [2] LinkedIn-scraper only")
    print("  [3] Both with fallback (JobSpy → LinkedIn)")
    while True:
        choice = input("Choice [1]: ").strip() or "1"
        if choice in ("1", "2", "3"):
            return int(choice)
        print("Invalid choice, please enter 1, 2, or 3")

def prompt_results_limit() -> int:
    """Prompt for results limit per source."""
    while True:
        limit = input("Results limit per source [10]: ").strip() or "10"
        try:
            n = int(limit)
            if n > 0:
                return n
        except ValueError:
            pass
        print("Please enter a positive number")

def prompt_output_file() -> str:
    """Prompt for output file path."""
    return input("Output file [jobs.jsonl]: ").strip() or "jobs.jsonl"

def run_menu() -> dict:
    """Run interactive menu, return config dict."""
    return {
        "query": prompt_search_query(),
        "location": prompt_location(),
        "source": prompt_source(),
        "limit": prompt_results_limit(),
        "output": prompt_output_file(),
    }

def main():
    """Entry point."""
    config = run_menu()
    print(f"\nConfig: {config}")

if __name__ == "__main__":
    main()