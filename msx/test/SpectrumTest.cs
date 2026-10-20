// Harness del ZX Spectrum 48K para ejecutar el juego original de
// Cybernoid y extraer sus graficos.
//
// No hace falta el ROM del Spectrum: el juego usa IM 2 con el vector
// en $FE00 (RAM), asi que basta con la imagen de memoria.
//
//   $0000-$3FFF  RAM (vacia)
//   $4000-$57FF  pixeles de la pantalla
//   $5800-$5AFF  atributos de la pantalla
//   $5B00-$FFFF  BASIC, tablas del juego y codigo
//
// La interrupcion de 50 Hz se genera aqui, y la pantalla se lee
// directamente de la RAM.

using Z80;

namespace CybernoidTest;

class SpectrumBus : IMemoryBus
{
    public byte[] Ram = new byte[65536];

    public byte Read(ushort address, ref int currentCycles) => Ram[address];

    public void Write(ushort address, byte value, ref int currentCycles)
        => Ram[address] = value;
}

class SpectrumMachine
{
    public Z80.Z80 Cpu = null!;
    public SpectrumBus Bus = null!;

    // El teclado: 8 semifilas de 5 teclas, en activo bajo
    public readonly byte[] Keys = new byte[8];

    // La ULA: el estado del altavoz y el borde
    public bool BeeperState;
    public byte BorderColour;
    public int BeeperEdges;

    public long TotalCycles;

    const int CyclesPerFrame = 69888;   // 3.5 MHz / 50 fps
    const int IntCycle = 1360;          // la ULA interrumpe en el ciclo 16

    // El puerto alto selecciona la semifila del teclado: el bit que
    // vale 0 en el byte alto es el que elige la fila.  El orden de
    // las ocho semifilas es el de los bits, de la 0 a la 7.
    static readonly int[] RowForPort =
    {
        0xFE, 0xDF, 0xBF, 0x7F, 0xFB, 0xFD, 0xEB, 0xDB,
    };

    public void Build()
    {
        Bus = new SpectrumBus();
        Cpu = new Z80.Z80();
        Cpu.MemoryBus = Bus;
        Cpu.Reset();

        for (int i = 0; i < Keys.Length; i++) Keys[i] = 0x1F;

        Cpu.OnInputPort = (port, cycles) =>
        {
            if ((port & 0xFF) == 0xFE)
            {
                // En el Spectrum, IN A,(n) pone A en el byte alto de la
                // direccion, y ahi va el selector de la semifila.
                int sel = Cpu.A;
                int zero = (~sel) & 0xFF;
                if (zero == 0) return 0xFF;
                int row = 0;
                while (((zero >> row) & 1) == 0) row++;
                byte v = (byte)(Keys[row] | 0xE0);
                if (KeyLog.Count < 40)
                    KeyLog.Add($"IN A=${sel:X2} -> ${v:X2} (fila {row})");
                return v;
            }
            return 0xFF;
        };

        Cpu.OnOutputPort = (port, value, cycles) =>
        {
            if ((port & 0xFF) == 0xFE)
            {
                // bit 4 = altavoz, bits 0-2 = color del borde
                bool state = (value & 0x10) != 0;
                if (state != BeeperState) BeeperEdges++;
                BeeperState = state;
                BorderColour = (byte)(value & 0x07);
            }
        };
    }

    /// Carga la imagen del juego: el byte 0 de la imagen es $4000.
    public void LoadImage(byte[] image)
    {
        Array.Copy(image, 0, Bus.Ram, 0x4000, Math.Min(image.Length, 0xC000));
    }

    public void Start(ushort pc, ushort sp)
    {
        Cpu.PC = pc;
        Cpu.SP = sp;
    }

    /// Ejecuta n frames de 50 Hz, con la interrupcion en su momento.
    public void RunFrames(int frames)
    {
        for (int f = 0; f < frames; f++)
        {
            int frameCycles = 0;
            bool fired = false;
            while (frameCycles < CyclesPerFrame)
            {
                if (!fired && frameCycles >= IntCycle)
                {
                    Cpu.InterruptPending = true;
                    fired = true;
                }
                if (Trace) PcCount.TryGetValue(Cpu.PC, out _);
                PcCount[Cpu.PC] = PcCount.GetValueOrDefault(Cpu.PC) + 1;                int c = Cpu.Step();
                if (c <= 0) c = 4;
                frameCycles += c;
                TotalCycles += c;
            }
        }
    }

