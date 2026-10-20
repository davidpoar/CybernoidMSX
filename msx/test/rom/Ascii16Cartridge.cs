// ASCII16 mapper cartridge, following the hardware exactly.
//
// From the reference (docs/reference/msx/ascii16_mapper_reference.md,
// which quotes openMSX's RomAscii16kB):
//
//   window A: $4000-$7FFF, register at $6000-$67FF
//   window B: $8000-$BFFF, register at $7000-$77FF
//
//   The register decode is
//       (0x6000 <= address) && (address < 0x7800) && !(address & 0x0800)
//   so $6800-$6FFF and $7800-$7FFF are NOT registers.
//
//   The registers are write only: reading them returns the ROM
//   content of the visible bank.
//
//   Reset leaves bank A = 0 and bank B = 0.
//
//   The bank number is masked: block < nrBlocks ? block : block & (n-1).
//
//   Pages 0 and 3 are not connected to the cartridge.

using Z80;

namespace CybernoidTest;

class Ascii16Cartridge : ISlotDevice
{
    private readonly byte[] romData;
    private readonly int bankCount;
    private int bankAt4000;
    private int bankAt8000;

    public Ascii16Cartridge(byte[] romData)
    {
        this.romData = romData;
        bankCount = Math.Max(1, romData.Length / 0x4000);
        bankAt4000 = 0;
        bankAt8000 = 0;          // the hardware reset state
    }

    /// <summary>Mask a bank number the way RomBlocks::setRom does.</summary>
    private int Mask(int block)
    {
        if (block < bankCount) return block;
        return block & (bankCount - 1);
    }

    public byte Read(ushort address)
    {
        if (address >= 0x4000 && address < 0x8000)
        {
            int off = Mask(bankAt4000) * 0x4000 + (address - 0x4000);
            return off < romData.Length ? romData[off] : (byte)0xFF;
        }
        if (address >= 0x8000 && address < 0xC000)
        {
            int off = Mask(bankAt8000) * 0x4000 + (address - 0x8000);
            return off < romData.Length ? romData[off] : (byte)0xFF;
        }
        return 0xFF;
    }

    public void Write(ushort address, byte value)
    {
        // (0x6000 <= address) && (address < 0x7800) && !(address & 0x0800)
        if (address >= 0x6000 && address < 0x7800 && (address & 0x0800) == 0)
        {
            int region = ((address >> 12) & 1) + 1;
            if (region == 1) bankAt4000 = Mask(value);
            else bankAt8000 = Mask(value);
        }
    }

    public (int at4000, int at8000) Banks => (bankAt4000, bankAt8000);
}
