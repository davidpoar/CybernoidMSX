# Estado del port de Cybernoid a MSX

Fecha: 20 de octubre de 2026

## Lo que hay

### La ROM MSX (`msx/build/cybernoid.rom`, 65536 bytes)

Un cartucho ASCII16 de 64 KB con el motor en el banco 0 y los assets
convertidos en el banco 1.

| | |
|---|---|
| Arranca | el BIOS de MSX1 lo detecta y mapea a las paginas 1 y 2 |
| Autotest del mapper | pasa (le los tres bancos y comprueba su byte ID) |
| VDP | modo grafico 2 con los registros correctos |
| VRAM | se carga durante el vblank, 256 bytes por frame |
| Pantalla | muestra los graficos originales de Cybernoid convertidos a tiles |
| PSG | silenciado, sin ruido |
| Interrupcion | la ISR propia en el hook `$FD9F` del BIOS |

Verificado con el emulador MSX de z80emu (captura de pantalla) y con
el harness de pruebas (`CYBERNOID_ROM=1`).

### Las herramientas

| | |
|---|---|
| `msx/scripts/build_rom.py` | construye la ROM |
| `msx/scripts/verify_rom.py` | 25 comprobaciones estaticas sobre la ROM |
| `msx/scripts/convert_spectrum.py` | convierte la pantalla del Spectrum en las tablas del modo 2 |
| `msx/scripts/test_rom_emulator.py` | prueba la ROM en el emulador |
| `msx/scripts/emu_check.py` | compara la ROM con ROMs ASCII16 reales |
| `msx/scripts/diag_rom.py` | diagnostico con breakpoints |
| `msx/scripts/capture_rom.ps1` | captura la ventana del emulador |
| `msx/test/SpectrumTest.cs` | un Spectrum 48K minimo que ejecuta el juego original |
| `tools/` | analisis de la imagen de memoria, desensamblador, referencias |

### La documentacion

* `docs/PORTING_GUIDE.md`: todo lo aprendido, escrito para servir en
  otros ports. Es la parte mas valiosa del repositorio.
* `docs/cybernoid/`: el analisis de este juego en concreto.
* `docs/reference/`: el MSX Red Book, la referencia del mapper
  ASCII16, el desensamblado del ROM del Spectrum, el libro del ULA y
  la documentacion del Z80.

## Lo que NO hay

**La logica del juego.** La ROM enseña la pantalla del juego original
convertida, pero no se juega: no hay nave, ni disparos, ni enemigos,
ni scroll, ni musica.

El motivo no es el hardware: es que el juego del Spectrum son 39 676
bytes de Z80 con unas 1 200 referencias absolutas, escritos para un
sistema con 40 KB de RAM escribible y un framebuffer de 6 KB que se
puede tocar a pelo. El modo grafico 2 del MSX no puede escribir en la
VRAM fuera del vblank, no puede desplazar la pantalla un pixel y solo
tiene 32 sprites. Portar la logica es reescribir el juego, no
adaptarlo.

Ademas, el fondo del juego original se dibuja con un recurso que
depende del scroll de 1 pixel por frame, y en el modo 2 el scroll
solo puede ser de 8 en 8 pixels (o hay que rehacer la tabla de
nombres en cada frame).

## Como seguir

El camino corto, en este orden:

1. **La nave y el control.** Leer el teclado del MSX por la PPI
   (`$AA` selecciona la fila, `$A9` devuelve las columnas, en activo
   bajo), mover un sprite del VDP con las flechas. El esqueleto del
   motor ya esta: el bucle principal corre a 50 Hz y la ISR del
   vblank es el sitio donde tocar la VRAM.
2. **El disparo.** Un segundo sprite (o dos, para el laser) y una
   lista de posiciones en la RAM.
3. **El fondo.** Habria que rehacer la conversion: en vez de dar un
   patron propio a cada celda, conviene detectar los tiles que se
   repiten y construir un conjunto pequeno de patrones con una tabla
   de nombres que se pueda desplazar.
4. **Los enemigos.** Cada tipo de enemigo es una rutina de movimiento
   y un sprite.
5. **La musica.** El driver del Spectrum esta en `$85BA` con las
   tablas en `$8710`; el PSG puede hacer lo mismo con la tabla de
   notas.

## Notas sobre z80emu

No se ha modificado nada del repositorio z80emu. Se ha usado solo
para depurar:

* el emulador MSX, con su protocolo de control por TCP, para
  arrancar la ROM y capturar la pantalla
* el emulador de Spectrum, que resulto inservible para esto: su
  `48.rom` es un relleno de un solo byte y en modo agente no genera
  las interrupciones de frame

Por eso el harness del Spectrum (`msx/test/SpectrumTest.cs`) es
propio: usa el nucleo Z80 que el proyecto ya tenia, sin tocar
z80emu.
