#!/usr/bin/env python3
"""
Clean visualization script - saves CSV data and creates better charts
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import csv
import os
from datetime import datetime
import statistics


def save_results_to_csv(results_data, filename=None):
    """Save benchmark results to CSV file in results folder"""
    if filename is None:
        filename = "results/benchmark_results.csv"
    
    # Prepare data for CSV
    rows = []
    for size, data in results_data.items():
        for lib in ['pygixml', 'lxml', 'elementtree']:
            parse_times = data['parsing'][lib]
            trav_times = data['traversal'][lib]
            
            for i, (parse_time, trav_time) in enumerate(zip(parse_times, trav_times)):
                rows.append({
                    'xml_size': size,
                    'library': lib,
                    'iteration': i + 1,
                    'parsing_time': parse_time,
                    'traversal_time': trav_time
                })
    
    # Write to CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['xml_size', 'library', 'iteration', 'parsing_time', 'traversal_time'])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"📊 CSV results saved to: {filename}")
    return filename


def create_better_charts(results_data):
    """Create cleaner, more focused performance charts"""
    
    # Create output directory
    os.makedirs("results", exist_ok=True)
    
    # Extract data
    sizes = list(results_data.keys())
    libraries = ['pygixml', 'lxml', 'elementtree']
    
    # Calculate averages
    parsing_avgs = {lib: [] for lib in libraries}
    traversal_avgs = {lib: [] for lib in libraries}
    
    for size in sizes:
        for lib in libraries:
            parsing_avgs[lib].append(statistics.mean(results_data[size]['parsing'][lib]))
            traversal_avgs[lib].append(statistics.mean(results_data[size]['traversal'][lib]))
    
    # Create a single, focused chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Chart 1: Parsing Performance Comparison
    colors = ['#2E86AB', '#A23B72', '#F18F01']
    markers = ['o', 's', '^']
    
    for i, lib in enumerate(libraries):
        ax1.plot(sizes, parsing_avgs[lib], 
                marker=markers[i], linewidth=3, markersize=8,
                label=lib.upper(), color=colors[i])
    
    ax1.set_xlabel('Number of XML Elements', fontsize=12)
    ax1.set_ylabel('Time (seconds)', fontsize=12)
    ax1.set_title('XML Parsing Performance Comparison', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    
    # Add performance annotations
    for size, pygixml_time, lxml_time, etree_time in zip(sizes, 
                                                        parsing_avgs['pygixml'], 
                                                        parsing_avgs['lxml'], 
                                                        parsing_avgs['elementtree']):
        speedup_vs_etree = etree_time / pygixml_time
        speedup_vs_lxml = lxml_time / pygixml_time
        
        if size == max(sizes):  # Only annotate largest size
            ax1.annotate(f'{speedup_vs_etree:.1f}x faster than ElementTree\n{speedup_vs_lxml:.1f}x faster than lxml',
                        xy=(size, pygixml_time),
                        xytext=(10, 20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                        fontsize=9)
    
    # Chart 2: Speedup Comparison
    speedup_data = []
    for size in sizes:
        etree_parse = parsing_avgs['elementtree'][sizes.index(size)]
        pygixml_speedup = etree_parse / parsing_avgs['pygixml'][sizes.index(size)]
        lxml_speedup = etree_parse / parsing_avgs['lxml'][sizes.index(size)]
        speedup_data.append({'size': size, 'pygixml': pygixml_speedup, 'lxml': lxml_speedup})
    
    x = np.arange(len(sizes))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, [d['pygixml'] for d in speedup_data], width,
                   label='pygixml', color=colors[0], alpha=0.8)
    bars2 = ax2.bar(x + width/2, [d['lxml'] for d in speedup_data], width,
                   label='lxml', color=colors[1], alpha=0.8)
    
    ax2.set_xlabel('Number of XML Elements', fontsize=12)
    ax2.set_ylabel('Speedup Factor (x)', fontsize=12)
    ax2.set_title('Speedup vs ElementTree', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(sizes)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}x', ha='center', va='bottom', 
                    fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    
    # Save the chart as SVG
    chart_path = "results/performance_comparison.svg"
    plt.savefig(chart_path, bbox_inches='tight', facecolor='white', format='svg')
    # plt.show()
    plt.close()
    
    print(f"📈 Chart saved to: {chart_path}")
    
    # Print performance summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    largest_size = max(sizes)
    idx = sizes.index(largest_size)
    
    pygixml_parse = parsing_avgs['pygixml'][idx]
    lxml_parse = parsing_avgs['lxml'][idx]
    etree_parse = parsing_avgs['elementtree'][idx]
    
    speedup_vs_etree = etree_parse / pygixml_parse
    speedup_vs_lxml = lxml_parse / pygixml_parse
    
    print(f"For {largest_size} XML elements:")
    print(f"   • pygixml: {pygixml_parse:.6f} seconds")
    print(f"   • lxml:    {lxml_parse:.6f} seconds") 
    print(f"   • ElementTree: {etree_parse:.6f} seconds")
    print(f"   • pygixml is {speedup_vs_etree:.1f}x faster than ElementTree")
    print(f"   • pygixml is {speedup_vs_lxml:.1f}x faster than lxml")
    
    return chart_path, speedup_data


def run_clean_benchmarks():
    """Run benchmarks and generate clean output"""
    print("🚀 Running XML benchmarks")
    print("="*50)
    
    # Import and run benchmarks
    from benchmark_parsing import main as run_parsing_benchmarks
    
    try:
        results = run_parsing_benchmarks()
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        return
    
    # Save to CSV
    csv_file = save_results_to_csv(results)
    
    # Create better charts
    chart_file, speedup_data = create_better_charts(results)
    
    print(f"\n✅ Benchmarks completed successfully!")
    print(f"📄 Data: {csv_file}")
    print(f"📊 Chart: {chart_file}")
    
    return results, csv_file, chart_file


if __name__ == "__main__":
    run_clean_benchmarks()
