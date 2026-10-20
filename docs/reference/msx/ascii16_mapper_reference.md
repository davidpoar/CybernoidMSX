# Referencia externa: mapper de cartucho MSX ASCII16

Documento de **referencia** (material externo descargado de Internet) para el
soporte del mapper **ASCII16** implementado en el emulador.

> Documento related: [`../../emulator/plans/ascii16_mapper.md`](../../emulator/plans/ascii16_mapper.md)
> (plan de implementación en el emulador).

Fecha de descarga de todas las fuentes: **2026-10-20**.

---

## 1. Resumen del hardware

El mapper **ASCII16** (también llamado *ASCII 16K*) es un mapa de ROM (MegaROM)
con **dos registros de banco de 16 KB**:

| Ventana | Rango CPU | Registro |
|---|---|---|
| Banco A | `4000h-7FFFh` | `6000h-67FFh` (se usa `6000h`) |
| Banco B | `8000h-BFFFh` | `7000h-77FFh` (se usan `7000h` y `77FFh`) |

- Los registros son de **solo escritura**: no existe lectura de vuelta del valor
  del banco.
- El estado de **reset** deja **banco A = 0** y **banco B = 0**.
- Las páginas 0 (`0000h-3FFFh`) y 3 (`C000h-FFFFh`) **no** están conectadas al
  cartucho: lecturas = `FFh` (bus sin dispositivo), escrituras ignoradas.
- Tamaño de ROM típico: múltiplo de 16 KB, hasta 2 MB.

### 1.1 Distinción con ASCII8

El mapper **ASCII8** (4 bancos de 8 KB, `6000h/6800h/7000h/7800h`) es
**distinto** del ASCII16 (2 bancos de 16 KB, `6000h/7000h`). Confundirlos rompe
el arranque de los juegos, porque el BIOS de MSX1 sondea las direcciones de
registro para detectar el tipo de cartucho.

---

## 2. Fuente: openMSX (emulador de referencia MSX)

- Repositorio: <https://github.com/openMSX/openMSX>
- Fichero del mapper: <https://github.com/openMSX/openMSX/blob/master/src/memory/RomAscii16kB.cc>
  (cabecera: `RomAscii16kB.hh`)
- Clase base con la lógica de bancos: <https://github.com/openMSX/openMSX/blob/master/src/memory/RomBlocks.cc>

### 2.1 `RomAscii16kB.cc` (extracto literal)

```cpp
// ASCII 16kB cartridges
//
// this type is used in a few cartridges.
// example of cartridges: Xevious, Fantasy Zone 2,
// Return of Ishitar, Androgynus, Gallforce ...
//
// The address to change banks:
//  first  16kb: 0x6000 - 0x67ff (0x6000 used)
//  second 16kb: 0x7000 - 0x77ff (0x7000 and 0x77ff used)

void RomAscii16kB::reset(EmuTime /*time*/)
{
	setUnmapped(0);
	setRom(1, 0);
	setRom(2, 0);
	setUnmapped(3);
}

void RomAscii16kB::writeMem(uint16_t address, byte value, EmuTime /*time*/)
{
	if ((0x6000 <= address) && (address < 0x7800) && !(address & 0x0800)) {
		byte region = ((address >> 12) & 1) + 1;
		setRom(region, value);
	}
}

byte* RomAscii16kB::getWriteCacheLine(uint16_t address)
{
	if ((0x6000 <= address) && (address < 0x7800) && !(address & 0x0800)) {
		return nullptr;
	} else {
		return unmappedWrite.data();
	}
}
```

Puntos clave que se han respetado en el emulador:

1. **Decodificación de registros** — el predicado
   `(0x6000 <= address) && (address < 0x7800) && !(address & 0x0800)` es
   exactamente equivalente a:
   - `(addr & 0xF800) == 0x6000` → banco A (`6000h-67FFh`),
   - `(addr & 0xF800) == 0x7000` → banco B (`7000h-77FFh`),
   - `6800h-6FFFh` y `7800h-7FFFh` **no** son registros (bit 11 = `0800h`
     activo → escritura ignorada).
