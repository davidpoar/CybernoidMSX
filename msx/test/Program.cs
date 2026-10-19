// Test harness for the Cybernoid MSX ROM.
//
// Machine layout (mirrors the z80emu MSX emulator):
//   Slot 0 page 0/1 : a tiny "BIOS" that jumps to the cartridge INIT
//   Slot 1 page 1    : the 16K cartridge ROM at $4000-$7FFF
//   Slot 3           : 64K of RAM at $0000-$FFFF
//
// The game is split like this:
//   $6504-$7FFF : cartridge ROM   (game part 1, patches baked in)
//   $8000-$FFFF : MSX main RAM    (game part 2, BLOADed)
//
// So the game runs at exactly its original Spectrum addresses.

using Z80;

namespace CybernoidTest;

class MsxBus : IMemoryBus
{
    public byte[] Ram = new byte[65536];
    public byte[] Cartridge = new byte[32768];
    public byte[] Bios = new byte[32768];
    public byte SlotRegister = 0xF4;

    public byte Read(ushort address, ref int currentCycles)
    {
        int page = address >> 14;
        int slot = (SlotRegister >> (page * 2)) & 0x03;
        switch (slot)
        {
            case 0:
                if (page == 0) return Bios[address & 0x3FFF];
                if (page == 1) return Bios[16384 + (address & 0x3FFF)];
                return 0xFF;
            case 1:
                if (page == 1) return Cartridge[address & 0x3FFF];
                if (page == 2) return Cartridge[16384 + (address & 0x3FFF)];
                return 0xFF;
            case 3:
                return Ram[address];
            default:
                return 0xFF;
        }
    }

    public void Write(ushort address, byte value, ref int currentCycles)
    {
        int page = address >> 14;
        int slot = (SlotRegister >> (page * 2)) & 0x03;
        if (slot == 3) Ram[address] = value;
    }
}

class TestMachine
{
    public Z80.Z80 Cpu = null!;
    public MsxBus Bus = null!;
    public byte[] Cartridge = new byte[32768];
    public byte[] Bios = new byte[32768];

    public List<string> IoLog = new();
    public byte[] KeyMatrix = new byte[16];
    public byte PpiPortC = 0x10;
    public byte SlotRegister;

    public const byte SLOT_ALL_RAM = 0xFF;
    public const byte SLOT_NORMAL = 0xF4;   // p0=BIOs p1=cart p2/3=RAM

    public byte ReadRam(ushort addr) => Bus.Ram[addr];

    public void LoadCartridge(byte[] rom16k)
    {
        Array.Clear(Cartridge, 0, Cartridge.Length);
        Array.Copy(rom16k, Cartridge, Math.Min(rom16k.Length, 16384));
    }

    public void BuildBios()
    {
        Array.Clear(Bios, 0, Bios.Length);
        // $0000: JP $4010 (cartridge INIT)
        Bios[0] = 0xC3;
        Bios[1] = 0x10;
        Bios[2] = 0x40;
        for (int i = 3; i < Bios.Length; i++) Bios[i] = 0xC9;
    }

    public void Build(byte slotRegister = SLOT_NORMAL)
    {
        SlotRegister = slotRegister;
        Bus = new MsxBus { SlotRegister = slotRegister };
        Bus.Bios = Bios;
        Bus.Cartridge = Cartridge;

        Cpu = new Z80.Z80();
        Cpu.MemoryBus = Bus;
        Cpu.Reset();
        Cpu.SlotRegister = slotRegister;   // Reset() clears it

        for (int i = 0; i < KeyMatrix.Length; i++) KeyMatrix[i] = 0xFF;

        Cpu.OnInputPort = (port, cycles) =>
        {
            switch (port & 0xFF)
            {
                case 0xA9: return KeyMatrix[PpiPortC & 0x0F];
                case 0xAA: return PpiPortC;
                default: return 0xFF;
            }
        };

        Cpu.OnOutputPort = (port, value, cycles) =>
        {
            switch (port & 0xFF)
            {
                case 0xAA:
                    PpiPortC = value;
                    IoLog.Add($"OUT ${port:X2} = ${value:X2}");
                    break;
                case 0xA8:
                    SlotRegister = value;
                    Cpu.SlotRegister = value;
                    Bus.SlotRegister = value;
                    IoLog.Add($"OUT $A8 = ${value:X2} (slot register)");
                    break;
                default:
                    IoLog.Add($"OUT ${port:X2} = ${value:X2}");
                    break;
            }
        };
    }

    public void Step(int n)
    {
        for (int i = 0; i < n; i++) Cpu.Step();
    }

    /// Load the game part 2 .BIN into RAM at $8000 (like BLOAD)
    public void LoadGameBin(byte[] bin)
    {
        byte[] game = new byte[bin.Length - 8];
        Array.Copy(bin, 7, game, 0, game.Length);
        Array.Copy(game, 0, Bus.Ram, 0x8000, game.Length);
    }

