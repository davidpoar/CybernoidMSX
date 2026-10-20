;==========================================================
; Cybernoid MSX - el juego
;----------------------------------------------------------
; La logica va en el manejador de vblank, una vez por frame
; (50 Hz).  Cybernoid no hace scroll continuo: cada "habitacion"
; es una pantalla completa, asi que aqui solo hay que mover los
; objetos.
;
; El teclado del MSX (matriz de 11 filas x 8 columnas, se lee con
; la PPI: $A8 selecciona la fila y $A9 devuelve las columnas, en
; activo bajo):
;
;   fila 0: 0 1 2 3 4 5 6 7      (bit 0 = la tecla '0')
;   fila 5: s t u v w x y z
;   fila 7: F4 F5 ESC TAB BREAK (BS) SELECT RETURN
;   fila 8: SPACE HOME INS DEL LEFT UP DOWN RIGHT
;
; Los sprites del VDP: 32 de 8x8, en la tabla de atributos de
; $1B00 (Y, X, nombre, atributo).  Y = 0 es la primera linea
; visible y Y = 255 las esconde; Y = 208 para el sprite es la
; senal de parada.  El patron se busca en la tabla de patrones de
; sprites ($3800) y el color es el nibble bajo del atributo (0 =
; transparente).
;==========================================================

;----------------------------------------------------------
; Estados del juego
;----------------------------------------------------------
EST_TITULO equ 0              ; el menu original
EST_JUEGO  equ 1              ; en partida
EST_MUERTO equ 2              ; la nave acaba de explotar

MAX_BALAS    equ 8
MAX_ENEMIGOS equ 8

; Los sprites que usa el motor
SPR_NAVE     equ 0            ; 4 sprites (16x16)
SPR_BALA     equ 4            ; 8 sprites
SPR_ENEMIGO  equ 12           ; 8 sprites
SPR_EXPLO    equ 20           ; 4 sprites

; El desplazamiento en la tabla de sprites del primer enemigo
SPR_ENEMIGO_OFF equ (SPR_ENEMIGO + MAX_BALAS) * 4

;----------------------------------------------------------
; Variables (pagina 3)
;----------------------------------------------------------
game_estado equ $C020
game_score  equ $C021         ; 3 bytes, en decimal
game_vidas  equ $C024
game_etapa  equ $C025
game_timer  equ $C026         ; frames que faltan para la etapa
game_pausa  equ $C027
; La tabla de sprites (32 x 4 = 128 bytes) va aparte: si se solapase
; con las variables del juego las pisaria.
game_spr    equ $C200

nave_x      equ $C0B0
nave_y      equ $C0B1
nave_dx     equ $C0B2
nave_dy     equ $C0B3
nave_fire   equ $C0B4
nave_lim    equ $C0B5

balas_x     equ $C0C0         ; MAX_BALAS bytes
balas_y     equ $C0C8
balas_viva  equ $C0D0

enem_x      equ $C0E0
enem_y      equ $C0E8
enem_tipo   equ $C0F0
enem_fase   equ $C0F8
enem_viva   equ $C100

key_flechas equ $C060
key_digitos equ $C061
key_antes  equ $C062
hud_score  equ $C064
hud_digitos equ $C066      ; 5 bytes
sound_off  equ $C070

;----------------------------------------------------------
; GAME_FRAME - la logica del juego, una vez por frame
;----------------------------------------------------------
GAME_FRAME:
        ld   a, (game_estado)
        cp   EST_TITULO
        jp   z, g_titulo
        cp   EST_JUEGO
        jp   z, g_juego
        ; EST_MUERTO: la explosion y la espera
        ld   a, (game_pausa)
        dec  a
        ld   (game_pausa), a
        jp   nz, g_fin
        ld   a, (game_vidas)
        and  a
        jp   z, g_game_over
        ld   a, EST_JUEGO
        ld   (game_estado), a
        jp   g_fin
g_game_over:
        ld   a, EST_TITULO
        ld   (game_estado), a
        jp   g_fin

g_titulo:
        call READ_KEY
        ; la tecla 1 empieza la partida
        ld   a, (key_digitos)
        cpl
        and  $02                  ; la tecla '1' es el bit 1
        jp   z, g_fin
        call START_GAME
        jp   g_fin

g_juego:
        call READ_KEY
        call MOVE_SHIP
        call MOVE_BULLETS
        call MOVE_ENEMIES
        call COLLISIONS
        call UPDATE_SPRITES
        ret