2. **Selección de región** — `((address >> 12) & 1) + 1`: `6000h-6FFFh` →
   región 1 (ventana `4000h-7FFFh`), `7000h-7FFFh` → región 2 (ventana
   `8000h-BFFFh`).
3. **Reset** — páginas 0 y 3 sin mapear (`setUnmapped`), bancos 1 y 2 en el
   banco 0 (`setRom(1, 0)` / `setRom(2, 0)`).
4. **Los registros solo afectan al bus de escrituras** — las *lecturas* en
   `6000h-67FFh` / `7000h-77FFh` devuelven el **contenido de la ROM** del banco
   visible (`RomBlocks::readMem` → `bankPtr[address / BANK_SIZE][...]`), no el
   valor del registro. Es el comportamiento del hardware real.

### 2.2 `RomBlocks.cc` — enmascarado del número de banco (extracto literal)

```cpp
	// Default mask: wraps at end of ROM image.
	blockMask = nrBlocks - 1;
```

```cpp
void RomBlocks<BANK_SIZE>::setRom(unsigned region, unsigned block)
{
	// Note: Some cartridges have a number of blocks that is not a power of 2,
	//       for those we have to make an exception for "block < nrBlocks".
	block = (block < nrBlocks) ? block : block & blockMask;
	if (block < nrBlocks) {
		setBank(region, &rom[block * BANK_SIZE], ...);
	} else {
		setBank(region, unmappedRead.data(), 255);
	}
}
```

Y el relleno de la imagen a un múltiplo del tamaño de banco:

```cpp
	auto extendedSize = (rom.size() + BANK_SIZE - 1) & ~(BANK_SIZE - 1);
	if (extendedSize != rom.size() && ...) {
		config.getCliComm().printWarning(
			"(uncompressed) ROM image filesize was not a multiple "
			"of ", BANK_SIZE / 1024, "kB (which is required for mapper type ", ...);
	}
	rom.addPadding(extendedSize);
```

**Regla de enmascarado adoptada por el emulador** (idéntica a openMSX):

| Nº de bancos | Valor escrito | Banco seleccionado |
|---|---|---|
| `n` potencia de 2 | `v >= n` | `v & (n - 1)` → *mirror* de la imagen |
| `n` no potencia de 2 | `v < n` | `v` (se usa tal cual) |
| `n` no potencia de 2 | `v >= n` | `v & (n - 1)` (≤ `n - 1`, siempre válido) |

Consecuencias:

- Como `v & (n-1) <= n-1 < n`, el índice enmascarado **nunca** queda fuera de
  rango: la ventana nunca se queda "sin banco". La rama de *bus abierto*
  (`setBank(region, unmappedRead...)`) de openMSX es defensiva.
- Una ROM de **48 KB** (3 bancos) con `v = 7` selecciona el banco `7 & 2 = 2`.
- Una ROM de **16 KB** (1 banco) ignora cualquier valor: siempre se ve el banco 0
  (imagen replicada en las dos ventanas).
- La imagen se rellena con `FFh` hasta un múltiplo de 16 KB, por lo que una ROM
  de 8 KB se comporta como una de 16 KB con la mitad superior a `FFh`.

---

## 3. Fuente: MSX Wiki — «MegaROM Mappers»

- URL: <https://www.msx.org/wiki/MegaROM_Mappers> (consultado 2026-10-20)

Extractos relevantes:

> **ASCII 16K**
> Rom size can be up to 2048kB (chip LZ93A13) or 2048kB (chip M60002 or BS6101).
> This mapper is called ASCII16. Several makers use this Rom mapper.
> In addition, the segment 0Fh is same as 17h (the last segment).
> *Page mirrors are not present on many cartridges.*

> **Value format for MegaROMs with an extra SRAM**
> ASCII16 mappers with an SRAM are called ASCII16SRAM2 or ASCII16SRAM8 depending
> the SRAM size.

Notas:

