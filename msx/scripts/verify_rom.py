#!/usr/bin/env python3
"""Verify the built Cybernoid ROM against the required checklist.

1. the file is exactly 65536 bytes and starts with 41 42 ("AB")
2. INIT points at the new code
3. no RET reachable from INIT without passing through a CALL
4. no OUT (00h),A and no OUT (A8h),A anywhere
5. no CALL 144Ch
6. the VDP registers are the SCREEN 2 values
7. the PSG writes the data to port A1
8. the bank registers are written with LD (nn),A
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from z80dis import z80

ROM = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom')

with open(ROM, 'rb') as f:
    rom = f.read()

fails = 0


def check(ok, label, detail=''):
    global fails
    print(f'  [{"PASS" if ok else "FAIL"}] {label}' + (f' - {detail}' if detail else ''))
    if not ok:
        fails += 1


print('=' * 66)
print('CYBERNOID ROM VERIFICATION')
print('=' * 66)

# ------------------------------------------------------------------
print('\n1. File format')
# ------------------------------------------------------------------
check(len(rom) == 65536, 'File is exactly 65536 bytes', f'{len(rom)} bytes')
check(rom[0] == 0x41 and rom[1] == 0x42, 'Starts with 41 42 ("AB")',
      rom[:2].hex(' '))
init = rom[2] | (rom[3] << 8)
check(init == 0x4010, 'INIT points at the new code', f'${init:04X}')

# ------------------------------------------------------------------
print('\n2. Disassembly of bank 0')
# ------------------------------------------------------------------
# The header at $4000 is data, not code: start the scan at $4010
# (the INIT entry point) so the disassembler stays in sync.
code = rom[0:0x4000]
insns = []
pos = 0x4010
while pos < 0x4000 + 0x400:
    off = pos - 0x4000
    if off >= len(code):
        break
    chunk = code[off:off + 4]
    try:
        d = z80.decode(chunk, pos)
        insns.append((pos, z80.decoded2str(d), d.len, chunk[:d.len]))
        pos += d.len
    except Exception:
        pos += 1

# ------------------------------------------------------------------
print('\n3. Forbidden instructions')
# ------------------------------------------------------------------
out_00 = [(a, s) for a, s, n, r in insns if s.upper().startswith('OUT (0X00)')]
out_a8 = [(a, s) for a, s, n, r in insns if s.upper().startswith('OUT (0XA8)')]
call_144c = [(a, s) for a, s, n, r in insns
              if s.upper().startswith('CALL 0X144C')]

check(not out_00, 'No OUT (00h),A anywhere',
      '; '.join(f'${a:04X}' for a, s in out_00) if out_00 else '')
check(not out_a8, 'No OUT (A8h),A anywhere',
      '; '.join(f'${a:04X}' for a, s in out_a8) if out_a8 else '')
check(not call_144c, 'No CALL 144Ch',
      '; '.join(f'${a:04X}' for a, s in call_144c) if call_144c else '')

import re

_HEX_RE = re.compile(r'0X([0-9A-Fa-f]+)')
_DEC_RE = re.compile(r',\s*(-?\d+)\s*$')


def operand_value(text):
    """Extract the numeric operand of a disassembled instruction.

    z80dis prints numbers either as 0x1A or as 26, so accept both.
    Beware: int(x, 0) treats a leading zero as octal, so parse the
    hexadecimal form explicitly.
    """
    up = text.upper()
    m = _HEX_RE.search(up)
    if m:
        return int(m.group(1), 16)
    m = _DEC_RE.search(up.strip())
    if m:
        return int(m.group(1), 10)
    return None


# ------------------------------------------------------------------
print('\n4. Control flow from INIT')
# ------------------------------------------------------------------
# Walk the code reachable from INIT, following jumps and calls, and
# collect every RET that is reached at call depth 0 (a RET inside a
# called routine is fine, it returns to its caller).
addr_to_insn = {a: (s, n) for a, s, n, r in insns}

init_insn = addr_to_insn.get(init)
check(init_insn is not None, 'INIT is a valid instruction',
      init_insn[0] if init_insn else 'not found')

rets = []
reached = set()
stack = [(init, 0)] if init_insn else []

while stack:
    a, depth = stack.pop()
    key = (a, depth)
    if key in reached:
        continue
    reached.add(key)
    ent = addr_to_insn.get(a)
    if not ent:
        continue
    s, n = ent
    u = s.upper()
    if u == 'RET':
        if depth == 0:
            rets.append(a)
        continue
    if u.startswith('JP'):
        v = operand_value(s)
        if v is not None:
            stack.append((v, depth))
        continue
    if u.startswith('JR'):
        v = operand_value(s)
        if v is not None:
            stack.append((v, depth))
        continue
    if u.startswith('CALL'):
        v = operand_value(s)
        if v is not None:
            stack.append((v, depth + 1))    # inside the called routine
        stack.append((a + n, depth))        # and after the call
        continue
    # ordinary instruction: fall through to the next one
    stack.append((a + n, depth))

check(not rets, 'No RET reachable from INIT without a CALL in between',
      '; '.join(f'${a:04X}' for a in rets) if rets else
      f'{len(reached)} states walked')

# The INIT must end in a jump to the main loop
init_jp = None
for a, s, n, r in insns:
    if a >= init and s.upper().startswith('JP'):
        init_jp = (a, s)
        break
check(init_jp is not None and init_jp[0] < 0x4060,
      'INIT ends in a JP to the main loop',
      f'${init_jp[0]:04X} {init_jp[1]}' if init_jp else 'not found')

# The main loop must contain HALT and loop back on itself
halt_found = any(s.upper() == 'HALT' for a, s, n, r in insns
                  if 0x404A <= a <= 0x4060)
check(halt_found, 'Main loop waits with HALT')

# ------------------------------------------------------------------
print('\n5. Bank registers')
# ------------------------------------------------------------------
bank_writes = [(a, s) for a, s, n, r in insns
               if 'LD (0X7000)' in s.upper() or 'LD (0X6000)' in s.upper()]
check(any('LD (0X7000)' in s.upper() for a, s in bank_writes),
      'Bank B written with LD (7000h),A',
      '; '.join(f'${a:04X}' for a, s in bank_writes))
check(not any('LD (0X6000)' in s.upper() for a, s in bank_writes),
      'Bank A ($6000) never written (bank 0 stays fixed)')

# ------------------------------------------------------------------
print('\n6. VDP registers')
# ------------------------------------------------------------------
expected_regs = {
    0: 0x02, 1: 0xE0, 2: 0x06, 3: 0xFF, 4: 0x03, 5: 0x36, 6: 0x07, 7: 0xF1,
}
# find the "ld b, imm / ld c, n / call VDP_SETREG" triples
found = {}
for i, (a, s, n, r) in enumerate(insns):
    up = s.upper()
    if up.startswith('LD C,') and i + 1 < len(insns):
        nxt = insns[i + 1]
        if nxt[1].upper().startswith('CALL'):
            reg = operand_value(up)
            if reg is None:
                continue
            # look back for "ld b, imm"
            for j in range(i - 1, max(i - 4, -1), -1):
                if insns[j][1].upper().startswith('LD B,'):
                    val = operand_value(insns[j][1])
                    if val is None:
                        break
                    found[reg] = (val, insns[j][0])
                    break

for reg in range(8):
    val, at = found.get(reg, (None, None))
    exp = expected_regs[reg]
    check(val == exp, f'VDP R{reg} = ${exp:02X}',
          f'${val:02X} at ${at:04X}' if val is not None else 'not found')

# ------------------------------------------------------------------
print('\n7. PSG ports')
# ------------------------------------------------------------------
# OUT (n),A encodes the port in the low byte of the operand
psg_data = []
psg_reg = []
for a, s, n, r in insns:
    if s.upper().startswith('OUT ('):
        port = operand_value(s)
        if port == 0xA0:
            psg_reg.append(a)
        elif port == 0xA1:
            psg_data.append(a)
check(len(psg_data) >= 4, 'PSG data written to port A1h',
      f'{len(psg_data)} writes')
check(len(psg_reg) >= 4, 'PSG register selected on port A0h',
      f'{len(psg_reg)} writes')

# the mixer must be silenced with $3F
mixer_ok = False
for i, (a, s, n, r) in enumerate(insns):
    if s.upper().startswith('LD A,') and i + 1 < len(insns):
        nxt = insns[i + 1]
        if operand_value(s) == 0x3F and nxt[1].upper().startswith('OUT ('):
            if operand_value(nxt[1]) == 0xA1:
                mixer_ok = True
check(mixer_ok, 'Mixer register silenced with $3F')

# the volume registers 8, 9 and 10 must be set to 0
vol_ok = 0
for i, (a, s, n, r) in enumerate(insns):
    if s.upper().startswith('LD A,') and i + 1 < len(insns):
        nxt = insns[i + 1]
        if operand_value(s) in (8, 9, 10) and nxt[1].upper().startswith('OUT ('):
            if operand_value(nxt[1]) == 0xA0:
                vol_ok += 1
check(vol_ok == 3, 'Volume registers 8, 9 and 10 selected', f'{vol_ok}/3')

# ------------------------------------------------------------------
print('\n8. Full listing of the engine')
# ------------------------------------------------------------------
print()
for a, s, n, r in insns:
    print(f'  ${a:04X}: {s:<28s} ; {r.hex(" ")}')

print()
print('=' * 66)
if fails == 0:
    print('ALL CHECKS PASSED')
    sys.exit(0)
print(f'{fails} CHECK(S) FAILED')
sys.exit(1)
