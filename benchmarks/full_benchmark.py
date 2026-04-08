#!/usr/bin/env python3
"""
Comprehensive benchmark suite for pygixml.

Compares:
  1. Parsing performance across multiple XML sizes
  2. Traversal performance
  3. Memory usage during parsing
"""

import time
import statistics
import os
import random
import string
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Test XML generation
# ---------------------------------------------------------------------------

def generate_test_xml(num_elements=1000):
    """Generate test XML data with specified number of elements."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<root>']
    for i in range(num_elements):
        parts.append(
            f'<item id="{i}">'
            f'<name>Item {i}</name>'
            f'<value>{random.randint(1, 1000)}</value>'
            f'<description>{"".join(random.choices(string.ascii_letters, k=50))}</description>'
            '</item>'
        )
    parts.append('</root>')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Parsing benchmarks
# ---------------------------------------------------------------------------

def bench_pygixml_parse(xml_str):
    import pygixml
    doc = pygixml.parse_string(xml_str)
    return doc


def bench_pygixml_parse_minimal(xml_str):
    import pygixml
    doc = pygixml.parse_string(xml_str, pygixml.PARSE_MINIMAL)
    return doc


def bench_lxml_parse(xml_str):
    from lxml import etree as lxml_etree
    return lxml_etree.fromstring(xml_str.encode('utf-8'))


def bench_et_parse(xml_str):
    import xml.etree.ElementTree as ET
    return ET.fromstring(xml_str)


# ---------------------------------------------------------------------------
# Traversal benchmarks
# ---------------------------------------------------------------------------

def bench_pygixml_traverse(doc):
    root = doc.root
    count = 0
    item = root.first_child()
    while item:
        count += 1
        name = item.child("name")
        value = item.child("value")
        if name and value:
            _ = name.child_value()
            _ = value.child_value()
        item = item.next_sibling
    return count


def bench_lxml_traverse(root):
    count = 0
    for item in root:
        count += 1
        name = item.find('name')
        value = item.find('value')
        if name is not None and value is not None:
            _ = name.text
            _ = value.text
    return count


def bench_et_traverse(root):
    count = 0
    for item in root:
        count += 1
        name = item.find('name')
        value = item.find('value')
        if name is not None and value is not None:
            _ = name.text
            _ = value.text
    return count


# ---------------------------------------------------------------------------
# Memory benchmarks  (uses tracemalloc)
# ---------------------------------------------------------------------------

def measure_memory(bench_fn, xml_str):
    """Return peak memory in MB used by bench_fn."""
    import tracemalloc
    tracemalloc.start()
    bench_fn(xml_str)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024 * 1024)  # bytes → MB


# ---------------------------------------------------------------------------
# Package size  (uses pip-size if available)
# ---------------------------------------------------------------------------

def get_package_size(pkg_name):
    """Return installed package size in MB via pip-size, or None."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip_size', pkg_name],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # pip-size output looks like:
            #   Package: pygixml
            #   Size: 1.2 MB
            for line in result.stdout.splitlines():
                if 'Size' in line or 'size' in line:
                    # Extract number
                    parts = line.split()
                    for p in parts:
                        try:
                            return float(p.replace(',', ''))
                        except ValueError:
                            continue
    except Exception:
        pass
    return None


def get_package_size_fallback(pkg_name):
    """Fallback: walk the installed package directory and sum file sizes."""
    try:
        mod = __import__(pkg_name)
        pkg_path = os.path.dirname(mod.__file__)
        total = 0
        for dirpath, _, filenames in os.walk(pkg_path):
            for f in filenames:
                total += os.path.getsize(os.path.join(dirpath, f))
        return total / (1024 * 1024)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

XML_SIZES = [100, 500, 1_000, 2_500, 5_000, 10_000]
ITERATIONS = 5


def run_parsing_benchmarks():
    results = {}
    for size in XML_SIZES:
        xml_str = generate_test_xml(size)
        print(f"\n  Parsing {size} elements...")

        bench_fns = {
            'pygixml': bench_pygixml_parse,
            'pygixml_min': bench_pygixml_parse_minimal,
            'lxml': bench_lxml_parse,
            'elementtree': bench_et_parse,
        }

        size_results = {}
        for lib, fn in bench_fns.items():
            times = []
            # Warmup: first call imports Cython, allocates, etc.
            fn(xml_str)
            for _ in range(ITERATIONS):
                t0 = time.perf_counter()
                fn(xml_str)
                t1 = time.perf_counter()
                times.append(t1 - t0)
            avg = statistics.mean(times)
            size_results[lib] = {
                'parse_avg_s': avg,
                'parse_min_s': min(times),
                'parse_max_s': max(times),
            }

        # Traversal
        print(f"  Traversing {size} elements...")
        pygixml_doc = bench_pygixml_parse(xml_str)
        lxml_root = bench_lxml_parse(xml_str)
        et_root = bench_et_parse(xml_str)

        for lib, fn, root_obj in [
            ('pygixml', bench_pygixml_traverse, pygixml_doc),
            ('lxml', bench_lxml_traverse, lxml_root),
            ('elementtree', bench_et_traverse, et_root),
        ]:
            trav_times = []
            count = 0
            # Warmup
            fn(root_obj)
            for _ in range(ITERATIONS):
                t0 = time.perf_counter()
                count = fn(root_obj)
                t1 = time.perf_counter()
                trav_times.append(t1 - t0)
            size_results[lib]['traverse_avg_s'] = statistics.mean(trav_times)
            size_results[lib]['traverse_min_s'] = min(trav_times)

        results[size] = size_results
        print(f"    ✓ done  ({count} elements verified)")

    return results


