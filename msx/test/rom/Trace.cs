// Trace the cartridge INIT step by step to find where it leaves the ROM.
using Z80;

namespace CybernoidTest;

class Trace
{
    public static void Run()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        byte[] rom = File.ReadAllBytes(Path.Combine(buildDir, "cybernoid.rom"));
        byte[] bios = File.ReadAllBytes(Path.Combine(buildDir, "msx.rom"));

        var bus = new RomBus();
        var cart = new Ascii16Cartridge(rom);
        bus.Cart = cart;
        bus.Slot0 = new BiosAndRamDevice(bios);
        bus.SlotRegister = 0x04;

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = 0x04;
        cpu.OnInputPort = (port, cyc) =>
            (port & 0xFF) == 0xA8 ? bus.SlotRegister : (byte)0xFF;
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xA8)
            {
                Console.WriteLine($"  OUT ($A8) = ${value:X2}   (PC=${cpu.PC:X4})");
                bus.SlotRegister = value;
            }
        };

        ushort init = BitConverter.ToUInt16(rom, 2);
        cpu.PC = init;
        cpu.SP = 0xF380;
        cpu.IFF1 = false;

        Console.WriteLine($"Starting at INIT=${init:X4}, slot=${bus.SlotRegister:X2}\n");

        bool reported = false;
        for (int i = 0; i < 4000; i++)
        {
            ushort pc = cpu.PC;

            if (pc == 0x0264 && !reported)
            {
                reported = true;
                Console.WriteLine("  --- ENASLT masks at $0264 ---");
                Console.WriteLine($"      B (OR mask)  = ${cpu.B:X2}");
                Console.WriteLine($"      C (AND mask) = ${cpu.C:X2}");
                Console.WriteLine($"      D (replic)   = ${cpu.D:X2}");
                Console.WriteLine($"      E (page msk) = ${cpu.E:X2}");
                Console.WriteLine($"      A (slot id)  = ${cpu.A:X2}");
                Console.WriteLine($"      HL (address) = ${cpu.H:X2}${cpu.L:X2}");
                Console.WriteLine($"      slot reg now = ${bus.SlotRegister:X2}");
            }

            cpu.Step();

            if (i < 40)
            {
                Console.WriteLine($"  step {i}: ${pc:X4} -> ${cpu.PC:X4}  "
                                + $"SP=${cpu.SP:X4} slot=${bus.SlotRegister:X2} "
                                + $"A=${cpu.A:X2} HL=${cpu.H:X2}${cpu.L:X2}");
            }

            if ((cpu.PC < 0x4000 || cpu.PC >= 0x8000) && reported && i >= 40)
            {
                Console.WriteLine($"  step {i}: PC ${pc:X4} -> ${cpu.PC:X4}  "
                                + $"SP=${cpu.SP:X4}  slot=${bus.SlotRegister:X2}");
                break;
            }
        }

        Console.WriteLine($"\nFinal: PC=${cpu.PC:X4} SP=${cpu.SP:X4} "
                        + $"slot=${bus.SlotRegister:X2} banks="
                        + $"{cart.Banks.at4000}/{cart.Banks.at8000}");
    }
}