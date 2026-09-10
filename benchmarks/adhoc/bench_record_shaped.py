import time, json, random, resource
from pygixml import jsonify

def gen_record(i):
    return (f"<order><id>{i}</id><customer>c{i%500}</customer>"
            f"<items><item><sku>s{i}</sku><qty>{i%9+1}</qty></item>"
            f"<item><sku>s{i+1}</sku><qty>{i%5+1}</qty></item></items>"
            f"<total>{i*1.5:.2f}</total></order>")

def gen_xml(n):
    return "<orders>" + "".join(gen_record(i) for i in range(n)) + "</orders>"

print("=== TIMING (should scale ~linearly) ===")
for N in [5000, 20000, 80000, 320000]:
    xml = gen_xml(N).encode()
    open('/tmp/rec.xml','wb').write(xml)
    t0 = time.time()
    n = jsonify.stream_dump('/tmp/rec.xml', '/tmp/rec.json', indent=0)
    t1 = time.time()
    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"N={N:7d}  elements={n:7d}  time={t1-t0:.4f}s  time/elem={((t1-t0)/N)*1e6:.3f}us  peak_rss={peak_kb/1024:.1f}MB")

print()
print("=== CORRECTNESS (byte-for-byte vs DOM reference, small+large N) ===")
for N in [50, 500, 5000, 50000]:
    xml = gen_xml(N).encode()
    open('/tmp/rec.xml','wb').write(xml)
    expected = jsonify.dumps_file('/tmp/rec.xml', pretty=False)
    jsonify.stream_dump('/tmp/rec.xml', '/tmp/rec.json', indent=0)
    got = open('/tmp/rec.json').read()
    ok = (got == expected)
    print(f"N={N:6d}  byte-exact match: {ok}")
    if not ok:
        print("  MISMATCH!")
        for a,b in zip(got, expected):
            if a!=b:
                print("first diff around:", got[:100], "...", expected[:100])
                break