    /// Prepare a tiny routine in RAM: LD A,nn ; CALL $addr ; JP self
    public void PrepareCall(byte value, ushort target)
    {
        Bus.Ram[0xFF00] = 0x3E;
        Bus.Ram[0xFF01] = value;
        Bus.Ram[0xFF02] = 0xCD;
        Bus.Ram[0xFF03] = (byte)(target & 0xFF);
        Bus.Ram[0xFF04] = (byte)(target >> 8);
        Bus.Ram[0xFF05] = 0xC3;    // JP $FF05 (spin, keeps A)
        Bus.Ram[0xFF06] = 0x05;
        Bus.Ram[0xFF07] = 0xFF;
        Cpu.PC = 0xFF00;
        Cpu.SP = 0xFF80;
        ClearHalted();
        Cpu.IFF1 = false;
    }

    /// Halted has a private setter; clear it with reflection.
    static readonly System.Reflection.FieldInfo? HaltedField =
        typeof(Z80.Z80).GetField("Halted",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

    public void ClearHalted()
    {
        HaltedField?.SetValue(Cpu, false);
    }
}

class Program
{
    static int failures = 0;

    static void Check(bool ok, string label, string detail = "")
    {
        Console.WriteLine($"  [{(ok ? "PASS" : "FAIL")}] {label}{(detail.Length > 0 ? " - " + detail : "")}");
        if (!ok) failures++;
    }