g_fin:
        call UPDATE_SPRITES
        ret

;----------------------------------------------------------
; START_GAME - empieza una partida
;----------------------------------------------------------
START_GAME:
        ld   a, EST_JUEGO
        ld   (game_estado), a
        xor  a
        ld   (game_score), a
        ld   (game_score+1), a
        ld   (game_score+2), a
        ld   a, 3
        ld   (game_vidas), a
        ld   a, 1
        ld   (game_etapa), a
        ld   a, 60
        ld   (game_timer), a
        ; la nave en el centro abajo
        ld   a, 112
        ld   (nave_x), a
        ld   a, 150
        ld   (nave_y), a
        ld   a, 0
        ld   (nave_dx), a
        ld   (nave_dy), a
        ld   (nave_fire), a         ; el enfriamiento del disparo
        ld   (hud_score), a         ; lo que hay en el marcador
        ld   a, 0
        ld   (game_pausa), a
        ; limpia las listas
        call CLEAR_ENEMIGOS
        call CLEAR_BALAS
        ; cambia a la pantalla del juego
        call SET_GAME_SCREEN
        ret

;----------------------------------------------------------
; READ_KEY - lee el teclado del MSX
;----------------------------------------------------------
; Solo hacen falta dos filas: la 8 (las flechas y el espacio) y
; la 0 (los digitos, para el menu).
;----------------------------------------------------------
READ_KEY:
        ; El selector de fila va por el puerto C de la PPI ($AA).
        ; OJO: el puerto A ($A8) en el MSX1 es el registro de slots
        ; (WRSLREG), no la PPI: escribir ahi desmapearia el
        ; cartucho.
        ld   a, $08
        out  (PPI_C), a
        in   a, (PPI_B)
        ld   (key_flechas), a
        xor  a
        out  (PPI_C), a
        in   a, (PPI_B)
        ld   (key_digitos), a
        ret

;----------------------------------------------------------
; MOVE_SHIP - mueve la nave y dispara
;----------------------------------------------------------
; Las flechas van en la fila 8: LEFT bit 4, UP bit 5, DOWN bit 6
; y RIGHT bit 7.  El espacio es el bit 0.
;----------------------------------------------------------
MOVE_SHIP:
        ld   a, (key_flechas)
        cpl                        ; las teclas pulsadas a 1
        ld   b, a

        ; --- la direccion ---
        ld   c, 0                  ; dx
        ld   e, 0                  ; dy
        ld   a, b
        and  $10                   ; izquierda
        jr   z, msh_der
        dec  c
msh_der:
        ld   a, b
        and  $80                   ; derecha
        jr   z, msh_arr
        inc  c
msh_arr:
        ld   a, b
        and  $20                   ; arriba
        jr   z, msh_abj
        dec  e
msh_abj:
        ld   a, b
        and  $40                   ; abajo
        jr   z, msh_pos
        inc  e
msh_pos:
        ; --- la posicion, limitada a la pantalla ---
        ld   a, (nave_x)
        add  a, c
        cp   16
        jr   nc, msh_x1            ; si es >= 16, vale
        ld   a, 16
msh_x1:
        cp   240
        jr   c, msh_x2             ; si es < 240, vale
        ld   a, 240
msh_x2:
        ld   (nave_x), a
        ld   a, (nave_y)
        add  a, e
        cp   16
        jr   nc, msh_y1
        ld   a, 16
msh_y1:
        cp   176
        jr   c, msh_y2
        ld   a, 176
msh_y2:
        ld   (nave_y), a

        ; --- el disparo ---
        ld   a, (nave_fire)
        and  a
        jp   nz, msh_no_fire
        ld   a, b
        and  $01                  ; el espacio
        jp   z, msh_fire_cd
        call SPAWN_BALA
        ld   a, 10
        ld   (nave_fire), a
        ret
msh_fire_cd:
        ; el enfriamiento baja, pero sin pasar de cero (un "dec a"
        ; con 0 daria 255 y el disparo no volveria a funcionar)
        ld   a, (nave_fire)
        and  a
        ret  z
        dec  a
        ld   (nave_fire), a
msh_no_fire:
        ret

;----------------------------------------------------------
; SPAWN_BALA - lanza una bala
;----------------------------------------------------------
SPAWN_BALA:
        ld   b, 0
