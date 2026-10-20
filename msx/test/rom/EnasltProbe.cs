// Empirically find the right ENASLT parameters.
//
// The BIOS ENASLT routine takes A = slot id and HL = address and rewrites
// the primary slot register.  We try a few combinations and report the
// resulting register, so we can see which one puts page 2 on our slot.
using Z80;

namespace CybernoidTest;

class EnasltProbe
{
    static byte Try(string biosPath, byte slotId, ushort address, byte initialReg)
    {
        byte[] bios = File.ReadAllBytes(biosPath);

        var bus = new RomBus();
        bus.Cart = new Ascii16Cartridge(new byte[65536]);
        bus.Slot0 = new BiosAndRamDevice(bios);
        bus.SlotRegister = initialReg;

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = initialReg;
        cpu.OnInputPort = (port, cyc) =>
            (port & 0xFF) == 0xA8 ? bus.SlotRegister : (byte)0xFF;
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xA8) bus.SlotRegister = value;
        };

        // Put a return address on the stack and call ENASLT
        cpu.SP = 0xF380;
        bus.Slot0.Ram[0xF380 - 0x8000] = 0x00;   // return to $0000
        bus.Slot0.Ram[0xF381 - 0x8000] = 0x00;
        cpu.PC = 0x0024;      // ENASLT entry
        cpu.A = slotId;
        cpu.HL = address;
        cpu.IFF1 = false;
        for (int i = 0; i < 5000; i++) cpu.Step();

        return bus.SlotRegister;
    }

    public static void Run()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        string biosPath = Path.Combine(buildDir, "msx.rom");

        // A real MSX: page 0 = slot 0 (BIOS), page 1 = slot 1 (cartridge),
        // pages 2-3 = slot 0 (RAM)   ->  $04
        byte initial = 0x04;
        // What we want: page 2 -> slot 1, everything else unchanged.
        byte wanted = 0x14;

        Console.WriteLine($"Initial slot register: ${initial:X2}");
        Console.WriteLine($"Wanted:               ${wanted:X2}  "
                        + "(page 2 -> slot 1)\n");

        Console.WriteLine("  searching over A = 0..255, HL = $8000 ...\n");
        int found = 0;
        for (int a = 0; a < 256; a++)
        {
            byte reg = Try(biosPath, (byte)a, 0x8000, initial);
            if (reg == wanted)
            {
                Console.WriteLine($"    FOUND: A = ${a:X2}, HL = $8000 -> ${reg:X2}");
                found++;
            }
        }
        if (found == 0)
        {
            Console.WriteLine("    no A works with HL = $8000");
            Console.WriteLine("    trying HL = $0000 .. $FFFF for A = 1 ..\n");
            for (int a = 0; a < 4; a++)
            {
                for (int addr = 0; addr < 0x10000; addr += 0x100)
                {
                    byte reg = Try(biosPath, (byte)a, (ushort)addr, initial);
                    if (reg == wanted)
                    {
                        Console.WriteLine($"    FOUND: A = ${a:X2}, "
                                        + $"HL = ${addr:X4} -> ${reg:X2}");
                        found++;
                    }
                }
            }
        }
        if (found == 0) Console.WriteLine("    nothing found");

        Console.WriteLine("\n  full table for A = 0..3, HL = $8000:");
        foreach (byte id in new byte[] { 0x00, 0x01, 0x02, 0x03 })
        {
            byte reg = Try(biosPath, id, 0x8000, initial);
            Console.WriteLine($"    A=${id:X2} -> ${reg:X2}");
        }
    }
}