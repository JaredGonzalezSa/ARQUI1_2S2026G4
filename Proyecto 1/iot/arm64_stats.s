.global _start

// ============================================================
// REGISTROS PRINCIPALES
//
// x23 = número actual
// x24 = suma
// x25 = cantidad
// x26 = máximo
// x27 = mínimo
// x28 = promedio
// ============================================================

.section .data

input_name:
    .asciz "datos.txt"

output_name:
    .asciz "resultado.txt"

label_max:
    .ascii "MÁX="
.equ len_max, . - label_max

label_min:
    .ascii "MIN="
.equ len_min, . - label_min

label_avg:
    .ascii "AVG="
.equ len_avg, . - label_avg

label_count:
    .ascii "COUNT="
.equ len_count, . - label_count

newline:
    .ascii "\n"


.section .bss

buffer:
    .skip 4096

num_buffer:
    .skip 32


.section .text

_start:

    // ========================================================
    // 1. ABRIR datos.txt
    // ========================================================

    mov x0, #-100
    adr x1, input_name
    mov x2, #0
    mov x3, #0
    mov x8, #56
    svc #0

    cmp x0, #0
    b.lt error

    mov x19, x0


    // ========================================================
    // 2. LEER datos.txt
    // ========================================================

    mov x0, x19
    adr x1, buffer
    mov x2, #4096
    mov x8, #63
    svc #0

    cmp x0, #0
    b.le error

    mov x20, x0


    // Cerrar archivo de entrada
    mov x0, x19
    mov x8, #57
    svc #0


    // ========================================================
    // 3. PREPARAR VARIABLES
    // ========================================================

    adr x21, buffer
    add x22, x21, x20

    mov x23, #0      // número actual
    mov x24, #0      // suma
    mov x25, #0      // cantidad
    mov x26, #0      // máximo
    mov x27, #0      // mínimo

    mov x14, #0      // indica si se está formando un número


// ============================================================
// 4. RECORRER datos.txt
// ============================================================

parse_loop:

    // Si llegamos al final sin encontrar $
    cmp x21, x22
    b.hs error

    // Leer un carácter
    ldrb w9, [x21], #1


    // ¿Es $?
    cmp w9, #'$'
    b.eq finish_data


    // ¿Es salto de línea?
    cmp w9, #10
    b.eq end_number


    // ¿Es un dígito?
    cmp w9, #'0'
    b.lt parse_loop

    cmp w9, #'9'
    b.gt parse_loop


    // ASCII -> número
    sub w9, w9, #'0'


    // número = número * 10 + dígito
    mov x10, #10
    madd x23, x23, x10, x9

    mov x14, #1

    b parse_loop


// ============================================================
// 5. TERMINÓ UN NÚMERO
// ============================================================

end_number:

    bl save_number

    b parse_loop


// ============================================================
// 6. SE ENCONTRÓ $
// ============================================================

finish_data:

    // Por si el último número está pegado al $
    bl save_number

    // No debe estar vacío
    cbz x25, error


    // promedio = suma / cantidad
    // División entera -> resultado truncado
    udiv x28, x24, x25


    // ========================================================
    // 7. CREAR resultado.txt
    // ========================================================

    mov x0, #-100
    adr x1, output_name

    // O_WRONLY | O_CREAT | O_TRUNC
    mov x2, #577

    // permisos 0644
    mov x3, #420

    mov x8, #56
    svc #0

    cmp x0, #0
    b.lt error

    mov x19, x0


    // ========================================================
    // MÁX=
    // ========================================================

    mov x0, x19
    adr x1, label_max
    mov x2, #len_max
    mov x8, #64
    svc #0

    mov x0, x19
    mov x1, x26
    bl write_number

    bl write_newline


    // ========================================================
    // MIN=
    // ========================================================

    mov x0, x19
    adr x1, label_min
    mov x2, #len_min
    mov x8, #64
    svc #0

    mov x0, x19
    mov x1, x27
    bl write_number

    bl write_newline


    // ========================================================
    // AVG=
    // ========================================================

    mov x0, x19
    adr x1, label_avg
    mov x2, #len_avg
    mov x8, #64
    svc #0

    mov x0, x19
    mov x1, x28
    bl write_number

    bl write_newline


    // ========================================================
    // COUNT=
    // ========================================================

    mov x0, x19
    adr x1, label_count
    mov x2, #len_count
    mov x8, #64
    svc #0

    mov x0, x19
    mov x1, x25
    bl write_number

    bl write_newline


    // Cerrar resultado.txt
    mov x0, x19
    mov x8, #57
    svc #0


    // Terminar correctamente
    mov x0, #0
    mov x8, #93
    svc #0


// ============================================================
// save_number
//
// Actualiza:
// suma, cantidad, máximo y mínimo
// ============================================================

save_number:

    // Si no había número, regresar
    cbz x14, save_done


    // Si es el primer número:
    // MAX = número
    // MIN = número
    cbnz x25, update_stats

    mov x26, x23
    mov x27, x23

    b add_stats


update_stats:

    // Actualizar máximo
    cmp x23, x26
    b.le check_min

    mov x26, x23


check_min:

    // Actualizar mínimo
    cmp x23, x27
    b.ge add_stats

    mov x27, x23


add_stats:

    // suma += número
    add x24, x24, x23

    // cantidad++
    add x25, x25, #1

    // Reiniciar número actual
    mov x23, #0
    mov x14, #0


save_done:

    ret


// ============================================================
// write_number
//
// Convierte un número entero positivo a texto.
//
// Entrada:
// x0 = archivo
// x1 = número
// ============================================================

write_number:

    mov x9, x0

    adr x10, num_buffer
    add x10, x10, #32


    // Caso especial: número = 0
    cbnz x1, convert_digits

    sub x10, x10, #1

    mov w11, #'0'
    strb w11, [x10]

    b emit_number


convert_digits:

    mov x12, #10


digit_loop:

    // cociente = número / 10
    udiv x13, x1, x12

    // residuo = número % 10
    msub x14, x13, x12, x1

    // convertir residuo a ASCII
    add w14, w14, #'0'

    sub x10, x10, #1
    strb w14, [x10]

    // seguir con el cociente
    mov x1, x13

    cbnz x1, digit_loop


emit_number:

    adr x11, num_buffer
    add x11, x11, #32

    // longitud
    sub x2, x11, x10

    mov x0, x9
    mov x1, x10
    mov x8, #64
    svc #0

    ret


// ============================================================
// Escribir salto de línea
// ============================================================

write_newline:

    mov x0, x19
    adr x1, newline
    mov x2, #1
    mov x8, #64
    svc #0

    ret


// ============================================================
// Error genérico
// ============================================================

error:

    mov x0, #1
    mov x8, #93
    svc #0