sb_loop:
        ld   a, b
        cp   MAX_BALAS
        ret  z
        ld   hl, balas_viva
        add  a, l
        ld   l, a
        ld   a, b
        and  a
        jp   z, sb_ok
        ld   a, (hl)
        and  a
        jp   z, sb_ok
        inc  b
        jp   sb_loop
sb_ok:
        ; la posicion: encima de la nave
        ld   a, b
        ld   hl, balas_x
        add  a, l
        ld   l, a
        ld   a, (nave_x)
        add  a, 7
        ld   (hl), a
        ld   a, b
        ld   hl, balas_y
        add  a, l
        ld   l, a
        ld   a, (nave_y)
        add  a, 254          ; resta 2 (modulo 256)
        ld   (hl), a
        ; y la marca como viva
        ld   a, b
        ld   hl, balas_viva
        add  a, l
        ld   l, a
        ld   a, 1
        ld   (hl), a
        ; el sonido
        call SOUND_SHOT
        ret

;----------------------------------------------------------
; MOVE_BULLETS
;----------------------------------------------------------
MOVE_BULLETS:
        ld   b, 0
mb_loop:
        ld   a, b
        cp   MAX_BALAS
        ret  z
        ld   hl, balas_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, mb_next
        ; sube
        ld   a, b
        ld   hl, balas_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        add  a, 252          ; resta 4 (modulo 256)
        ld   (hl), a
        ; fuera de pantalla?
        ld   a, (hl)
        cp   250
        jp   nc, mb_del
        jp   mb_next
mb_del:
        ld   hl, balas_viva
        ld   a, b
        add  a, l
        ld   l, a
        xor  a
        ld   (hl), a
mb_next:
        inc  b
        jp   mb_loop

;----------------------------------------------------------
; MOVE_ENEMIES - los mueve y van apareciendo
;----------------------------------------------------------
; Tres tipos:
;   0  un dron que baja recto
;   1  uno que baja en diagonal
;   2  una bomba que baja y se acelera
;----------------------------------------------------------
MOVE_ENEMIES:
        ld   b, 0
me_loop:
        ld   a, b
        cp   MAX_ENEMIGOS
        jp   z, me_spawn
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, me_next
        ; el tipo
        ld   a, b
        ld   hl, enem_tipo
        add  a, l
        ld   l, a
        ld   a, (hl)
        cp   2
        jp   z, me_bomba
        ; el dron o el diagonal: baja 1 y se mueve de lado
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        inc  a
        ld   (hl), a
        ld   a, b
        ld   hl, enem_fase
        add  a, l
        ld   l, a
        ld   a, (hl)
        inc  a
        ld   (hl), a
        ; el desplazamiento lateral segun la fase
        ld   a, b
        ld   hl, enem_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   c, a
        ld   a, b
        ld   hl, enem_fase
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  $04
        jp   z, me_izq
        inc  c
        jp   me_px
me_izq:
        dec  c
me_px:
        ld   a, c
        cp   8
        jp   nc, me_pz
        ld   a, 8
me_pz:
        ld   c, a
        cp   248
        jp   c, me_pw
        ld   a, 248
me_pw:
        ld   (hl), a
        ; fuera de pantalla?
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        cp   200
        jp   nc, me_del
        jp   me_next
me_bomba:
        ; la bomba baja mas rapido
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        add  a, 2
        ld   (hl), a
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        cp   200
        jp   nc, me_del
        jp   me_next
me_del:
        ld   hl, enem_viva
        ld   a, b
        add  a, l
        ld   l, a
        xor  a
        ld   (hl), a
        jp   me_next
me_next:
        inc  b
        jp   me_loop

;--- van apareciendo ---
me_spawn:
        ; el timer baja cada frame: cuando llega a cero aparece un
        ; enemigo nuevo
        ld   a, (game_timer)
        and  a
        jp   z, me_spawn_now
        dec  a
        ld   (game_timer), a
        ret
me_spawn_now:
        ld   a, 40
        ld   (game_timer), a
        call SPAWN_ENEMY
        ret

;----------------------------------------------------------
; SPAWN_ENEMY - pone un enemigo nuevo
;----------------------------------------------------------
SPAWN_ENEMY:
        ld   b, 0
se_loop:
        ld   a, b
        cp   MAX_ENEMIGOS
        ret  z
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, se_ok
        inc  b
        jp   se_loop
se_ok:
        ; la posicion
        ld   a, b
        ld   hl, enem_x
        add  a, l
        ld   l, a
        ld   a, (game_etapa)
        add  a, a
        add  a, a
        add  a, 16
        ld   c, a
        ld   a, b
        add  a, c
        ld   c, a
        cp   240
        jp   c, se_x1
        ld   a, 240
