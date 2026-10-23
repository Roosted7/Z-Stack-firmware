import hashlib, json, struct, sys, zipfile
from pathlib import Path
p = Path(sys.argv[1])
mem = {}; base = 0; eof = False; count = 0
for line in p.read_text().splitlines():
    assert not eof, 'record after EOF'
    assert line.startswith(':')
    r = bytes.fromhex(line[1:]); count += 1
    assert len(r) == r[0] + 5 and sum(r) % 256 == 0
    n, addr, kind = r[0], int.from_bytes(r[1:3], 'big'), r[3]
    data = r[4:-1]
    if kind == 0:
        for i, v in enumerate(data):
            a = base + addr + i
            assert a not in mem, 'overlapping records'
            mem[a] = v
    elif kind == 1:
        assert n == 0 and addr == 0; eof = True
    elif kind == 4:
        assert n == 2 and addr == 0; base = int.from_bytes(data, 'big') << 16
    elif kind == 2:
        assert n == 2 and addr == 0; base = int.from_bytes(data, 'big') << 4
    else:
        assert kind in (3, 5) and n == 4
assert eof and mem
assert min(mem) == 0 and max(mem) == 0x57fff
assert not any(0x50000 <= a < 0x57fa8 for a in mem), 'image writes NV storage or flash gap'
def word(a): return int.from_bytes(bytes(mem[a+i] for i in range(4)), 'little')
sp, reset = word(0), word(4)
assert 0x20000000 <= sp <= 0x20014000 and reset & 1 and (reset & ~1) in mem
bl = word(0x57fd8)
assert bl >> 24 == 0xc5 and bl & 0xff == 0xc5
assert (bl >> 8) & 0xff == 13 and not (bl & 0x10000)
result = dict(status='PASS', records=count, data_bytes=len(mem), address_min=hex(min(mem)), address_max=hex(max(mem)), initial_stack_pointer=hex(sp), reset_vector=hex(reset), bootloader_word=hex(bl), bootloader_backdoor='DIO13 active low', nv_region='0x50000-0x55fff, no image data', sha256=hashlib.sha256(p.read_bytes()).hexdigest())
if len(sys.argv) > 2:
    z = zipfile.ZipFile(sys.argv[2]); assert z.testzip() is None
    assert len(z.namelist()) == 1 and z.read(z.namelist()[0]) == p.read_bytes()
    result['zip_crc_and_content'] = 'PASS'
    result['zip_sha256'] = hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()
print(json.dumps(result, indent=2))
