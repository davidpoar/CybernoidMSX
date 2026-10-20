// ASCII16 mapper cartridge, mirroring the format the Cybernoid ROM expects.
//
//   write to $6000-$6FFF : selects the 16K bank visible at $4000-$7FFF
//   write to $7000-$7FFF : selects the 16K bank visible at $8000-$BFFF
//
// ROM layout (64K = 4 banks of 16K):
//   file $0000-$3FFF  bank 0 -> MSX $4000-$7FFF   (engine, "AB" header)
//   file $4000-$7FFF  bank 1 -> MSX $8000-$BFFF   (assets)
//   file $8000-$BFFF  bank 2 -> MSX $8000-$BFFF   (assets)
//   file $C000-$FFFF  bank 3 -> MSX $8000-$BFFF   (assets)

using Z80;

namespace CybernoidTest;

/// <summary>Same shape as emu.ISlotDevice, declared here so the test
/// project does not need a reference to msx.core.</summary>
interface ISlotDevice
{
    byte Read(ushort address);
    void Write(ushort address, byte value);
}

/// <summary>
/// ASCII16 mapper cartridge, mirroring the format the Cybernoid ROM expects.
//
//   write to $6000-$6FFF : selects the 16K bank visible at $4000-$7FFF
//   write to $7000-$7FFF : selects the 16K bank visible at $8000-$BFFF
//
// ROM layout (64K = 4 banks of 16K):
//   file $0000-$3FFF  bank 0 -> MSX $4000-$7FFF   (engine, "AB" header)
//   file $4000-$7FFF  bank 1 -> MSX $8000-$BFFF   (assets)
//   file $8000-$BFFF  bank 2 -> MSX $8000-$BFFF   (assets)
//   file $C000-$FFFF  bank 3 -> MSX $8000-$BFFF   (assets)
// </summary>
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
        bankAt8000 = bankCount > 1 ? 1 : 0;
    }

    public byte Read(ushort address)
    {
        if (address >= 0x4000 && address < 0x8000)
        {
            int off = bankAt4000 * 0x4000 + (address - 0x4000);
            return off < romData.Length ? romData[off] : (byte)0xFF;
        }
        if (address >= 0x8000 && address < 0xC000)
        {
            int off = bankAt8000 * 0x4000 + (address - 0x8000);
            return off < romData.Length ? romData[off] : (byte)0xFF;
        }
        return 0xFF;
    }

    public void Write(ushort address, byte value)
    {
        if (address >= 0x6000 && address < 0x7000)
        {
            bankAt4000 = value % bankCount;
        }
        else if (address >= 0x7000 && address < 0x8000)
        {
            bankAt8000 = value % bankCount;
        }
        // $8000-$BFFF holds no registers: writes are ignored.
    }

    public (int at4000, int at8000) Banks => (bankAt4000, bankAt8000);
}