def run_memory_benchmarks():
    """Measure peak memory usage for each parser at different sizes."""
    mem_sizes = [1_000, 5_000, 10_000]
    results = {}

    for size in mem_sizes:
        xml_str = generate_test_xml(size)
        print(f"\n  Memory {size} elements...")

        mem = {}
        for label, fn in [
            ('pygixml', bench_pygixml_parse),
            ('lxml', bench_lxml_parse),
            ('elementtree', bench_et_parse),
        ]:
            measurements = []
            for _ in range(3):
                m = measure_memory(fn, xml_str)
                measurements.append(m)
            mem[label] = statistics.mean(measurements)
            print(f"    {label:12s}: {mem[label]:.2f} MB")

        results[size] = mem

    return results


def run_package_size():
    """Get installed package sizes."""
    print("\n  Package sizes...")
    packages = {}
    for pkg in ['pygixml', 'lxml']:
        size = get_package_size(pkg)
        if size is None:
            size = get_package_size_fallback(pkg)
        packages[pkg] = size
        print(f"    {pkg:12s}: {size:.2f} MB" if size else f"    {pkg:12s}: N/A")
    return packages


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------

def print_table(results):
    print("\n" + "=" * 85)
    print("PARSING PERFORMANCE")
    print("=" * 85)
    print(f"{'Size':>8} | {'Library':12} | {'Avg (s)':>10} | {'Min (s)':>10} | {'Speedup vs ET':>14}")
    print("-" * 85)

    for size in XML_SIZES:
        et_avg = results[size]['elementtree']['parse_avg_s']
        for lib in ['pygixml', 'pygixml_min', 'lxml', 'elementtree']:
            d = results[size][lib]
            speedup = et_avg / d['parse_avg_s'] if d['parse_avg_s'] > 0 else 0
            print(f"{size:>8} | {lib:12} | {d['parse_avg_s']:>10.6f} | {d['parse_min_s']:>10.6f} | {speedup:>13.1f}x")
        print("-" * 85)

    print("\n" + "=" * 85)
    print("TRAVERSAL PERFORMANCE")
    print("=" * 85)
    print(f"{'Size':>8} | {'Library':12} | {'Avg (s)':>10} | {'Min (s)':>10}")
    print("-" * 85)

    for size in XML_SIZES:
        for lib in ['pygixml', 'lxml', 'elementtree']:
            d = results[size][lib]
            print(f"{size:>8} | {lib:12} | {d['traverse_avg_s']:>10.6f} | {d['traverse_min_s']:>10.6f}")
        print("-" * 85)


def print_memory_table(mem_results):
    print("\n" + "=" * 60)
    print("MEMORY USAGE (peak, traced via tracemalloc)")
    print("=" * 60)
    print(f"{'Size':>8} | {'Library':12} | {'Peak MB':>10}")
    print("-" * 60)
    for size in sorted(mem_results.keys()):
        for lib in ['pygixml', 'lxml', 'elementtree']:
            val = mem_results[size].get(lib, 0)
            print(f"{size:>8} | {lib:12} | {val:>10.2f}")
        print("-" * 60)


def print_package_table(pkg_sizes):
    print("\n" + "=" * 40)
    print("INSTALLED PACKAGE SIZE")
    print("=" * 40)
    print(f"{'Package':12} | {'Size (MB)':>10}")
    print("-" * 40)
    for pkg, size in pkg_sizes.items():
        if size is not None:
            print(f"{pkg:12} | {size:>10.2f}")
        else:
            print(f"{pkg:12} | {'N/A':>10}")
    print("-" * 40)


# ---------------------------------------------------------------------------
# Save JSON results
# ---------------------------------------------------------------------------

def save_json(all_results, output_path='results/benchmark_full.json'):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Convert everything to JSON-serializable
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n📊 Full results saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("pygixml  Comprehensive Benchmark Suite")
    print("=" * 60)

    # 1. Parsing + traversal across sizes
    print("\n--- Parsing & Traversal ---")
    parse_results = run_parsing_benchmarks()
    print_table(parse_results)

    # 2. Memory
    print("\n--- Memory ---")
    mem_results = run_memory_benchmarks()
    print_memory_table(mem_results)

    # 3. Package size
    pkg_results = run_package_size()
    print_package_table(pkg_results)

    # Save everything
    save_json({
        'parse': parse_results,
        'memory': mem_results,
        'package_size': pkg_results,
        'xml_sizes': XML_SIZES,
        'iterations': ITERATIONS,
    })

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