    public bool Trace;
    public readonly List<string> KeyLog = new();
    public readonly Dictionary<ushort, int> PcCount = new();

    public byte[] ScreenPixels() => Bus.Ram[0x4000..0x5800];

    public byte[] ScreenAttributes() => Bus.Ram[0x5800..0x5B00];

    /// Vuelca la pantalla cruda para analizarla con Python
    public void DumpScreen(string path)
    {
        using var f = new FileStream(path, FileMode.Create);
        f.Write(ScreenPixels());
        f.Write(ScreenAttributes());
    }

    /// Vuelca una zona de la RAM (por ejemplo los sprites)
    public void DumpRam(string path, int start, int length)
    {
        using var f = new FileStream(path, FileMode.Create);
        f.Write(Bus.Ram, start, length);
    }
}

static class SpectrumTest
{
    static readonly string Root = AppContext.BaseDirectory;

    /// Busca la raiz del proyecto (donde esta la carpeta spectrum/)
    static string ProjectDir
    {
        get
        {
            var d = new DirectoryInfo(Root);
            while (d != null)
            {
                if (Directory.Exists(Path.Combine(d.FullName, "spectrum")))
                    return d.FullName;
                d = d.Parent;
            }
            return Root;
        }
    }

    static string ImagePath =>
        Path.Combine(ProjectDir, "spectrum", "cybernoid_after_lddr.bin");

    static string OutDir =>
        Path.Combine(ProjectDir, "spectrum", "captures");

