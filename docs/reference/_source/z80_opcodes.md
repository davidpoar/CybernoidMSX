# Guía de Implementación de Opcodes del Z80

Este documento describe la arquitectura y estándares adoptados para escalar la implementación de las instrucciones (opcodes) de la CPU Z80.

---

## 1. Estructura de Clases Parciales

La clase `Z80` es una clase parcial dividida en múltiples archivos para evitar un código fuente excesivamente grande y desordenado:

*   [Z80.cs](file:///home/david/dev/z80emu/Z80/Z80.cs): Estado del procesador (registros, flags, memoria, ciclo principal de ejecución).
*   [Z80.Opcodes.Main.cs](file:///home/david/dev/z80emu/Z80/Z80.Opcodes.Main.cs): Tabla de opcodes primarios (los 256 básicos sin prefijo).
*   `Z80.Opcodes.CB.cs`: Operaciones de bits, rotaciones y desplazamientos (prefijo `0xCB`).
*   `Z80.Opcodes.ED.cs`: Instrucciones extendidas (prefijo `0xED`).
*   `Z80.Opcodes.Indexed.cs`: Instrucciones que usan los registros de índice `IX` e `IY` (prefijos `0xDD` y `0xFD`).

---

## 2. Decodificación por Patrones e Índices de Registros

Las instrucciones del Z80 se agrupan en octetos y bits estructurados. En lugar de crear un método de C# por cada opcode individual, agrupamos opcodes con el mismo comportamiento físico.

### Índices de Registros de 8 Bits (`GetRegister8` / `SetRegister8`)
El Z80 identifica los registros de 8 bits usando 3 bits (0 al 7):

| Índice | Registro | Nota |
| :--- | :--- | :--- |
| **0** | `B` | |
| **1** | `C` | |
| **2** | `D` | |
| **3** | `E` | |
| **4** | `H` | |
| **5** | `L` | |
| **6** | `(HL)` | Apuntador a celda de memoria `ram[HL]` |
| **7** | `A` | Acumulador |

---

## 3. Inicialización Eficiente de la Tabla

Mantenemos la velocidad de ejecución directa del bucle principal `opcodes[opcode]()` inicializando las entradas de la tabla usando bucles de patrones al arrancar:

### Ejemplo para `LD r, r'` (Opcodes `0x40` a `0x7F`, excepto `0x76`):
```csharp
for (int op = 0x40; op <= 0x7F; op++)
{
    if (op == 0x76) continue; // HALT
    int dest = (op >> 3) & 0x07;
    int src = op & 0x07;
    opcodes[op] = () => {
        SetRegister8(dest, GetRegister8(src));
        cycles += (dest == 6 || src == 6) ? 7 : 4;
    };
}
```

### Ejemplo para `LD r, n` (Opcodes `0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E`):
Patrón binario: `00yyy110` (donde `yyy` es el registro destino).
```csharp
for (int reg = 0; reg < 8; reg++)
{
    int op = (reg << 3) | 0x06;
    int targetReg = reg;
    opcodes[op] = () => {
        byte value = Fetch8();
        SetRegister8(targetReg, value);
        cycles += (targetReg == 6) ? 10 : 7;
    };
}
```

---

## 4. Funciones Auxiliares de Lectura e Incremento

*   `Fetch8()`: Lee `ram[PC]` y hace `PC++`.
*   `Fetch16()`: Lee dos bytes consecutivos, los combina en un `ushort` Little Endian y avanza `PC` dos veces.

---

## 5. Entrada/Salida (I/O) y Mapeo de Puertos

El Z80 interactúa con periféricos externos mediante los opcodes `IN` y `OUT`. Se han implementado los delegados:
*   `public InputDelegate? OnInputPort;`
*   `public OutputDelegate? OnOutputPort;`

En el emulador de MSX, el VDP (TMS9918) se mapea a los puertos `0x98` y `0x99`:
*   **Puerto 0x98 (Datos VDP)**:
    *   Escritura: Invoca `vdp.WriteData(value)`.
    *   Lectura: Invoca `vdp.ReadData()`.
*   **Puerto 0x99 (Control / Estado VDP)**:
    *   Escritura: Invoca `vdp.WriteControl(value)`.
    *   Lectura: Invoca `vdp.ReadStatus()`.

---

## 6. Emulación Frame-by-Frame y Carga de BIOS

Para evitar bloquear el hilo de ejecución principal de MonoGame, implementamos:
1.  **Ejecución Paso a Paso (`Step`)**:
    *   `cpu.Step()` ejecuta una única instrucción y devuelve los ciclos consumidos.
    *   En cada frame (`Update`), se ejecutan instrucciones en un bucle hasta alcanzar la cuota de ciclos de un frame completo en MSX (3.58 MHz / 60 fps ≈ `59,659` ciclos).
2.  **Carga de BIOS ROM y Fallback**:
    *   El emulador busca `msx.rom` o `vg8020_basic-bios1.rom` en el directorio de ejecución actual o de base de la app.
    *   **Si se encuentra**: Se carga en `0x0000 - 0x7FFF` de la memoria RAM del CPU y arranca la emulación.
    *   **Si no se encuentra**: Imprime en consola un mensaje explicativo y amigable indicando las rutas donde el usuario puede colocar la ROM, y activa una pantalla interactiva de pruebas (bouncing sprite) para que el emulador siga siendo funcional.
    *   **Control de Errores (CPU crash)**: Si la BIOS ejecuta un opcode que no está implementado y lanza una excepción, el sistema la captura, la muestra por consola indicando el PC problemático, y regresa de forma segura al modo de prueba interactiva en lugar de colgarse.

---

## 7. Emulación de Teclado y PPI (Intel 8255)

El teclado y los slots del MSX1 se gestionan a través de los puertos I/O del chip PPI (`0xA8`, `0xA9`, `0xAA`):
*   **Puerto 0xA8 (Registro de Slots)**:
    *   Lectura/Escritura del estado de selección de slots primarios (`primarySlotRegister`).
*   **Puerto 0xA9 (Datos de Columnas de Teclado)**:
    *   Lectura: Devuelve un byte que contiene el estado de las 8 columnas para la fila seleccionada (lógica active-low, `0` indica tecla pulsada).
*   **Puerto 0xAA (Selector de Fila de Teclado)**:
    *   Escritura: Escribe el selector de fila (bits 0-3 de port `0xAA` determinan la fila de la matriz, del 0 al 10).

Cada frame, el estado físico del teclado del ordenador anfitrión se lee mediante MonoGame (`Keyboard.GetState()`) y se traduce a la matriz bidimensional interna `keyboardMatrix[16]` que la CPU consulta mediante el PPI.
