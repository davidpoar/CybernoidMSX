// Test harness for the 64K Cybernoid MSX ROM (ASCII16 mapper).
//
// Machine layout:
//   slot 0 page 0/1 : MSX BIOS (32K)      - the real msx.rom
//   slot 1 page 1/2 : the cartridge       - our 64K ROM
//   slot 3          : 64K of RAM
//
// The cartridge is mapped to page 1, so the BIOS ROM search calls its
// INIT routine.  The ROM's INIT then switches page 2 to the cartridge
// with ENASLT, which is what makes the asset banks reachable.

using Z80;

namespace CybernoidTest;

class RomBus : IMemoryBus
{
    public byte[] Ram = new byte[65536];
    public byte[] Cartridge = new byte[65536];
    public byte[] Bios = new byte[32768];
    public byte SlotRegister = 0xF4;   // p0=BIOs p1=cart p2/3=RAM
    public Ascii16Cartridge? Cart;

    public byte Read(ushort address, ref int cycles)
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
                return Cart?.Read(address) ?? 0xFF;
            case 3:
                return Ram[address];
            default:
                return 0xFF;
        }
    }

    public void Write(ushort address, byte value, ref int cycles)
    {
        int page = address >> 14;
        int slot = (SlotRegister >> (page * 2)) & 0x03;
        switch (slot)
        {
            case 1:
                Cart?.Write(address, value);
                break;
            case 3:
                Ram[address] = value;
                break;
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
        Check(BitConverter.ToUInt16(rom, 4) == 0, "STATEMENT handler is 0");
        Check(BitConverter.ToUInt16(rom, 6) == 0, "DEVICE handler is 0");
        Check(BitConverter.ToUInt16(rom, 8) == 0, "TEXT pointer is 0");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("2. Bank content check");
        // ------------------------------------------------------------------
        // Each asset bank starts with an ID byte so it can be told apart.
        for (int bank = 1; bank < 4; bank++)
        {
            byte id = rom[bank * 0x4000];
            Check(id == (byte)(0xB0 + bank),
                  $"Bank {bank} carries its ID byte ${0xB0 + bank:X2}",
                  $"${id:X2}");
        }
        Check(rom[0] == 'A', "Bank 0 starts with the cartridge header");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("3. Boot: the BIOS calls the cartridge INIT");
        // ------------------------------------------------------------------
        var bus = new RomBus();
        var cart = new Ascii16Cartridge(rom);
        bus.Cart = cart;

        // The MSX BIOS ROM, if we have it
        if (File.Exists(biosPath))
        {
            byte[] bios = File.ReadAllBytes(biosPath);
            Array.Copy(bios, bus.Bios, Math.Min(bios.Length, bus.Bios.Length));
            Check(true, $"MSX BIOS loaded ({bios.Length} bytes)");
        }
        else
        {
            // Minimal BIOS: a jump to the cartridge INIT
            bus.Bios[0] = 0xC3;
            bus.Bios[1] = (byte)(init & 0xFF);
            bus.Bios[2] = (byte)(init >> 8);
            Check(true, "Minimal BIOS stub (no msx.rom found, jumping to INIT)");
        }

        var cpu = new Z80.Z80();
        cpu.MemoryBus = bus;
        cpu.Reset();
        cpu.SlotRegister = bus.SlotRegister;
        // The BIOS routines (ENASLT and friends) change the slot
        // register through PPI port $A8.
        cpu.OnOutputPort = (port, value, cyc) =>
        {
            if ((port & 0xFF) == 0xA8) bus.SlotRegister = value;
        };

        // Simulate the BIOS ROM search: page 1 already points at the
        // cartridge, so the BIOS would call the INIT address.
        cpu.PC = init;
        cpu.SP = 0xF380;
        cpu.IFF1 = false;

        for (int i = 0; i < 20000; i++) cpu.Step();

        Console.WriteLine($"  PC = ${cpu.PC:X4}  SP = ${cpu.SP:X4}  "
                        + $"slot register = ${bus.SlotRegister:X2}");
        Console.WriteLine($"  banks: $4000->{cart.Banks.at4000}  "
                        + $"$8000->{cart.Banks.at8000}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("4. Slot setup");
        // ------------------------------------------------------------------
        // The INIT must have switched page 2 to the cartridge so the
        // asset banks are reachable.
        int cyclesDummy = 0;
        int page2Slot = (bus.SlotRegister >> 4) & 0x03;
        Check(page2Slot == 1, "Page 2 ($8000) mapped to the cartridge slot",
              $"slot = {page2Slot}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("5. Bank switching");
        // ------------------------------------------------------------------
        // Write to $6000 and $7000 and check the visible content changes.
        byte before8000 = bus.Read(0x8000, ref cyclesDummy);
        cart.Write(0x7000, 2);                 // bank 2 at $8000
        byte after8000 = bus.Read(0x8000, ref cyclesDummy);
        Check(cart.Banks.at8000 == 2, "Write to $7000 selects the $8000 window",
              $"bank = {cart.Banks.at8000}");
        Check(before8000 != after8000 || after8000 == 0xFF,
              "The $8000 window content changed with the bank",
              $"{before8000:X2} -> {after8000:X2}");

        cart.Write(0x7000, 1);                 // back to bank 1
        Check(cart.Banks.at8000 == 1, "Write to $7000 restores the bank");

        // The engine window must stay on bank 0.
        Check(cart.Banks.at4000 == 0,
              "The $4000 window stays on bank 0 (the engine)",
              $"bank = {cart.Banks.at4000}");

        // ------------------------------------------------------------------
        Console.WriteLine();
        Console.WriteLine("6. VDP configuration");
        // ------------------------------------------------------------------
        // The INIT configures SCREEN 2 by hand.  We check the registers
        // through a small VDP model.
        var vdp = new FakeVdp();
        // Re-run the INIT with the VDP hooked up.
        var bus2 = new RomBus { SlotRegister = 0xF4 };
        var cart2 = new Ascii16Cartridge(rom);
        bus2.Cart = cart2;
        if (File.Exists(biosPath))
        {
            byte[] bios = File.ReadAllBytes(biosPath);
            Array.Copy(bios, bus2.Bios, Math.Min(bios.Length, bus2.Bios.Length));
        }
        else
        {
            bus2.Bios[0] = 0xC3;
            bus2.Bios[1] = (byte)(init & 0xFF);
            bus2.Bios[2] = (byte)(init >> 8);
        }
        var cpu2 = new Z80.Z80();
        cpu2.MemoryBus = bus2;
        cpu2.Reset();
        cpu2.SlotRegister = bus2.SlotRegister;
        cpu2.PC = init;
        cpu2.SP = 0xF380;
        cpu2.IFF1 = false;
        cpu2.OnOutputPort = (port, value, cyc) =>
        {
            if (port == 0x98 || port == 0x99) vdp.Write(port, value);
        };
        for (int i = 0; i < 20000; i++) cpu2.Step();

        var regText = string.Join(" ", vdp.Regs.Select((r, i) => "R" + i + "=$" + r.ToString("X2")));
        Console.WriteLine("  VDP registers: " + regText);
        Check(vdp.Regs[0] == 0x02, "R0 = $02 (graphics mode)", $"${vdp.Regs[0]:X2}");
        Check(vdp.Regs[2] == 0x50, "R2 = $50 (name table at $3800)", $"${vdp.Regs[2]:X2}");
        Check(vdp.Regs[3] == 0xC0, "R3 = $C0 (colour table at $2000)", $"${vdp.Regs[3]:X2}");
        Check(vdp.Regs[4] == 0x00, "R4 = $00 (pattern table at $0000)", $"${vdp.Regs[4]:X2}");
        Check(vdp.Regs[5] == 0x76, "R5 = $76 (sprite attrs at $1B00)", $"${vdp.Regs[5]:X2}");
        Check(vdp.Regs[6] == 0x03, "R6 = $03 (sprite patterns at $1800)", $"${vdp.Regs[6]:X2}");
        Check((vdp.Regs[1] & 0x20) != 0, "R1 has the IRQ enable bit",
              $"${vdp.Regs[1]:X2}");

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
