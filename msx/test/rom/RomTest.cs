// Test harness for the 64K Cybernoid MSX ROM (ASCII16 mapper).
//
// Machine layout (a realistic MSX1):
//   slot 0 : pages 0-1 = MSX BIOS ROM, pages 2-3 = main RAM
//   slot 1 : our 64K cartridge (pages 1 and 2)
//   slot 3 : a second RAM slot (expansion)
//
// The cartridge is mapped to page 1, so the BIOS ROM search calls its
// INIT routine.  The ROM's INIT then switches page 2 to the cartridge
// with ENASLT, which is what makes the asset banks reachable.

using Z80;

namespace CybernoidTest;

/// <summary>Slot 0 of a real MSX: the 32K BIOS in pages 0-1 and the
/// main RAM in pages 2-3.</summary>
class BiosAndRamDevice : ISlotDevice
{
    private readonly byte[] bios;
    public readonly byte[] Ram = new byte[32768];   // pages 2 and 3

    public BiosAndRamDevice(byte[] bios) { this.bios = bios; }

    public byte Read(ushort address)
    {
        int page = address >> 14;
        if (page <= 1) return bios[address & 0x7FFF];
        return Ram[(address - 0x8000) & 0x7FFF];
    }

    public void Write(ushort address, byte value)
    {
        int page = address >> 14;
        if (page <= 1) return;                       // ROM
        Ram[(address - 0x8000) & 0x7FFF] = value;
    }
}

class RomBus : IMemoryBus
{
    public BiosAndRamDevice Slot0 = null!;
    public byte[] Slot3Ram = new byte[65536];
    public Ascii16Cartridge? Cart;
    public int CartSlot = 1;              // the primary slot of the cartridge
    public byte SlotRegister = 0x04;       // p0=BIOs p1=cart p2/3=slot0

    public byte Read(ushort address, ref int cycles)
    {
        int page = address >> 14;
        int slot = (SlotRegister >> (page * 2)) & 0x03;
        if (slot == CartSlot) return Cart?.Read(address) ?? 0xFF;
        switch (slot)
        {
            case 0: return Slot0.Read(address);
            case 3: return Slot3Ram[address];
            default: return 0xFF;
        }
    }

    public void Write(ushort address, byte value, ref int cycles)
    {
        int page = address >> 14;
        int slot = (SlotRegister >> (page * 2)) & 0x03;
        if (slot == CartSlot) { Cart?.Write(address, value); return; }
        switch (slot)
        {
            case 0: Slot0.Write(address, value); break;
            case 3: Slot3Ram[address] = value; break;
        }
    }
}

class RomTest
{
    static int failures = 0;

    static void Check(bool ok, string label, string detail = "")
    {
        Console.WriteLine($"  [{(ok ? "PASS" : "FAIL")}] {label}{(detail.Length > 0 ? " - " + detail : "")}");
        if (!ok) failures++;
    }

