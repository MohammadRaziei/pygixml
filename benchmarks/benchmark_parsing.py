#!/usr/bin/env python3
"""
Benchmark script for comparing XML parsing performance between:
- pygixml (our Cython wrapper)
- lxml (fast C-based parser)
- xml.etree.ElementTree (Python standard library)
"""

import time
import timeit
import statistics
import sys
import os
import xml.etree.ElementTree as ET
from lxml import etree as lxml_etree
import pygixml
import random
import string


def generate_test_xml(num_elements=1000):
    """Generate test XML data with specified number of elements"""
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>', '<root>']
    
    for i in range(num_elements):
        element = f'<item id="{i}">'
        element += f'<name>Item {i}</name>'
        element += f'<value>{random.randint(1, 1000)}</value>'
        element += f'<description>{"".join(random.choices(string.ascii_letters, k=50))}</description>'
        element += '</item>'
        xml_content.append(element)
    
    xml_content.append('</root>')
    return '\n'.join(xml_content)


def benchmark_pygixml_parse(xml_content):
    """Benchmark pygixml parsing"""
    start_time = time.time()
    doc = pygixml.parse_string(xml_content)
    end_time = time.time()
    return end_time - start_time, doc


def benchmark_lxml_parse(xml_content):
    """Benchmark lxml parsing"""
    start_time = time.time()
    root = lxml_etree.fromstring(xml_content.encode('utf-8'))
    end_time = time.time()
    return end_time - start_time, root


def benchmark_elementtree_parse(xml_content):
    """Benchmark ElementTree parsing"""
    start_time = time.time()
    root = ET.fromstring(xml_content)
    end_time = time.time()
    return end_time - start_time, root


def benchmark_pygixml_traversal(doc):
    """Benchmark pygixml traversal"""
    start_time = time.time()
    root = doc.first_child()
    count = 0
    
    item = root.first_child()
    while item:
        count += 1
        name = item.child("name")
        value = item.child("value")
        if name and value:
            _ = name.child_value()
            _ = value.child_value()
        item = item.next_sibling()
    
    end_time = time.time()
    return end_time - start_time, count


def benchmark_lxml_traversal(root):
    """Benchmark lxml traversal"""
    start_time = time.time()
    count = 0
    
    for item in root:
        count += 1
        name = item.find('name')
        value = item.find('value')
        if name is not None and value is not None:
            _ = name.text
            _ = value.text
    
    end_time = time.time()
    return end_time - start_time, count


def benchmark_elementtree_traversal(root):
    """Benchmark ElementTree traversal"""
    start_time = time.time()
    count = 0
    
    for item in root:
        count += 1
        name = item.find('name')
        value = item.find('value')
        if name is not None and value is not None:
            _ = name.text
            _ = value.text
    
    end_time = time.time()
    return end_time - start_time, count


def run_benchmarks(xml_content, iterations=10):
    """Run comprehensive benchmarks"""
    print(f"Running benchmarks with {len(xml_content.split())} lines of XML...")
    print("=" * 60)
    
    results = {
        'parsing': {'pygixml': [], 'lxml': [], 'elementtree': []},
        'traversal': {'pygixml': [], 'lxml': [], 'elementtree': []}
    }
    
    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}")
        
        # Parsing benchmarks
        pygixml_time, pygixml_doc = benchmark_pygixml_parse(xml_content)
        lxml_time, lxml_root = benchmark_lxml_parse(xml_content)
        elementtree_time, elementtree_root = benchmark_elementtree_parse(xml_content)
        
        results['parsing']['pygixml'].append(pygixml_time)
        results['parsing']['lxml'].append(lxml_time)
        results['parsing']['elementtree'].append(elementtree_time)
        
        # Traversal benchmarks
        pygixml_trav_time, pygixml_count = benchmark_pygixml_traversal(pygixml_doc)
        lxml_trav_time, lxml_count = benchmark_lxml_traversal(lxml_root)
        elementtree_trav_time, elementtree_count = benchmark_elementtree_traversal(elementtree_root)
        
        results['traversal']['pygixml'].append(pygixml_trav_time)
        results['traversal']['lxml'].append(lxml_trav_time)
        results['traversal']['elementtree'].append(elementtree_trav_time)
        
        # Verify all libraries processed the same number of elements
        assert pygixml_count == lxml_count == elementtree_count, \
            f"Element count mismatch: pygixml={pygixml_count}, lxml={lxml_count}, elementtree={elementtree_count}"
    
    return results


def print_results(results):
    """Print benchmark results in a formatted table"""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    
    print("\nPARSING PERFORMANCE (seconds)")
    print("-" * 50)
    for lib in ['pygixml', 'lxml', 'elementtree']:
        times = results['parsing'][lib]
        avg = statistics.mean(times)
        std = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)
        print(f"{lib:12} | Avg: {avg:.6f} ± {std:.6f} | Min: {min_time:.6f} | Max: {max_time:.6f}")
    
    print("\nTRAVERSAL PERFORMANCE (seconds)")
    print("-" * 50)
    for lib in ['pygixml', 'lxml', 'elementtree']:
        times = results['traversal'][lib]
        avg = statistics.mean(times)
        std = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)
        print(f"{lib:12} | Avg: {avg:.6f} ± {std:.6f} | Min: {min_time:.6f} | Max: {max_time:.6f}")
    
    # Calculate speedup factors
    print("\nSPEEDUP FACTORS (compared to ElementTree)")
    print("-" * 50)
    elementtree_parse_avg = statistics.mean(results['parsing']['elementtree'])
    elementtree_trav_avg = statistics.mean(results['traversal']['elementtree'])
    
    for lib in ['pygixml', 'lxml']:
        parse_avg = statistics.mean(results['parsing'][lib])
        trav_avg = statistics.mean(results['traversal'][lib])
        
        parse_speedup = elementtree_parse_avg / parse_avg if parse_avg > 0 else float('inf')
        trav_speedup = elementtree_trav_avg / trav_avg if trav_avg > 0 else float('inf')
        
        print(f"{lib:12} | Parsing: {parse_speedup:.2f}x | Traversal: {trav_speedup:.2f}x")


def main():
    """Main benchmark function"""
    print("XML Parser Benchmark Suite")
    print("Comparing: pygixml vs lxml vs xml.etree.ElementTree")
    print()
    
    # Test with different XML sizes
    xml_sizes = [100, 1000, 5000]
    
    all_results = {}
    
    for size in xml_sizes:
        print(f"\n{'='*60}")
        print(f"Testing with {size} XML elements")
        print(f"{'='*60}")
        
        xml_content = generate_test_xml(size)
        results = run_benchmarks(xml_content, iterations=5)
        all_results[size] = results
        print_results(results)
    
    return all_results


if __name__ == "__main__":
    main()