se_x1:
        ld   (hl), a
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        xor  a
        ld   (hl), a
        ; el tipo y la fase
        ld   a, b
        ld   hl, enem_tipo
        add  a, l
        ld   l, a
        ld   a, (game_etapa)
        and  $03
        ld   (hl), a
        ld   a, b
        ld   hl, enem_fase
        add  a, l
        ld   l, a
        ld   a, (game_etapa)
        ld   (hl), a
        ; viva
        ld   a, b
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, 1
        ld   (hl), a
        ret

;----------------------------------------------------------
; CLEAR_ENEMIGOS / CLEAR_BALAS
;----------------------------------------------------------
CLEAR_ENEMIGOS:
        ld   hl, enem_viva
        ld   b, MAX_ENEMIGOS
        xor  a
ce_loop:
        ld   (hl), a
        inc  hl
        dec  b
        jp   nz, ce_loop
        ret

CLEAR_BALAS:
        ld   hl, balas_viva
        ld   b, MAX_BALAS
        xor  a
cb_loop:
        ld   (hl), a
        inc  hl
        dec  b
        jp   nz, cb_loop
        ret

;----------------------------------------------------------
; COLLISIONS - balas contra enemigos y nave contra enemigos
;----------------------------------------------------------
COLLISIONS:
        ; --- las balas contra los enemigos ---
        ld   b, 0
co_b_loop:
        ld   a, b
        cp   MAX_BALAS
        jp   z, co_n_loop
        ld   hl, balas_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, co_b_next
        ; la posicion de la bala
        ld   a, b
        ld   hl, balas_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   c, a                  ; cx
        ld   a, b
        ld   hl, balas_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   d, a                  ; cy
        ; contra cada enemigo
        ld   e, 0
co_e_loop:
        ld   a, e
        cp   MAX_ENEMIGOS
        jp   z, co_b_next
        push hl
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, co_e_next
        ; la posicion del enemigo
        ld   a, e
        ld   hl, enem_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        sub  c
        cp   9
        jp   nc, co_e_far
        cp   247
        jp   c, co_e_far
        ld   a, e
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        sub  d
        cp   9
        jp   nc, co_e_far
        cp   247
        jp   c, co_e_far
        ; impacto!
        call KILL_ENEMY
        pop hl
        jp   co_b_next
co_e_far:
        pop hl
co_e_next:
        inc  e
        jp   co_e_loop
co_b_next:
        inc  b
        jp   co_b_loop

        ; --- la nave contra los enemigos ---
co_n_loop:
        ld   a, (nave_x)
        ld   c, a
        ld   a, (nave_y)
        ld   d, a
        ld   e, 0
co_n_e:
        ld   a, e
        cp   MAX_ENEMIGOS
        ret  z
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, co_n_next
        ld   a, e
        ld   hl, enem_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        sub  c
        cp   9
        jp   nc, co_n_far
        cp   247
        jp   c, co_n_far
        ld   a, e
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        sub  d
        cp   9
        jp   nc, co_n_far
        cp   247
        jp   c, co_n_far
        ; la nave ha sido alcanzada
        call KILL_SHIP
        ret
co_n_far:
co_n_next:
        inc  e
        jp   co_n_e

;----------------------------------------------------------
; KILL_ENEMY - un enemigo explota y suma puntos
;----------------------------------------------------------
KILL_ENEMY:
        ; el enemigo 'e' (en el registro E)
        ld   a, e
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        xor  a
        ld   (hl), a
        ; +100 puntos
        ld   a, (game_score+2)
        inc  a
        ld   (game_score+2), a
        ld   a, (game_score+1)
        adc  a, 0
        ld   (game_score+1), a
        ld   a, (game_score)
        adc  a, 0
        ld   (game_score), a
        call SOUND_EXPLODE
        ret

;----------------------------------------------------------
; KILL_SHIP - la nave explota
;----------------------------------------------------------
KILL_SHIP:
        ld   a, (game_vidas)
        dec  a
        ld   (game_vidas), a
        ld   a, EST_MUERTO
        ld   (game_estado), a
        ld   a, 60
        ld   (game_pausa), a
        call SOUND_EXPLODE
        ret