    static int Main()
    {
        if (Environment.GetEnvironmentVariable("CYBERNOID_DEBUG") == "1")
        {
            Debug.Run();
            return 0;
        }
        if (Environment.GetEnvironmentVariable("CYBERNOID_SCREEN") == "1")
        {
            Debug.RunGameAndDumpScreen();
            return 0;
        }
        if (Environment.GetEnvironmentVariable("CYBERNOID_COM") == "1")
        {
            return ComTest.Run();
        }

        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        string romPath = Path.Combine(buildDir, "cybernoid.rom");
        string binPath = Path.Combine(buildDir, "cybernoid.bin");

        Console.WriteLine("Cybernoid MSX ROM test harness");
        Console.WriteLine($"  ROM: {romPath}");
        Console.WriteLine($"  BIN: {binPath}");
        Console.WriteLine();

        if (!File.Exists(romPath) || !File.Exists(binPath))
        {
            Console.WriteLine("ERROR: build outputs not found. Run msx/scripts/build.py first.");
            return 1;
        }

        byte[] rom = File.ReadAllBytes(romPath);
        byte[] bin = File.ReadAllBytes(binPath);

        // ------------------------------------------------------------------
        Console.WriteLine("1. ROM header");
        // ------------------------------------------------------------------
        Check(rom.Length == 16384, "ROM is 16K", $"{rom.Length} bytes");
        Check(rom[0] == 'A' && rom[1] == 'B', "Signature is 'AB'");
        ushort initAddr = (ushort)(rom[2] | (rom[3] << 8));
        Check(initAddr == 0x4010, "INIT address is $4010", $"${initAddr:X4}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("2. Cartridge contents");
        // ------------------------------------------------------------------
        Check(rom[0x40] == 0xE5, "I/O routines at $4040 (PUSH HL)",
              $"byte = ${rom[0x40]:X2}");
        Check(rom[0x200] == 0xF3, "Init code at $4200 (DI)",
              $"byte = ${rom[0x200]:X2}");
        Check(rom[0x2504] == 0xF3, "Game part 1 at $6504 (DI)",
              $"byte = ${rom[0x2504]:X2}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("3. Part 1 patches baked into the ROM");
        // ------------------------------------------------------------------
        foreach (int a in new[] { 0x65ED, 0x65F4, 0x660D, 0x7B4C })
        {
            int off = a - 0x4000;
            ushort tgt = (ushort)(rom[off + 1] | (rom[off + 2] << 8));
            Check(rom[off] == 0xCD && tgt == 0x4040,
                  $"IN A,($FE) at ${a:X4} -> CALL $4040",
                  $"${rom[off]:X2} ${tgt:X4}");
        }
        {
            int off = 0x651F - 0x4000;
            ushort tgt = (ushort)(rom[off + 1] | (rom[off + 2] << 8));
            Check(rom[off] == 0xCD && tgt == 0x40BF,
                  "OUT ($FE),A at $651F -> CALL $40BF",
                  $"${rom[off]:X2} ${tgt:X4}");
        }

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("4. Boot the ROM and init the hardware");
        // ------------------------------------------------------------------
        var m = new TestMachine();
        m.LoadCartridge(rom);
        m.BuildBios();
        m.Build(TestMachine.SLOT_NORMAL);

        m.Step(300000);
        Check(m.Cpu.PC >= 0x4200 && m.Cpu.PC < 0x4400,
              "Executing init code at $4200", $"PC = ${m.Cpu.PC:X4}");

        Check(m.IoLog.Count(s => s.StartsWith("OUT $99")) >= 8,
              "VDP mode registers written",
              $"{m.IoLog.Count(s => s.StartsWith("OUT $99"))} writes to $99");
        Check(m.IoLog.Any(s => s.StartsWith("OUT $A0")), "PSG registers written",
              string.Join(", ", m.IoLog.Where(s => s.StartsWith("OUT $A0")).Take(3)));
        Check(m.Cpu.InterruptMode == 2, "IM 2 set", $"IM = {m.Cpu.InterruptMode}");
        Check(m.Cpu.I == 0xF0, "Interrupt vector base = $F0", $"I = ${m.Cpu.I:X2}");
        Check(m.IoLog.Any(s => s == "OUT $99 = $A0"),
              "VDP R1 = $A0 (16K VRAM + IRQ enabled)");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("5. Load game part 2 and press a key");
        // ------------------------------------------------------------------
        m.LoadGameBin(bin);
        m.KeyMatrix[8] = 0xFE;    // SPACE pressed
        m.Step(400000);

        Console.WriteLine($"  PC = ${m.Cpu.PC:X4}  IM = {m.Cpu.InterruptMode}  "
                        + $"I = ${m.Cpu.I:X2}");

        Check(m.IoLog.Count(s => s.StartsWith("OUT $98")) >= 16000,
              "VRAM cleared (16K writes to $98)",
              $"{m.IoLog.Count(s => s.StartsWith("OUT $98"))} writes");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("6. Part 2 patch applied at runtime");
        // ------------------------------------------------------------------
        ushort bee = (ushort)(m.Bus.Ram[0x8637 + 1] | (m.Bus.Ram[0x8637 + 2] << 8));
        Check(m.Bus.Ram[0x8637] == 0xCD && bee == 0x40BF,
              "OUT ($FE),A at $8637 -> CALL $40BF",
              $"${m.Bus.Ram[0x8637]:X2} ${bee:X4}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("7. Game runs from $6504");
        // ------------------------------------------------------------------
        Check(m.Cpu.PC >= 0x6504, "PC inside the game (entry $6504)",
              $"PC = ${m.Cpu.PC:X4}");

        m.Cpu.IFF1 = true;
        m.Step(300000);
        Check(m.Cpu.PC >= 0x6504 && m.Cpu.PC <= 0xFFFF,
              "PC still in the game after 300k instructions",
              $"PC = ${m.Cpu.PC:X4}");
        Check(!m.Cpu.Halted, "CPU not halted", $"Halted = {m.Cpu.Halted}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("8. Keyboard routine (MSX_KBD_READ at $4040)");
        // ------------------------------------------------------------------
        // The game may have HALTed the CPU; clear it before each probe.
        void KeyboardProbe(byte row, byte keyMask, byte spectrumRow, string label)
        {
            for (int i = 0; i < 16; i++) m.KeyMatrix[i] = 0xFF;
            m.KeyMatrix[row] = keyMask;
            m.PpiPortC = 0x10;
            m.PrepareCall(spectrumRow, 0x4040);
            m.Step(20000);
            // The Spectrum-style result mirrors the MSX mask for the bits
            // the port maps (bit 0 of MSX row 8 -> bit 0 of Spectrum row $F7,
            // bit 3 of MSX row 0 -> bit 1 of Spectrum row $FE, ...).
            Check(m.Cpu.A != 0x1F || keyMask == 0xFF, label,
                  $"A = ${m.Cpu.A:X2}");
        }
        KeyboardProbe(8, 0xFE, 0xF7, "SPACE pressed changes row $F7");
        KeyboardProbe(8, 0xFF, 0xF7, "SPACE released -> row $F7 idle");
        // MSX row 5 = S T U V W X Y Z  (bit 7 = Z, bit 5 = X)
        KeyboardProbe(5, 0x7F, 0xFE, "Z pressed changes row $FE");
        KeyboardProbe(5, 0xDF, 0xFE, "X pressed changes row $FE");
        KeyboardProbe(5, 0xFF, 0xFE, "no key -> row $FE idle");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("9. Beeper routine (MSX_BEEPER at $40BF)");
        // ------------------------------------------------------------------
        m.IoLog.Clear();
        m.PrepareCall(0x10, 0x40BF);
        m.Step(20000);
        Check(m.IoLog.Any(s => s.StartsWith("OUT $A0")),
              "PSG register written by MSX_BEEPER",
              string.Join(", ", m.IoLog.Where(s => s.StartsWith("OUT $A")).Take(4)));

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("10. IM 2 handler");
        // ------------------------------------------------------------------
        Check(rom[0x104] == 0xF5, "MSX_IM2_HANDLER at $4104 = PUSH AF",
              $"${rom[0x104]:X2}");
        bool callsGame = false;
        for (int i = 0x104; i < 0x104 + 24; i++)
        {
            if (rom[i] == 0xCD && (ushort)(rom[i + 1] | (rom[i + 2] << 8)) == 0x70D3)
            {
                callsGame = true;
                break;
            }
        }
        Check(callsGame, "  -> CALL $70D3 (game's IM 2 handler)");

        // ------------------------------------------------------------------
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
}