    public static int Run()
    {
        Console.WriteLine(new string('=', 66));
        Console.WriteLine("CYBERNOID EN EL SPECTRUM 48K (harness propio)");
        Console.WriteLine(new string('=', 66));

        byte[] image = File.ReadAllBytes(ImagePath);
        Console.WriteLine($"imagen: {image.Length} bytes ($4000-$FFFF)");

        var m = new SpectrumMachine();
        m.Build();
        m.LoadImage(image);
        m.Start(0x6504, 0x0000);

        int frames = int.Parse(Environment.GetEnvironmentVariable("CYBERNOID_FRAMES") ?? "300");
        Console.WriteLine($"ejecutando {frames} frames...");
        m.RunFrames(frames);

        Report(m);
        foreach (var k in m.KeyLog) Console.WriteLine("    " + k);
        Console.WriteLine("\n  Donde pasa el tiempo (PC mas frecuentes):");
        foreach (var kv in m.PcCount.OrderByDescending(k => k.Value).Take(12))
            Console.WriteLine($"    ${kv.Key:X4}  {kv.Value} veces");

        Console.WriteLine("\n  Rastreo del teclado:");
        foreach (ushort a in new ushort[] { 0x6604, 0x660B, 0x662B, 0x81DB,
                                           0x833B, 0x9470, 0x65E1, 0x84F5 })
            Console.WriteLine($"    ${a:X4}  {m.PcCount.GetValueOrDefault(a)} veces");

        Directory.CreateDirectory(OutDir);
        string stamp = DateTime.Now.ToString("HHmmss");
        Save(m, Path.Combine(OutDir, $"spec_{stamp}_1_titulo.png"), 1);
        m.DumpScreen(Path.Combine(OutDir, $"spec_{stamp}_1_titulo.raw"));

        // Pulsar una tecla para empezar la partida.  El menu pide un
        // digito del 1 al 6, que esta en la fila 3, bit 0.
        int keyRow = int.Parse(Environment.GetEnvironmentVariable("CYBERNOID_KEYROW") ?? "3");
        int keyBit = int.Parse(Environment.GetEnvironmentVariable("CYBERNOID_KEYBIT") ?? "0");
        Console.WriteLine($"\npulsando la tecla (fila {keyRow}, bit {keyBit})...");
        m.KeyLog.Clear();
        m.Keys[keyRow] &= (byte)~(1 << keyBit);
        m.RunFrames(20);
        m.Keys[keyRow] |= (byte)(1 << keyBit);
        m.RunFrames(60);
        Report(m);
        Console.WriteLine("  lecturas del teclado con la tecla pulsada:");
        foreach (var k in m.KeyLog.Take(12)) Console.WriteLine("    " + k);
        DumpAttributes(m);
        m.DumpScreen(Path.Combine(OutDir, $"spec_{stamp}_juego.raw"));
        m.DumpRam(Path.Combine(OutDir, $"spec_{stamp}_sprites.bin"), 0x5F00, 0x400);
        m.DumpRam(Path.Combine(OutDir, $"spec_{stamp}_spr2.bin"), 0x5E00, 0x200);
        m.DumpRam(Path.Combine(OutDir, $"spec_{stamp}_tablas.bin"), 0x6300, 0x200);
        m.DumpRam(Path.Combine(OutDir, $"spec_{stamp}_tablas2.bin"), 0x5F00, 0x200);
        Save(m, Path.Combine(OutDir, $"spec_{stamp}_2_juego.png"), 1);

        // Una partida: capturas cada pocos segundos y con las teclas de
        // movimiento pulsadas para ver como se mueve la nave.
        Console.WriteLine("\n  partida:");
        var pasos = new (int frames, int row, int bit, string nombre)[]
        {
            (60,  -1, 0, "a_60"),
            (60,  -1, 0, "b_120"),
            (60,  -1, 0, "c_180"),
            (60,  -1, 0, "d_240"),
            (30,   4, 1, "e_derecha"),      // la 9 = derecha
            (30,   4, 1, "f_derecha2"),
            (30,  -1, 0, "g_suelto"),
            (30,   4, 4, "h_izquierda"),   // la 6 = izquierda
            (30,  -1, 0, "i_suelto"),
            (30,   4, 3, "j_arriba"),      // la 7 = arriba
            (30,  -1, 0, "k_suelto"),
            (60,  -1, 0, "l_final"),
        };
        foreach (var (cuantos, row, bit, nombre) in pasos)
        {
            if (row >= 0) m.Keys[row] &= (byte)~(1 << bit);
            m.RunFrames(cuantos);
            if (row >= 0) m.Keys[row] |= (byte)(1 << bit);
            Report(m);
            m.DumpScreen(Path.Combine(OutDir, $"spec_{stamp}_part_{nombre}.raw"));
            Save(m, Path.Combine(OutDir, $"spec_{stamp}_part_{nombre}.png"), 1);
        }

        // Frames seguidos: sirve para ver que se mueve (la nave, las
        // balas, los enemigos) comparando dos capturas consecutivas.
        Console.WriteLine("\n  frames seguidos:");
        for (int i = 0; i < 6; i++)
        {
            m.RunFrames(1);
            m.DumpScreen(Path.Combine(OutDir, $"spec_{stamp}_seq_{i}.raw"));
        }
        Console.WriteLine($"  guardadas en spec_{stamp}_seq_*.raw");

        Console.WriteLine($"\n  capturas en {OutDir}");
        return 0;
    }

    static void Report(SpectrumMachine m)
    {
        var cpu = m.Cpu;
        Console.WriteLine($"  PC=${cpu.PC:X4}  SP=${cpu.SP:X4}  IM={cpu.InterruptMode}  " +
                          $"IFF1={cpu.IFF1}  Halted={cpu.Halted}  " +
                          $"interr={cpu.InterruptsServiced}  altavoz={m.BeeperEdges}");
    }

    /// Vuelca la tabla de atributos como texto para ver si la pantalla
    /// esta girada (el juego desplaza la pantalla rotando las tablas).
    static void DumpAttributes(SpectrumMachine m)
    {
        byte[] attrs = m.ScreenAttributes();
        Console.WriteLine("  atributos (el numero es el color de papel, "
                        + "en mayuscula el de tinta):");
        for (int row = 0; row < 24; row++)
        {
            var sb = new System.Text.StringBuilder("    ");
            for (int col = 0; col < 32; col++)
            {
                int a = attrs[row * 32 + col];
                int paper = (a >> 3) & 7;
                int ink = a & 7;
                sb.Append(paper == 0 && ink == 0 ? '.' :
                          paper == ink ? (char)('0' + paper) :
                          (char)('A' + ink));
            }
            Console.WriteLine(sb.ToString());
        }
    }