;----------------------------------------------------------
; UPDATE_SPRITES - monta la tabla de atributos de los sprites
;----------------------------------------------------------
; 32 sprites de 4 bytes: Y, X, nombre, atributo.  Se montan en la
; RAM y luego se copian a la VRAM (que solo se puede escribir en
; el vblank).  Y = 208 es la senal de parada: a partir de ahi el
; VDP no dibuja mas sprites.
;----------------------------------------------------------
UPDATE_SPRITES:
        ld   hl, game_spr
        ld   b, 128
        xor  a
us_clear:
        ld   (hl), a
        inc  hl
        dec  b
        jp   nz, us_clear

        ld   hl, game_spr

        ; --- la nave: 4 sprites de 8x8 (16x16) ---
        ld   a, (game_estado)
        cp   EST_MUERTO
        jp   z, us_nave_muerta
        ld   a, (nave_x)
        ld   c, a
        ld   a, (nave_y)
        ld   d, a
        ; 0: arriba izquierda
        ld   (hl), a
        inc  hl
        ld   a, c
        ld   (hl), a
        inc  hl
        ld   a, 0
        ld   (hl), a
        inc  hl
        ld   a, 15                 ; blanco
        ld   (hl), a
        inc  hl
        ; 1: arriba derecha
        ld   a, d
        ld   (hl), a
        inc  hl
        ld   a, c
        add  a, 8
        ld   (hl), a
        inc  hl
        ld   a, 1
        ld   (hl), a
        inc  hl
        ld   a, 15
        ld   (hl), a
        inc  hl
        ; 2: abajo izquierda
        ld   a, d
        add  a, 8
        ld   (hl), a
        inc  hl
        ld   a, c
        ld   (hl), a
        inc  hl
        ld   a, 2
        ld   (hl), a
        inc  hl
        ld   a, 15
        ld   (hl), a
        inc  hl
        ; 3: abajo derecha
        ld   a, d
        add  a, 8
        ld   (hl), a
        inc  hl
        ld   a, c
        add  a, 8
        ld   (hl), a
        inc  hl
        ld   a, 3
        ld   (hl), a
        inc  hl
        ld   a, 15
        ld   (hl), a
        inc  hl
        jp   us_balas
us_nave_muerta:
        ; oculta la nave: Y = 208
        ld   a, 208
        ld   (hl), a

        ; --- las balas ---
us_balas:
        ld   b, 0
        ld   de, SPR_BALA * 4
us_b_loop:
        ld   a, b
        cp   MAX_BALAS
        jp   z, us_enemigos
        ; esta viva?
        ld   a, b
        ld   hl, balas_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, us_b_next
        ; la escribe
        push de
        ld   a, b
        ld   hl, balas_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   (de), a          ; el Y
        inc  de
        ld   a, b
        ld   hl, balas_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   (de), a          ; el X
        inc  de
        ld   a, 4              ; el patron de la bala
        ld   (de), a
        inc  de
        ld   a, 14             ; amarillo
        ld   (de), a
        inc  de
        pop  de
        jp   us_b_fin
us_b_next:
        ; hueco: la senal de parada
        ld   a, 208
        ld   (de), a
us_b_fin:
        inc  de
        inc  b
        jp   us_b_loop

        ; --- los enemigos ---
us_enemigos:
        ld   b, 0
        ld   de, SPR_ENEMIGO_OFF
us_e_loop:
        ld   a, b
        cp   MAX_ENEMIGOS
        jp   z, us_fin
        ld   a, b
        ld   hl, enem_viva
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  a
        jp   z, us_e_next
        push de
        ld   a, b
        ld   hl, enem_y
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   (de), a
        inc  de
        ld   a, b
        ld   hl, enem_x
        add  a, l
        ld   l, a
        ld   a, (hl)
        ld   (de), a
        inc  de
        ; el patron segun el tipo
        ld   a, b
        ld   hl, enem_tipo
        add  a, l
        ld   l, a
        ld   a, (hl)
        add  a, 5              ; 5, 6 y 7
        ld   (de), a
        inc  de
        ; el color segun el tipo
        ld   a, b
        ld   hl, enem_tipo
        add  a, l
        ld   l, a
        ld   a, (hl)
        and  $01
        jp   z, us_e_rojo
        ld   a, 13              ; magenta
        jp   us_e_col
us_e_rojo:
        ld   a, 9               ; rojo
us_e_col:
        ld   (de), a
        inc  de
        pop  de
        jp   us_e_fin
us_e_next:
        ld   a, 208
        ld   (de), a
us_e_fin:
        inc  de
        inc  b
        jp   us_e_loop

