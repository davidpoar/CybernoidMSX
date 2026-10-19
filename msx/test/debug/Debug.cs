// Focused debug of the MSX_KBD_READ routine.
using Z80;
using System.Text;

namespace CybernoidTest;

class Debug
{
    public static void Run()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        byte[] rom = File.ReadAllBytes(Path.Combine(buildDir, "cybernoid.rom"));

        byte[] ram = new byte[65536];
        byte[] cart = new byte[32768];
        Array.Copy(rom, cart, 16384);

        byte[] bios = new byte[32768];
        bios[0] = 0xC3; bios[1] = 0x10; bios[2] = 0x40;
        for (int i = 3; i < bios.Length; i++) bios[i] = 0xC9;

        var bus = new MsxBus
        {
            Ram = ram,
            Cartridge = cart,
            Bios = bios,
            SlotRegister = 0xF4
        };

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = 0xF4;

        byte[] keyMatrix = new byte[16];
        for (int i = 0; i < 16; i++) keyMatrix[i] = 0xFF;
        keyMatrix[8] = 0xFE;   // SPACE pressed

        byte ppiC = 0x10;
        List<string> log = new();

        cpu.OnInputPort = (port, cyc) =>
        {
            byte v;
            switch (port & 0xFF)
            {
                case 0xA9:
                    v = keyMatrix[ppiC & 0x0F];
                    log.Add($"IN $A9 (row {ppiC & 0x0F}) = ${v:X2}");
                    return v;
                case 0xAA:
                    log.Add($"IN $AA = ${ppiC:X2}");
                    return ppiC;
                default:
                    return 0xFF;
            }
        };
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xAA)
            {
                ppiC = value;
                log.Add($"OUT $AA = ${value:X2} (row {value & 0x0F})");
            }
        };

        // LD A,$F7 ; CALL $4040 ; HALT
        ram[0xFF00] = 0x3E; ram[0xFF01] = 0xF7;
        ram[0xFF02] = 0xCD; ram[0xFF03] = 0x40; ram[0xFF04] = 0x40;
        ram[0xFF05] = 0x76;
        cpu.PC = 0xFF00;
        cpu.SP = 0xFF80;
        cpu.IFF1 = false;

        for (int i = 0; i < 20000; i++) cpu.Step();

        Console.WriteLine($"A = ${cpu.A:X2}  PC = ${cpu.PC:X4}  Halted = {cpu.Halted}");
        Console.WriteLine("I/O trace:");
        foreach (var l in log.Take(30)) Console.WriteLine("  " + l);
        if (log.Count > 30) Console.WriteLine($"  ... ({log.Count} total)");

        Console.WriteLine();
        Console.WriteLine("Raw bytes of MSX_KBD_READ ($4040):");
        for (int i = 0; i < 48; i++)
        {
            if (i % 16 == 0) Console.Write($"  ${0x4040 + i:X4}:");
            Console.Write($" {cart[0x40 + i]:X2}");
            if (i % 16 == 15) Console.WriteLine();
        }
        Console.WriteLine();
    }

    /// Run the whole game and dump the Spectrum screen buffer so we can
    /// see how many distinct 8x8 patterns it uses.
    public static void RunGameAndDumpScreen()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        byte[] rom = File.ReadAllBytes(Path.Combine(buildDir, "cybernoid.rom"));
        byte[] bin = File.ReadAllBytes(Path.Combine(buildDir, "cybernoid.bin"));

        byte[] ram = new byte[65536];
        byte[] cart = new byte[32768];
        Array.Copy(rom, cart, 16384);

        byte[] bios = new byte[32768];
        bios[0] = 0xC3; bios[1] = 0x10; bios[2] = 0x40;
        for (int i = 3; i < bios.Length; i++) bios[i] = 0xC9;

        var bus = new MsxBus
        {
            Ram = ram,
            Cartridge = cart,
            Bios = bios,
            SlotRegister = 0xF4
        };

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = 0xF4;

        byte[] keyMatrix = new byte[16];
        for (int i = 0; i < 16; i++) keyMatrix[i] = 0xFF;
        byte ppiC = 0x10;

        cpu.OnInputPort = (port, cyc) =>
        {
            switch (port & 0xFF)
            {
                case 0xA9: return keyMatrix[ppiC & 0x0F];
                case 0xAA: return ppiC;
                default: return 0xFF;
            }
        };
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xAA) ppiC = value;
        };

        // Load game part 2 at $8000
        byte[] game = new byte[bin.Length - 8];
        Array.Copy(bin, 7, game, 0, game.Length);
        Array.Copy(game, 0, ram, 0x8000, game.Length);

        // Copy game part 1 from the cartridge ROM to RAM at the SAME
        // addresses ($6504-$7FFF) - this is what the real loader does.
        for (int a = 0x6504; a <= 0x7FFF; a++)
            ram[a] = cart[a - 0x4000];

        // Switch to all-RAM so the screen buffer at $4000 is writable RAM
        bus.SlotRegister = 0xFF;
        cpu.SlotRegister = 0xFF;

        // Run the game: jump to $6504 (entry in RAM now)
        cpu.PC = 0x6504;
        cpu.SP = 0xF380;
        cpu.IFF1 = true;

        Console.WriteLine("Running the game for 2,000,000 instructions...");
        for (int i = 0; i < 2_000_000; i++)
        {
            cpu.Step();
            if (cpu.Halted) { Console.WriteLine($"  HALTED at ${cpu.PC:X4} after {i} steps"); break; }
        }
        Console.WriteLine($"  PC = ${cpu.PC:X4}  I = ${cpu.I:X2}  IM = {cpu.InterruptMode}");
        Console.WriteLine($"  Halted = {cpu.Halted}");

        // Dump the Spectrum screen buffer ($4000-$57FF pixels, $5800-$5AFF attrs)
        var patterns = new Dictionary<string, int>();
        int cells = 0, blank = 0;
        for (int row = 0; row < 24; row++)
        {
            for (int col = 0; col < 32; col++)
            {
                int src = 0x4000 + (row / 8) * 0x100 + (row % 8) * 0x20 + col * 8;
                var pat = new byte[8];
                for (int i = 0; i < 8; i++) pat[i] = ram[src + i];
                var key = Convert.ToHexString(pat);
                if (!patterns.ContainsKey(key)) patterns[key] = patterns.Count;
                if (pat.All(b => b == 0)) blank++;
                cells++;
            }
        }
        Console.WriteLine($"\nScreen buffer analysis ({cells} cells):");
        Console.WriteLine($"  distinct 8x8 patterns : {patterns.Count}");
        Console.WriteLine($"  blank cells          : {blank}");
        Console.WriteLine($"  MSX pattern slots needed (max 256): {(patterns.Count <= 256 ? "OK" : "TOO MANY")}");

        // Attributes
        var attrs = new HashSet<byte>();
        for (int i = 0; i < 0x300; i++) attrs.Add(ram[0x5800 + i]);
        Console.WriteLine($"  distinct attributes  : {attrs.Count} -> {string.Join(",", attrs.Select(a => a.ToString("X2")))}");

        // Dump a small part of the screen for visual inspection
        Console.WriteLine("\nScreen rows 8-9 (bytes):");
        for (int row = 8; row < 10; row++)
        {
            int src = 0x4000 + (row / 8) * 0x100 + (row % 8) * 0x20;
            var line = new StringBuilder();
            for (int i = 0; i < 32; i++)
                line.Append($"{ram[src + i * 8]:X2} ");
            Console.WriteLine($"  row {row}: {line}");
        }

        // Save the screen for further analysis
        File.WriteAllBytes(
            Path.Combine(Path.GetTempPath(), "cybernoid_screen.bin"),
            ram.Skip(0x4000).Take(0x1B00).ToArray());
        Console.WriteLine($"\nScreen buffer saved to {Path.Combine(Path.GetTempPath(), "cybernoid_screen.bin")}");
    }
}