- La remark *"the segment 0Fh is same as 17h"* describe una particularidad de
  cartuchos concretos (el segmento 15 se replica en el 23); **no** es una regla
  general del ASCII16 y no se ha implementado.
- Las variantes con SRAM (`ASCII16SRAM2` / `ASCII16SRAM8`) quedan fuera de
  alcance en el emulador actual.
- El *dump* del wiki indica también la tabla de direcciones de registro por
  mapper (ASCII 8K: `6000h/6800h/7000h/7800h`; ASCII 16K: `6000h/7000h`),
  coherente con la implementación de openMSX.

---

## 4. Fuente: foro MSX — decodificación alternativa del CI ASCII16

- URL: <https://www.msx.org/forum/msx-talk/development/doubt-about-developing-a-128kb-megarom-ascii-16k-mapper>
  (consultado 2026-10-20)

Extracto:

> "ASCII16 mapper IC checks if the address is in the range 6000H-6FFFH or
> 7000H-7FFFH and if so will set the value specified on the data bus into ..."

**Variante documentada:** algunos CI de ASCII16 decodifican el registro con
granularidad de `2000h` (`6000h-6FFFh` y `7000h-7FFFh`) en lugar de `0800h`
(`6000h-67FFh` y `7000h-77FFh`).

**Decisión del emulador:** se implementa la variante de **openMSX**
(`(addr & 0xF800) == 0x6000` / `== 0x7000`), que es la que espera el BIOS de
MSX1 al detectar el tipo de cartucho, tal y como se especifica en el diseño de
este soporte. Si en el futuro se necesita la variante `2000h`, el cambio se
localiza en `Ascii16CartridgeDevice.Write`.

---

## 5. Fuente: especificación ASCII16-X (extensión de ASCII16)

- URL: <https://www.grauw.nl/projects/ascii-x/ascii16-x/> (consultado 2026-10-20)
- Soporte en openMSX desde la versión 20.0 (`src/memory/RomAscii16X.cc`)

Extractos:

> The ASCII16-X mapper has two 16K pages available at 4000H-7FFFH (page 1) and
> 8000H-BFFFH (page 2). For additional flexibility, their contents are also
> mirrored in the other two quadrants of the address space.
> | Page | Page address | Mirror |
> | 1 | 4000H - 7FFFH | C000H - FFFFH |
> | 2 | 8000H - BFFFH | 0000H - 3FFFH |
> To support ROM sizes greater than 4 MB, the bank register takes a 12-bit bank
> number by supplementing the 8 data bits with 4 address bits. The bank
> number's lower eight bits are written in data bits D0-D7 and the high bits in
> address bits A8-A11.
> To allow auto-detection of the ASCII16-X mapper type, it is recommended to put
> the string ASCII16X at ROM offset 00010H (at 4010H in the MSX address space).

Notas:

- ASCII16-X es una **extensión** (12 bits de banco, espejo de páginas, firma
  `ASCII16X` en el offset `0010h` de la ROM) que **no** está implementada en el
  emulador. Se deja documentada como trabajo pendiente.
- La firma `ASCII16X` en `4010h` sugiere una vía futura de **auto-detección**
  del tipo de mapper a partir del contenido de la ROM (hoy el emulador exige
  `--mapper ascii16`).

---

## 6. Ficheros relacionados en openMSX (mapeadores de la familia ASCII)

Listado de `src/memory/` de openMSX (obtenido vía API de GitHub, 2026-10-20):

| Fichero | Descripción |
|---|---|
| `RomAscii16kB.cc` | ASCII 16K (el implementado en este emulador) |
| `RomAscii16_2.cc` | Variante de 2 bancos de ASCII16 |
| `RomAscii16X.cc` | ASCII16-X (extensión con banco de 12 bits) |
| `RomAscii8kB.cc` | ASCII 8K (4 bancos de 8 KB) |
| `RomAscii8_8.cc` | Variante ASCII8 |
| `RomBlocks.cc` | Base común: enmascarado de bancos y relleno de la imagen |

---

