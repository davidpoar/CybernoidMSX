"""Verify the post-LDDR memory layout of the Cybernoid game.

The loader's LDDR copies src $6104-$FBFF -> dest $6504-$FFFF, i.e.
dest = src + $4000.  That means:

  post-LDDR $6504-$7FFF  <- pre-LDDR $2504-$3FFF  (block 9 start)
  post-LDDR $8000-$9AFF  <- pre-LDDR $4000-$5AFF  (the Spectrum screen!)
  post-LDDR $9B00-$BFFF  <- pre-LDDR $5B00-$7FFF  (BASIC area + block 9)
  post-LDDR $C000-$D12C  <- pre-LDDR $8000-$912C  (block 7, the graphics)
  post-LDDR $D12D-$FFFF  <- pre-LDDR $912D-$FFFF  (block 9 tail)

This script prints what each region actually contains.
"""
import sys
from pathlib import Path

MEM = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')
with open(MEM, 'rb') as f:
    mem = f.read()


def region(name, lo, hi):
    data = mem[lo - 0x4000:hi - 0x4000 + 1]
    nonzero = sum(1 for b in data if b != 0)
    print(f'  ${lo:04X}-${hi:04X}  {len(data):6d} bytes  '
          f'{nonzero:6d} non-zero  {100*nonzero//max(1,len(data)):3d}%  {name}')
    return data


print('Post-LDDR memory layout (the state when the game starts):\n')
region('game code / data', 0x6504, 0x7FFF)
region('copy of the Spectrum screen', 0x8000, 0x9AFF)
region('BASIC area + block 9 head', 0x9B00, 0xBFFF)
region('block 7 (graphics data)', 0xC000, 0xD12C)
region('block 9 tail', 0xD12D, 0xFFFF)

print()
print('  => The real game code lives at $6504-$7FFF and $9B00-$FFFF.')
print('  => $8000-$9AFF is a stale copy of the (never initialised) screen.')
print('  => The "graphics" data (block 7) is at $C000-$D12C.')

# Look for the block 7 signature to confirm
print()
blk7 = mem[0xC000 - 0x4000:0xC000 - 0x4000 + 64]
print('  block 7 first 64 bytes at $C000:')
for row in range(4):
    a = row * 16
    hexs = ' '.join(f'{blk7[a+i]:02X}' for i in range(16))
    asc = ''.join(chr(blk7[a+i]) if 32 <= blk7[a+i] < 127 else '.' for i in range(16))
    print(f'    ${0xC000+row*16:04X}: {hexs}  {asc}')
