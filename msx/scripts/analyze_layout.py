"""Analyse the game binary: compressibility, absolute address references,
and where the game can live in MSX RAM.
"""
import struct
from collections import Counter

BIN = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.bin'

with open(BIN, 'rb') as f:
    data = f.read()

game = data[7:-1]          # Spectrum $6504-$FFFF (39676 bytes)
print(f'Game size: {len(game)} bytes')

# ------------------------------------------------------------------
# 1. Compressibility
# ------------------------------------------------------------------
# Simple RLE
rle = bytearray()
i = 0
while i < len(game):
    run = 1
    while i + run < len(game) and game[i + run] == game[i] and run < 255:
        run += 1
    if run >= 3:
        rle.append(0x00)        # marker
        rle.append(run)
        rle.append(game[i])
        i += run
    else:
        rle.append(game[i])
        i += 1
print(f'RLE size: {len(rle)} bytes ({len(rle)*100//len(game)}%)')

# LZ-ish: simple 2-byte dictionary
def lz_size(data):
    # Greedy LZ77 with 4096-byte window, 12-bit offset + 4-bit length
    out = 0
    i = 0
    table = {}
    while i < len(data):
        best_len = 0
        best_off = 0
        start = max(0, i - 4096)
        for off in range(start, i):
            l = 0
            while i + l < len(data) and l < 18 and data[off + l] == data[i + l]:
                l += 1
            if l > best_len:
                best_len = l
                best_off = i - off
        if best_len >= 4:
            out += 2
            i += best_len
        else:
            out += 1
            i += 1
    return out

# (slow lz_size for reference - use a faster estimate on a sample)
sample = game[:8000]
lz = lz_size(sample)
print(f'LZ77 estimate (8K sample): {lz} -> {lz*5} for 40K (approx)')

# ------------------------------------------------------------------
# 2. Absolute address references in the game
# ------------------------------------------------------------------
# Scan for 3-byte instructions with 16-bit operands:
#   CD nn nn  CALL
#   C3 nn nn  JP
#   21 nn nn  LD HL,nn
#   11 nn nn  LD DE,nn
#   01 nn nn  LD BC,nn
#   31 nn nn  LD SP,nn
#   22 nn nn  LD (nn),HL
#   2A nn nn  LD HL,(nn)
#   32 nn nn  LD (nn),A
#   3A nn nn  LD A,(nn)
#   18 nn     JR (relative)
#   28/30/38/20 nn  conditional JR
refs = Counter()
in_data = 0
i = 0
while i < len(game) - 2:
    op = game[i]
    if op in (0xCD, 0xC3, 0x21, 0x11, 0x01, 0x31, 0x22, 0x2A, 0x32, 0x3A):
        addr = game[i+1] | (game[i+2] << 8)
        refs[addr] += 1
        i += 3
    else:
        i += 1

print()
print(f'Total 16-bit absolute references found: {sum(refs.values())}')
print(f'Distinct addresses referenced: {len(refs)}')

# Bucket by region
buckets = Counter()
for addr in refs:
    if addr < 0x4000:
        buckets['$0000-$3FFF (BIOS/ROM area)'] += refs[addr]
    elif addr < 0x5B00:
        buckets['$4000-$5AFF (Spectrum screen)'] += refs[addr]
    elif addr < 0x6504:
        buckets['$5B00-$6503 (zeroed area)'] += refs[addr]
    elif addr < 0x8000:
        buckets['$6504-$7FFF (game low)'] += refs[addr]
    elif addr < 0xC000:
        buckets['$8000-$BFFF (game mid)'] += refs[addr]
    else:
        buckets['$C000-$FFFF (game high)'] += refs[addr]

print()
print('References by target region:')
for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
    print(f'  {k:32s} {v}')

# ------------------------------------------------------------------
# 3. Where can the game live in MSX RAM?
# ------------------------------------------------------------------
print()
print('MSX main RAM (slot 0, pages 2-3) = $8000-$FFFF = 32768 bytes')
print(f'Game needs: {len(game)} bytes')
print(f'Shortfall:  {len(game) - 32768} bytes')
print()
print('MSX-DOS "all RAM" mode gives the full $0000-$FFFF = 65536 bytes')
print('  -> game at $0000 works with zero relocation (Spectrum addrs intact)')
print()
print('With main RAM only ($8000-$FFFF), the game must be relocated')
print(f'  Spectrum $6504 -> MSX $8000  (shift +${0x8000-0x6504:04X})')
print(f'  Top reference $FFFF -> MSX ${0xFFFF + (0x8000-0x6504):04X} (overflow!)')