    static void Save(SpectrumMachine m, string path, int scale = 1)
    {
        byte[] pixels = m.ScreenPixels();
        byte[] attrs = m.ScreenAttributes();

        // La paleta del Spectrum (el bit 7 es "brillo")
        (int R, int G, int B)[] palette =
        {
            (0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
            (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215),
        };

        int w = 256 * scale, h = 192 * scale;
        byte[] rgb = new byte[w * h * 3];
        for (int row = 0; row < 24; row++)
        {
            for (int col = 0; col < 32; col++)
            {
                int attr = attrs[row * 32 + col];
                int ink = attr & 7;
                int paper = (attr >> 3) & 7;
                for (int y = 0; y < 8; y++)
                {
                    int addr = (row / 8) * 0x100 + (row % 8) * 0x20 + col * 8;
                    int b = pixels[addr + y];
                    for (int x = 0; x < 8; x++)
                    {
                        bool on = (b & (0x80 >> x)) != 0;
                        int c = on ? ink : paper;
                        var (R, G, B) = palette[c];
                        for (int sy = 0; sy < scale; sy++)
                        {
                            for (int sx = 0; sx < scale; sx++)
                            {
                                int px = col * 8 + x, py = row * 8 + y;
                                int o = ((py * scale + sy) * w + px * scale + sx) * 3;
                                rgb[o] = (byte)R;
                                rgb[o + 1] = (byte)G;
                                rgb[o + 2] = (byte)B;
                            }
                        }
                    }
                }
            }
        }
        Png.Write(path, w, h, rgb);
        Console.WriteLine($"  guardada {path}");
    }
}

/// Escribe un PNG sin dependencias externas.
static class Png
{
    public static void Write(string path, int width, int height, byte[] rgb)
    {
        // las lineas del PNG llevan un byte de filtro al principio
        byte[] raw = new byte[height * (1 + width * 3)];
        int p = 0;
        for (int y = 0; y < height; y++)
        {
            raw[p++] = 0;
            Array.Copy(rgb, y * width * 3, raw, p, width * 3);
            p += width * 3;
        }

        using var ms = new MemoryStream();
        ms.Write(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 });

        var ihdr = new byte[13];
        BigEndian(ihdr, 0, width);
        BigEndian(ihdr, 4, height);
        ihdr[8] = 8;      // bits por canal
        ihdr[9] = 2;      // color RGB
        Chunk(ms, "IHDR", ihdr);

        using (var comp = new MemoryStream())
        {
            using (var z = new System.IO.Compression.ZLibStream(
                comp, System.IO.Compression.CompressionLevel.Optimal, true))
            {
                z.Write(raw, 0, raw.Length);
            }
            Chunk(ms, "IDAT", comp.ToArray());
        }

        Chunk(ms, "IEND", Array.Empty<byte>());

        File.WriteAllBytes(path, ms.ToArray());
    }

    static void BigEndian(byte[] b, int o, int v)
    {
        b[o] = (byte)(v >> 24);
        b[o + 1] = (byte)(v >> 16);
        b[o + 2] = (byte)(v >> 8);
        b[o + 3] = (byte)v;
    }

    static void Chunk(Stream s, string type, byte[] data)
    {
        var len = new byte[4];
        BigEndian(len, 0, data.Length);
        s.Write(len);

        var t = System.Text.Encoding.ASCII.GetBytes(type);
        s.Write(t);
        s.Write(data);

        uint crc = Crc32(t, data);
        var c = new byte[4];
        BigEndian(c, 0, (int)crc);
        s.Write(c);
    }

    static readonly uint[] CrcTable = BuildCrcTable();

    static uint[] BuildCrcTable()
    {
        var t = new uint[256];
        for (uint n = 0; n < 256; n++)
        {
            uint c = n;
            for (int k = 0; k < 8; k++)
                c = (c & 1) != 0 ? 0xEDB88320 ^ (c >> 1) : c >> 1;
            t[n] = c;
        }
        return t;
    }

    static uint Crc32(byte[] a, byte[] b)
    {
        uint c = 0xFFFFFFFF;
        foreach (var x in a) c = CrcTable[(c ^ x) & 0xFF] ^ (c >> 8);
        foreach (var x in b) c = CrcTable[(c ^ x) & 0xFF] ^ (c >> 8);
        return c ^ 0xFFFFFFFF;
    }
}






