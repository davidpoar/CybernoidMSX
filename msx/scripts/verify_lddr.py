"""Empirically determine the LDDR mapping by comparing the pre- and post-LDDR
memory images."""
from pathlib import Path

BEFORE = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_before_lddr.bin')
AFTER = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')

with open(BEFORE, 'rb') as f:
    before = f.read()
with open(AFTER, 'rb') as f:
    after = f.read()

print(f'before: {len(before)} bytes, after: {len(after)} bytes\n')

# For each destination address, find which source address has the same
# content. The LDDR copies with a fixed offset, so we can search for it.
print('Searching for the LDDR offset (dest - src):')
for offset in (0x4000, 0x8000, 0x2000):
    # compare a sample of the copied range
    matches = 0
    total = 0
    for d in range(0x6504, 0xFFFF, 0x100):
        s = d - offset
        if 0x4000 <= s <= 0xFFFF:
            total += 1
            if after[d - 0x4000] == before[s - 0x4000]:
                matches += 1
    if total:
        print(f'  offset ${offset:04X}: {matches}/{total} samples match')

print()
print('Direct check of a few addresses:')
for d in (0x6504, 0x7000, 0x8000, 0x9000, 0xA000, 0xC000, 0xD000, 0xE000):
    src = d - 0x4000
    same = (0x4000 <= src <= 0xFFFF and
            after[d - 0x4000] == before[src - 0x4000])
    print(f'  dest ${d:04X}: after=${after[d-0x4000]:02X}  '
          f'before[${src:04X}]={before[src-0x4000]:02X}  '
          f'{"MATCH" if same else "differs"}')

print()
print('First 16 bytes of each post-LDDR region:')
for lo, hi, name in [(0x6504, 0x7FFF, 'game part 1'),
                     (0x8000, 0x9AFF, 'region 2'),
                     (0x9B00, 0xBFFF, 'region 3'),
                     (0xC000, 0xD12C, 'region 4'),
                     (0xD12D, 0xFFFF, 'region 5')]:
    d = after[lo - 0x4000:lo - 0x4000 + 16]
    print(f'  ${lo:04X} {name:12s}: {d.hex(" ")}')