## 7. Resumen de lo aplicado en el emulador

| Aspecto | Comportamiento implementado | Fuente |
|---|---|---|
| Ventanas | A: `4000h-7FFFh`, B: `8000h-BFFFh` | openMSX `RomAscii16kB` |
| Registro banco A | `(addr & 0xF800) == 0x6000` | openMSX `RomAscii16kB` |
| Registro banco B | `(addr & 0xF800) == 0x7000` | openMSX `RomAscii16kB` |
| Direcciones no decodificadas | `6800h-6FFFh`, `7800h-7FFFh` | openMSX `RomAscii16kB` |
| Reset | banco A = 0, banco B = 0 | openMSX `RomAscii16kB` |
| Páginas 0 y 3 | sin mapear → `FFh` | openMSX `RomAscii16kB` |
| Lecturas en las direcciones de registro | contenido de la ROM del banco visible | openMSX `RomBlocks::readMem` |
| Enmascarado del banco | `v < n ? v : v & (n-1)` | openMSX `RomBlocks::setRom` |
| ROM < 32 KB | imagen replicada, sin leer fuera del buffer | openMSX (relleno con `FFh`) |
| Tamaño de ROM no múltiplo de 16 KB | se ignoran los bytes sobrantes | openMSX (relleno con `FFh`) |

---

## 8. Validación con juegos reales (descarga y ejecución)

Para verificar el mapper no se han usado solo tests unitarios: se han
**descargado ROMs reales** y ejecutado en el emulador, dejados fuera del
repositorio (directorio temporal del agente).

### 8.1 Fuentes descargadas

| Recurso | URL | Fecha |
|---|---|---|
| BIOS MSX1 (Philips VG-8020, 32 KB) | <https://archive.org/details/msx-system-roms-and-bios_202505> → `MSX System Roms and Bios.zip` → `Philips/vg8020_basic-bios1.rom` | 2026-10-20 |
| Colección de juegos MSX | <https://archive.org/details/MSXRomCollectionByGhostware> | 2026-10-20 |
| `Gall Force (1986) (Sony)` — 128 KB, **ASCII16** | `.../MSXRomCollectionByGhostware/Gall Force (1986) (Sony).zip` | 2026-10-20 |
| `Elevator Action (1985) (Taito)` — 32 KB, **ASCII16** | `.../Elevator Action (1985) (Taito).zip` | 2026-10-20 |
| `Cross Blaim (1985) (dB-Soft)` — 64 KB, **ASCII16** | `.../Cross Blaim (1985) (dB-Soft).zip` | 2026-10-20 |
| `Antarctic Adventure (1984) (Konami)` — 16 KB, ROM plana | `.../Antarctic Adventure (1984) (Konami).zip` | 2026-10-20 |
| `The Maze of Galious (1987) (Konami)` — 128 KB, Konami SCC | `.../Maze of Galious, The (1987) (Konami).zip` | 2026-10-20 |

Comando de ejecución:

```bash
msx\bin\Debug\net10.0\msx.exe -r gallforce.rom --mapper ascii16 --agent-port 5555
```

El control se hizo por el **protocolo de agente** (`msx.run_frames`,
`msx.slots`, `msx.screen.text`, `mem.read`, `cpu.write`).

### 8.2 Resultados

| ROM | Mapper forzado | `slot_register` | Página 1 / 2 | Resultado |
|---|---|---|---|---|
| Gall Force (ASCII16) | `ascii16` | `0xD4` | slot 1 / slot 1 | **El BIOS detecta el cartucho y el juego corre** (pantalla GRAPHIC animada, PC en `0xBCE6`, dentro de la ventana B) |
| Gall Force | `konami` | `0xF0` | slot 0 / slot 3 | El BIOS **no** detecta el cartucho; se queda en la pantalla de copyright |
| Gall Force | `standard` | `0xF0` | slot 0 / slot 3 | Ídem; el BIOS arranca BASIC sin cartucho |
| Elevator Action (ASCII16) | `ascii16` | `0xD4` | slot 1 / slot 1 | Detectado como ASCII16 por el BIOS; el juego dibuja |
| Cross Blaim (ASCII16) | `ascii16` | `0xD4` | slot 1 / slot 1 | Detectado como ASCII16 por el BIOS |
| Antarctic Adventure (16 KB) | `standard` | `0xF4` | slot 1 / slot 3 | Funciona (regresión: la ROM plana sigue bien) |
| The Maze of Galious (Konami SCC) | `konami-scc` | `0xF0` | slot 0 / slot 3 | **El BIOS no lo detecta** → ver §8.5 |

