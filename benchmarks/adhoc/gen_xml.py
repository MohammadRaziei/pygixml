import sys
def gen_record(i):
    return (f"<order><id>{i}</id><customer>c{i%500}</customer>"
            f"<items><item><sku>s{i}</sku><qty>{i%9+1}</qty></item>"
            f"<item><sku>s{i+1}</sku><qty>{i%5+1}</qty></item></items>"
            f"<total>{i*1.5:.2f}</total></order>")
N = int(sys.argv[1])
path = sys.argv[2]
with open(path, 'w') as f:
    f.write("<orders>")
    for i in range(N):
        f.write(gen_record(i))
    f.write("</orders>")
