#!/usr/bin/env python3
"""Proxy validator - tests proxies and saves working ones using stdlib only."""

import urllib.request
import urllib.error
import sys
import concurrent.futures
from typing import List, Tuple

# Test configuration
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 8  # seconds per proxy
MAX_WORKERS = 20  # parallel threads

def test_proxy(proxy: str) -> Tuple[str, bool]:
    """Test a single proxy, return (proxy, is_working)."""
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': f'http://{proxy}'})
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        resp = opener.open(TEST_URL, timeout=TIMEOUT)
        return (proxy, resp.status == 200)
    except Exception:
        return (proxy, False)

def load_proxies(path: str) -> List[str]:
    """Load proxies from file."""
    with open(path) as f:
        return [line.strip() for line in f if line.strip() and ":" in line]

def save_proxies(proxies: List[str], path: str):
    """Save working proxies to file."""
    with open(path, "w") as f:
        for proxy in proxies:
            f.write(proxy + "\n")

def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_proxies.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    print(f"Loading proxies from {input_file}...")
    proxies = load_proxies(input_file)
    print(f"Loaded {len(proxies)} proxies, testing with {MAX_WORKERS} workers...")

    working = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_proxy = {executor.submit(test_proxy, p): p for p in proxies}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_proxy)):
            proxy, is_working = future.result()
            if is_working:
                working.append(proxy)
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{len(proxies)}, {len(working)} working")

    print(f"\nFound {len(working)} working proxies")
    save_proxies(working, output_file)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()