Que el BIOS de MSX1 mapee el cartucho a las **páginas 1 y 2** del mismo slot
(`0xD4`) es la señal de que su rutina de detección de tipo de cartucho ha
identificado un mapper de dos ventanas de 16 KB: el propio BIOS valida la
implementación del mapper ASCII16.

### 8.3 Prueba directa de los registros de banco (en el emulador en marcha)

Se inyectó en RAM (`0xC000`) un programa Z80 que escribe en los registros y
devuelve el primer byte de cada ventana; el resultado se lee por el agente:

```
LD A,3   ; LD (6000h),A   ; banco A = 3
LD A,(4000h)              ; -> 0xC100
LD A,5   ; LD (7000h),A   ; banco B = 5
LD A,(8000h)              ; -> 0xC101
```

Con `Gall Force` (8 bancos de 16 KB; primer byte de cada banco:
`0:41 1:56 2:FF 3:C2 4:58 5:E0 6:06 7:02`):

| Operación | Leído | Esperado | |
|---|---|---|---|
| banco A = 3 → `4000h` | `0xC2` | `0xC2` | OK |
| banco B = 5 → `8000h` | `0xE0` | `0xE0` | OK |
| banco A = 99 (`99 & 7 = 3`) → `4000h` | `0xC2` | `0xC2` | OK (mirror) |
| banco B = 55 (`55 & 7 = 7`) → `8000h` | `0x02` | `0x02` | OK (mirror) |

### 8.4 Hallazgo: cabecera ROM no estándar en la colección "Ghostware"

Las ROMs de la colección `MSXRomCollectionByGhostware` **no** usan la cabecera
estándar de MSX. En lugar de

```
4000h: 41 42 4D 53 58 00 00 00    "AB" "MSX" 00 00 00
4008h: <init lo> <init hi>
```

contienen una cabecera compacta de 16 bytes:

```
4000h: 41 42 10 40 00 00 00 00 00 00 00 00 00 00 00 00
        "AB" <init?> 00 ...
```

- `4002h-4003h` = dirección de inicio (0x4010 en la mayoría, 0x4084 en
  *Cross Blaim*).
- `4008h-4009h` (INIT en formato estándar) = `0000`.
- No aparece la cadena `"MSX"` en el fichero.

Aun así, el BIOS de MSX1 arranca el cartucho: su rutina de detección comprueba
únicamente la firma `"AB"` en `4000h-4001h` (comparación `RST 10h` con `4241h`
en `7D8Ah` del BIOS) y el resto de campos no son necesarios para el arranque.
La posición 0x4000 del fichero corresponde a la CPU 0x4000, es decir, el
contenido del banco 0 se ve en la ventana A tal y como espera el hardware.

### 8.5 Limitación pendiente: mapper Konami-SCC

*The Maze of Galious* (Konami SCC) **no** es detectado por el BIOS con el
mapper `konami-scc` del emulador. El motivo es que
`KonamiSccCartridgeDevice` decodifica los registros en `6000h-7FFFh`,
`8000h-9FFFh`, `A000h-BFFFh` y `B000h-B7FFh`, mientras que el Konami SCC real
usa `5000h-57FFh`, `7000h-77FFh`, `9000h-97FFh` y `B000h-B7FFh` (ver
`KonamiUltimateCollection.cc` de openMSX, §2). Es un **problema preexistente
del emulador**, ajeno al soporte ASCII16, y queda como trabajo pendiente.

