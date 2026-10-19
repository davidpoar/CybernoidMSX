// Test harness for the Cybernoid MSX .COM executable.
//
// The .COM is loaded at $0100 in MSX RAM (as MSX-DOS does), then:
//   1. the stub copies game part 1 to $6504 and part 2 to $8000
//   2. the init code switches to "all RAM" mode
//   3. the game starts at $6504
//
// A tiny fake VDP (16K of VRAM) records everything written to port $98
// so we can verify the video conversion.

using Z80;

namespace CybernoidTest;

/// <summary>Minimal TMS9918 model, enough to check what the port writes do.
///
/// Command port ($99) protocol:
///   * register write : value first, then $80|reg
///   * VRAM write    : address LSB first, then $40|addrMSB
/// </summary>
class FakeVdp
{
    public byte[] Vram = new byte[16384];
    public byte[] Regs = new byte[8];
    public int Prev;              // previous value written to $99
    public bool HaveLsb;          // waiting for the second byte of a pair
    public int Lsb;
    public int VramAddress;
    public bool InVramMode;       // true = data port writes go to VRAM
    public int VramWrites;        // counter for diagnostics
    public int CmdWrites;         // counter for diagnostics
    public List<int> AddrTrace = new();

    public void Write(int port, byte value)
    {
        if (port == 0x98)
        {
            VramWrites++;
            if (InVramMode)
            {
                Vram[VramAddress & 0x3FFF] = value;
                VramAddress = (VramAddress + 1) & 0x3FFF;
            }
        }
        else if (port == 0x99)
        {
            CmdWrites++;
            if (AddrTrace.Count < 12) AddrTrace.Add(value);

            if (!HaveLsb)
            {
                // first byte of a pair: address LSB, or a register value
                Lsb = value;
                HaveLsb = true;
            }
            else
            {
                int msb = value;
                int addr = ((msb & 0x3F) << 8) | Lsb;
                if ((msb & 0x80) != 0)
                {
                    // register write: the value was the first byte
                    Regs[msb & 0x07] = (byte)Lsb;
                    InVramMode = false;
                }
                else
                {
                    VramAddress = addr;
                    InVramMode = (msb & 0x40) != 0;
                }
                HaveLsb = false;
            }
            Prev = value;
        }
    }
}

class ComTest
{
    static int failures = 0;

    static void Check(bool ok, string label, string detail = "")
    {
        Console.WriteLine($"  [{(ok ? "PASS" : "FAIL")}] {label}{(detail.Length > 0 ? " - " + detail : "")}");
        if (!ok) failures++;
    }

    public static int Run()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        string comPath = Path.Combine(buildDir, "cybernoid.com");

        if (!File.Exists(comPath))
        {
            Console.WriteLine($"ERROR: {comPath} not found. Run msx/scripts/build.py first.");
            return 1;
        }

        byte[] com = File.ReadAllBytes(comPath);
        Console.WriteLine($"Cybernoid .COM test harness ({com.Length} bytes)\n");

        // Read the routine addresses from the build's symbol file so the
        // test does not have to hard-code them.
        ushort syncRows = 0x04F5;
        string symPath = Path.Combine(buildDir, "com_video.sym");
        if (File.Exists(symPath))
        {
            foreach (var line in File.ReadAllLines(symPath))
            {
                var parts = line.Trim().Split();
                if (parts.Length >= 3 && parts[0] == "MSX_VIDEO_SYNC_ROWS")
                    syncRows = (ushort)Convert.ToInt32(parts[2].TrimEnd('H'), 16);
            }
        }
        Console.WriteLine($"  MSX_VIDEO_SYNC_ROWS = ${syncRows:X4}\n");

        // ------------------------------------------------------------------
        Console.WriteLine("1. Load the .COM into RAM at $0100");
        // ------------------------------------------------------------------
        byte[] ram = new byte[65536];
        byte[] bios = new byte[32768];
        bios[0] = 0xC3; bios[1] = 0x00; bios[2] = 0x01;   // JP $0100
        for (int i = 3; i < bios.Length; i++) bios[i] = 0xC9;

        var bus = new MsxBus { Ram = ram, Bios = bios, SlotRegister = 0xFF };
        var vdp = new FakeVdp();
        byte[] keyMatrix = new byte[16];
        for (int i = 0; i < 16; i++) keyMatrix[i] = 0xFF;
        byte ppiC = 0x10;

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = 0xFF;

