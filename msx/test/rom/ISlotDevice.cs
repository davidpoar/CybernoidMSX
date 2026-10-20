namespace CybernoidTest;

/// <summary>Same shape as emu.ISlotDevice, declared here so the test
/// project does not need a reference to msx.core.</summary>
interface ISlotDevice
{
    byte Read(ushort address);
    void Write(ushort address, byte value);
}
