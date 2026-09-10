import sys, resource, time
from pygixml import jsonify
xml_path, json_path = sys.argv[1], sys.argv[2]
t0 = time.time()
n = jsonify.stream_dump(xml_path, json_path, indent=0)
t1 = time.time()
peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(f"elements={n} time={t1-t0:.4f}s peak_rss_MB={peak_kb/1024:.2f}")