us_fin:
        ; la senal de parada
        ld   a, 208
        ld   (de), a
        ret

;----------------------------------------------------------
; SPRITES_TO_VRAM - copia la tabla de sprites a la VRAM
;----------------------------------------------------------
SPRITES_TO_VRAM:
        ld   a, $00
        out  (VDP_CMD), a
        ld   a, $1B | $40
        out  (VDP_CMD), a
        ld   hl, game_spr
        ld   b, 128
stv_loop:
        ld   a, (hl)
        out  (VDP_DAT), a
        inc  hl
        dec  b
        jp   nz, stv_loop
        ret

;----------------------------------------------------------
; UPDATE_HUD - la puntuacion en la tabla de nombres
;----------------------------------------------------------
; Los cinco digitos van en las cinco primeras celdas de la primera
; fila.  El patron de un digito es su propio numero (0 a 9), en
; la primera zona de la tabla de patrones.
;----------------------------------------------------------
UPDATE_HUD:
        ld   a, (game_score+2)
        ld   b, a
        ld   a, (hud_score)
        cp   b
        ret  z
        ld   a, b
        ld   (hud_score), a

        ; copia la puntuacion a un buffer de 5 digitos
        ld   hl, hud_digitos
        ld   b, 5
        ld   a, (game_score+2)
        ld   (hl), a
        inc  hl
        ld   a, (game_score+1)
        ld   (hl), a
        inc  hl
        ld   a, (game_score)
        ld   (hl), a
        inc  hl
        ld   a, 0
        ld   (hl), a
        inc  hl
        ld   (hl), a

        ; y los escribe en la tabla de nombres ($1800)
        ld   a, $00
        out  (VDP_CMD), a
        ld   a, $18 | $40
        out  (VDP_CMD), a
        ld   hl, hud_digitos
        ld   b, 5
uh_loop:
        ld   a, (hl)
        out  (VDP_DAT), a
        inc  hl
        dec  b
        jp   nz, uh_loop
        ret

;----------------------------------------------------------
; SET_GAME_SCREEN - cambia a la pantalla del juego
;----------------------------------------------------------
; El fondo del juego esta en el banco 2 y tiene el mismo layout
; que la pantalla del titulo, asi que solo hay que cambiar el
; banco y reiniciar la carga de la VRAM.
;----------------------------------------------------------
SET_GAME_SCREEN:
        ld   a, 2
        call SETBANK_B
        ld   a, 0
        ld   (job_phase), a
        ld   hl, NAME_BASE
        ld   (job_dst), hl
        ld   hl, ASSET_NAME
        ld   (job_src), hl
        ld   hl, NAME_PAGES
        ld   (job_pages), hl
        ret

;----------------------------------------------------------
; El sonido (PSG)
;----------------------------------------------------------
; El PSG tiene dos puertos: $A0 selecciona el registro y $A1
; recibe el dato.
;----------------------------------------------------------
SOUND_SHOT:
        ld   a, $07
        out  (PSG_REG), a
        ld   a, $3E             ; solo el canal A
        out  (PSG_DAT), a
        ld   a, $00
        out  (PSG_REG), a
        ld   a, 60              ; la frecuencia
        out  (PSG_DAT), a
        ld   a, $01
        out  (PSG_REG), a
        ld   a, 20
        out  (PSG_DAT), a
        ld   a, $08
        out  (PSG_REG), a
        ld   a, 10              ; el volumen
        out  (PSG_DAT), a
        ld   a, 3
        ld   (sound_off), a
        ret

SOUND_EXPLODE:
        ld   a, $07
        out  (PSG_REG), a
        ld   a, $36             ; el canal B con ruido
        out  (PSG_DAT), a
        ld   a, $0D
        out  (PSG_REG), a
        ld   a, 8
        out  (PSG_DAT), a
        ld   a, $08
        out  (PSG_REG), a
        ld   a, 12
        out  (PSG_DAT), a
        ld   a, 6
        ld   (sound_off), a
        ret

;----------------------------------------------------------
; SOUND_UPDATE - apaga el sonido a los pocos frames
;----------------------------------------------------------
SOUND_UPDATE:
        ld   a, (sound_off)
        and  a
        ret  z
        dec  a
        ld   (sound_off), a
        ret  nz
        ; silencia el mixer
        ld   a, $07
        out  (PSG_REG), a
        ld   a, $3F
        out  (PSG_DAT), a
        ret