        cpu.OnInputPort = (port, cyc) =>
        {
            switch (port & 0xFF)
            {
                case 0xA9: return keyMatrix[ppiC & 0x0F];
                case 0xAA: return ppiC;
                case 0x99: return 0x00;   // VDP status
                default: return 0xFF;
            }
        };
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            switch (port & 0xFF)
            {
                case 0xA8:
                    bus.SlotRegister = value;
                    cpu.SlotRegister = value;
                    break;
                case 0xAA:
                    ppiC = value;
                    break;
                case 0x98:
                case 0x99:
                    vdp.Write(port & 0xFF, value);
                    break;
            }
        };

        // MSX-DOS loads the .COM payload (everything after the 256 byte
        // header) at $0100.
        Array.Copy(com, 256, ram, 0x0100, com.Length - 256);
        Check(ram[0x0100] == 0xF3, "Stub starts at $0100 (DI)",
              $"${ram[0x0100]:X2}");
        Check(ram[0x0800] == 0xF3, "Game part 1 at $0800 (DI)",
              $"${ram[0x0800]:X2}");
        // Spectrum $8000 is the start of the graphics data (block 7);
        // the first byte happens to be zero, so just check the region
        // is present.
        bool part2Present = ram[0x2300] == 0x00 && ram[0x2310] != 0x00;
        Check(part2Present, "Game part 2 present at $2300 (graphics data)",
              $"${ram[0x2310]:X2}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("2. Run the stub");
        // ------------------------------------------------------------------
        cpu.PC = 0x0100;
        cpu.SP = 0xF380;
        cpu.IFF1 = false;
        for (int i = 0; i < 200000; i++) cpu.Step();

        Console.WriteLine($"  PC = ${cpu.PC:X4}  slot = ${bus.SlotRegister:X2}  "
                        + $"I = ${cpu.I:X2}  IM = {cpu.InterruptMode}");

        Check(bus.SlotRegister == 0xFF, "Switched to all-RAM mode",
              $"slot register = ${bus.SlotRegister:X2}");
        Check(ram[0x6504] == 0xF3, "Game part 1 installed at $6504",
              $"${ram[0x6504]:X2}");
        Check(ram[0x8000] == 0x00 && ram[0x8010] != 0x00,
              "Game part 2 installed at $8000",
              $"${ram[0x8010]:X2}");
        Check(cpu.PC >= 0x6504, "PC in the game",
              $"PC = ${cpu.PC:X4}");
        Check(cpu.InterruptMode == 2, "IM 2 active", $"IM = {cpu.InterruptMode}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("3. Patches applied");
        // ------------------------------------------------------------------
        ushort kbd = (ushort)(ram[0x65ED + 1] | (ram[0x65ED + 2] << 8));
        Check(ram[0x65ED] == 0xCD && kbd == 0x0200,
              "IN A,($FE) at $65ED -> CALL $0200 (MSX_KBD_READ)",
              $"${ram[0x65ED]:X2} ${kbd:X4}");
        ushort bee = (ushort)(ram[0x651F + 1] | (ram[0x651F + 2] << 8));
        Check(ram[0x651F] == 0xCD && bee == 0x027F,
              "OUT ($FE),A at $651F -> CALL $027F (MSX_BEEPER)",
              $"${ram[0x651F]:X2} ${bee:X4}");
        ushort bee2 = (ushort)(ram[0x8637 + 1] | (ram[0x8637 + 2] << 8));
        Check(ram[0x8637] == 0xCD && bee2 == 0x027F,
              "OUT ($FE),A at $8637 -> CALL $027F",
              $"${ram[0x8637]:X2} ${bee2:X4}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("4. Video tables built");
        // ------------------------------------------------------------------
        // The name table at VRAM $3800 must contain 0..31 repeated 24 times.
        bool nameOk = true;
        for (int row = 0; row < 24; row++)
            for (int col = 0; col < 32; col++)
                if (vdp.Vram[0x3800 + row * 32 + col] != (byte)col)
                    nameOk = false;
        Check(nameOk, "Name table at VRAM $3800 = column indices 0..31 x24");

        // The colour conversion table lives in RAM at $05C1.
        // Spectrum attribute 0 = black ink on black paper -> MSX $11.
        Check(ram[0x05C1] == 0x11,
              "Colour conversion table built (attr 0 -> $11)",
              $"${ram[0x05C1]:X2}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("5. Video sync copies the screen to the VDP");
        // ------------------------------------------------------------------
        // Done early: the game's stack grows down from $FFFF and would
        // eventually overwrite any probe we leave in low memory.
        //
        // The probe is a plain CALL: we push a return address and point
        // the PC at the routine.
        // The probe lives in $0020-$00FF: the game sets SP=$0000, so the
        // stack only reaches that area after it has wrapped around the
        // whole address space.
        ram[0x4000] = 0xA5;
        ram[0x4001] = 0x5A;
        ram[0x0020] = 0x3E; ram[0x0021] = 24;            // LD A,24
        ram[0x0022] = 0xCD; ram[0x0023] = (byte)(syncRows & 0xFF);
        ram[0x0024] = (byte)((syncRows >> 8) & 0xFF);     // CALL sync
        ram[0x0025] = 0xC3; ram[0x0026] = 0x28; ram[0x0027] = 0x00;  // JP $0028
        ram[0x0028] = 0xC3; ram[0x0029] = 0x28; ram[0x002A] = 0x00;  // spin
        cpu.PC = 0x0020;
        cpu.SP = 0xFF80;
        ClearHalted(cpu);
        cpu.IFF1 = false;
        int vwBefore = vdp.VramWrites;
        int cwBefore = vdp.CmdWrites;
        vdp.AddrTrace.Clear();
        for (int i = 0; i < 400000; i++) cpu.Step();
        Console.WriteLine($"  VDP writes during the probe: "
                        + $"{vdp.VramWrites - vwBefore} data, "
                        + $"{vdp.CmdWrites - cwBefore} command");
        Console.WriteLine($"  first command bytes: "
                        + string.Join(", ", vdp.AddrTrace.Select(v => $"${v:X2}")));
        Console.WriteLine($"  screen buffer $4000 = ${ram[0x4000]:X2}");

        Check(vdp.Vram[0] == 0xA5 && vdp.Vram[1] == 0x5A,
              "Video sync copies the screen buffer to the pattern table",
              $"VRAM[0] = ${vdp.Vram[0]:X2} VRAM[1] = ${vdp.Vram[1]:X2}");

        // The colour table must hold the converted attribute of row 0.
        byte attr = ram[0x5800];
        byte expected = ram[0x05C1 + attr];   // COLTAB[attr]
        Check(vdp.Vram[0x2000] == expected,
              "Colour table holds the converted attribute of row 0",
              $"attr = ${attr:X2} -> VRAM[$2000] = ${vdp.Vram[0x2000]:X2} "
              + $"(expected ${expected:X2})");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("6. Keyboard in the running game");
        // ------------------------------------------------------------------
        keyMatrix[8] = 0xFE;    // SPACE pressed
        ram[0x0020] = 0x3E; ram[0x0021] = 0xF7;
        ram[0x0022] = 0xCD; ram[0x0023] = 0x00; ram[0x0024] = 0x02;
        ram[0x0025] = 0xC3; ram[0x0026] = 0x28; ram[0x0027] = 0x00;
        ram[0x0028] = 0xC3; ram[0x0029] = 0x28; ram[0x002A] = 0x00;
        cpu.PC = 0x0020;
        cpu.SP = 0xFF80;
        ClearHalted(cpu);
        cpu.IFF1 = false;
        for (int i = 0; i < 20000; i++) cpu.Step();
        Check((cpu.A & 0x01) == 0, "SPACE detected through the patched routine",
              $"A = ${cpu.A:X2}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("7. Game runs");
        // ------------------------------------------------------------------
        cpu.IFF1 = true;
        cpu.PC = 0x6504;
        for (int i = 0; i < 3000000; i++)
        {
            cpu.Step();
            if (cpu.Halted) break;
        }
        Console.WriteLine($"  PC = ${cpu.PC:X4}  Halted = {cpu.Halted}");
        Check(cpu.PC >= 0x6504, "PC still inside the game",
              $"PC = ${cpu.PC:X4}");

        Console.WriteLine();
        Console.WriteLine(new string('=', 62));
        if (failures == 0)
        {
            Console.WriteLine("ALL TESTS PASSED");
            return 0;
        }
        else
        {
            Console.WriteLine($"{failures} TEST(S) FAILED");
            return 1;
        }
    }

    static void ClearHalted(Z80.Z80 cpu)
    {
        typeof(Z80.Z80).GetField("Halted",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance)?.SetValue(cpu, false);
    }
}