    /// Build a machine with the cartridge in the given primary slot and
    /// run the cartridge INIT the way the BIOS would.
    static (RomBus bus, Ascii16Cartridge cart, Z80.Z80 cpu) Boot(
        string biosPath, byte[] rom, int cartSlot, bool useBiosBoot)
    {
        var bus = new RomBus();
        var cart = new Ascii16Cartridge(rom);
        bus.Cart = cart;
        bus.CartSlot = cartSlot;

        bool haveBios = File.Exists(biosPath);
        if (haveBios)
        {
            byte[] bios = File.ReadAllBytes(biosPath);
            bus.Slot0 = new BiosAndRamDevice(bios);
        }
        else
        {
            byte[] stub = new byte[32768];
            stub[0] = 0xC3; stub[1] = 0x10; stub[2] = 0x40;   // JP $4010
            bus.Slot0 = new BiosAndRamDevice(stub);
        }

        // A real MSX after the power-up:
        //   page 0 -> slot 0 (BIOS), page 1 -> our cartridge slot,
        //   pages 2 and 3 -> slot 0 (RAM)
        byte reg = 0x04;
        reg = (byte)((reg & ~0x0C) | (cartSlot << 2));   // page 1
        bus.SlotRegister = reg;

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = reg;
        cpu.OnInputPort = (port, cyc) =>
        {
            if ((port & 0xFF) == 0xA8) return bus.SlotRegister;
            return 0xFF;
        };
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xA8) bus.SlotRegister = value;
        };

        ushort init = BitConverter.ToUInt16(rom, 2);

        if (useBiosBoot && haveBios)
        {
            // Let the real BIOS boot: it searches the slots, finds our
            // cartridge and calls its INIT.
            cpu.PC = 0x0000;
            cpu.SP = 0xF380;
            cpu.IFF1 = false;
            for (int i = 0; i < 400000; i++)
            {
                cpu.Step();
                if (cpu.PC == init) break;    // the BIOS called our INIT
                if (cpu.PC == 0x0000) break; // something went wrong
            }
        }
        else
        {
            cpu.PC = init;
            cpu.SP = 0xF380;
            cpu.IFF1 = false;
        }

        // Run our INIT and the main loop for a while.
        // (the VRAM clear alone needs ~150k steps)
        for (int i = 0; i < 400000; i++) cpu.Step();

        return (bus, cart, cpu);
    }

    public static int Run()
    {
        string buildDir = Path.GetFullPath(
            Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "build"));
        string romPath = Path.Combine(buildDir, "cybernoid.rom");
        string biosPath = Path.Combine(buildDir, "msx.rom");

        if (!File.Exists(romPath))
        {
            Console.WriteLine($"ERROR: {romPath} not found. Run msx/scripts/build_rom.py");
            return 1;
        }

        byte[] rom = File.ReadAllBytes(romPath);
        Console.WriteLine($"Cybernoid 64K ROM test harness ({rom.Length} bytes)\n");

        // ------------------------------------------------------------------
        Console.WriteLine("1. Header");
        // ------------------------------------------------------------------
        Check(rom.Length == 65536, "ROM is 64 KB", $"{rom.Length} bytes");
        Check(rom[0] == 'A' && rom[1] == 'B', "Signature is 'AB'");
        ushort init = BitConverter.ToUInt16(rom, 2);
        Check(init >= 0x4000 && init < 0x8000, "INIT inside the cartridge window",
              $"${init:X4}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("2. Bank content check");
        // ------------------------------------------------------------------
        for (int bank = 1; bank < 4; bank++)
        {
            byte id = rom[bank * 0x4000];
            Check(id == (byte)(0xB0 + bank),
                  $"Bank {bank} carries its ID byte ${0xB0 + bank:X2}",
                  $"${id:X2}");
        }

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("3. Boot: the BIOS calls the cartridge INIT");
        // ------------------------------------------------------------------
        var (bus, cart, cpu) = Boot(biosPath, rom, cartSlot: 1, useBiosBoot: false);
        Console.WriteLine($"  PC = ${cpu.PC:X4}  SP = ${cpu.SP:X4}  "
                        + $"slot register = ${bus.SlotRegister:X2}");
        Console.WriteLine($"  banks: $4000->{cart.Banks.at4000}  "
                        + $"$8000->{cart.Banks.at8000}");

        bool inMainLoop = cpu.PC >= 0x404A && cpu.PC <= 0x4052;
        Check(inMainLoop, "Execution is in the main loop (no reboot)",
              $"PC = ${cpu.PC:X4}");
        Check(cpu.SP >= 0xF000, "Stack pointer is at the top of the RAM",
              $"SP = ${cpu.SP:X4}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("4. Slot setup (ENASLT)");
        // ------------------------------------------------------------------
        int page2Slot = (bus.SlotRegister >> 4) & 0x03;
        Check(page2Slot == 1, "Page 2 ($8000) mapped to the cartridge slot",
              $"slot = {page2Slot}");
        int page0Slot = bus.SlotRegister & 0x03;
        Check(page0Slot == 0, "Page 0 still points at the BIOS slot",
              $"slot = {page0Slot}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("5. Mapper test: SETBANK_B(n) then read $8000");
        // ------------------------------------------------------------------
        byte selfTest = bus.Slot0.Ram[0xC004 - 0x8000];
        Check(selfTest == 0x00,
              "The ROM's own bank self test passed",
              $"bank_result = ${selfTest:X2}");

        int cyclesDummy = 0;
        bool allOk = true;
        for (int bank = 1; bank <= 3; bank++)
        {
            cart.Write(0x7000, (byte)bank);
            byte got = bus.Read(0x8000, ref cyclesDummy);
            bool ok = got == (byte)(0xB0 + bank);
            Console.WriteLine($"    bank {bank}: $8000 = ${got:X2} "
                            + $"(expected ${0xB0 + bank:X2}) {(ok ? "OK" : "FAIL")}");
            if (!ok) allOk = false;
        }
        cart.Write(0x7000, 1);
        Check(allOk, "Reading $8000 returns the signature of the selected bank");
        Check(cart.Banks.at4000 == 0, "The $4000 window stays on bank 0",
              $"bank = {cart.Banks.at4000}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("6. VDP configuration");
        // ------------------------------------------------------------------
        var vdp = new FakeVdp();
        {
            var bus3 = new RomBus();
            var cart3 = new Ascii16Cartridge(rom);
            bus3.Cart = cart3;
            byte[] bios = File.ReadAllBytes(biosPath);
            bus3.Slot0 = new BiosAndRamDevice(bios);
            bus3.SlotRegister = 0x04;
            var cpu3 = new Z80.Z80();
            cpu3.MemoryBus = bus3;
            cpu3.Reset();
            cpu3.SlotRegister = 0x04;
            cpu3.OnInputPort = (port, cyc) =>
                (port & 0xFF) == 0xA8 ? bus3.SlotRegister : (byte)0xFF;
            cpu3.OnOutputPort = (port, value, cyc) =>
            {
                if ((port & 0xFF) == 0xA8) bus3.SlotRegister = value;
                if (port == 0x98 || port == 0x99) vdp.Write(port, value);
            };
            cpu3.PC = init;
            cpu3.SP = 0xF380;
            cpu3.IFF1 = false;
            for (int i = 0; i < 400000; i++) cpu3.Step();
        }

        var regText = string.Join(" ",
            vdp.Regs.Select((r, i) => "R" + i + "=$" + r.ToString("X2")));
        Console.WriteLine("  VDP registers: " + regText);
        Check(vdp.Regs[0] == 0x02, "R0 = $02 (graphics mode)", $"${vdp.Regs[0]:X2}");
        Check(vdp.Regs[1] == 0xE0, "R1 = $E0 (16K VRAM, IRQ, display on)", $"${vdp.Regs[1]:X2}");
        Check(vdp.Regs[2] == 0x06, "R2 = $06 (name table at $1800)", $"${vdp.Regs[2]:X2}");
        Check(vdp.Regs[3] == 0xFF, "R3 = $FF (colour table at $2000)", $"${vdp.Regs[3]:X2}");
        Check(vdp.Regs[4] == 0x03, "R4 = $03 (pattern generator at $0000)", $"${vdp.Regs[4]:X2}");
        Check(vdp.Regs[5] == 0x36, "R5 = $36 (sprite attributes at $1B00)", $"${vdp.Regs[5]:X2}");
        Check(vdp.Regs[6] == 0x07, "R6 = $07 (sprite patterns at $3800)", $"${vdp.Regs[6]:X2}");
        Check(vdp.Regs[7] == 0xF1, "R7 = $F1 (border colour 1)", $"${vdp.Regs[7]:X2}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("7. Machine configurations");
        // ------------------------------------------------------------------
        foreach (var cfg in new[]
                 {
                     (name: "cart in slot 1", cart: 1),
                     (name: "cart in slot 2", cart: 2),
                 })
        {
            var (b, c, u) = Boot(biosPath, rom, cfg.cart, useBiosBoot: false);
            int p2 = (b.SlotRegister >> 4) & 0x03;
            bool ok = p2 == cfg.cart && u.PC >= 0x404A && u.PC <= 0x4052;
            Check(ok, cfg.name,
                  $"page2=slot{p2}, PC=${u.PC:X4}, SP=${u.SP:X4}");
        }

        Console.WriteLine();
        Console.WriteLine(new string('=', 62));
        if (failures == 0)
        {
            Console.WriteLine("ALL TESTS PASSED");
            return 0;
        }
        Console.WriteLine($"{failures} TEST(S) FAILED");
        return 1;
    }
}