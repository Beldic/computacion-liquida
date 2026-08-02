# BCM-ISA/0.1-A — revisión 2

## Semántica mínima del intérprete local

Esta versión define una máquina de pila determinista. Cada instrucción se ejecuta por completo o no modifica el estado. Una instrucción que falla no avanza el contador de programa, no consume operandos y no publica resultados parciales.

## Estado

El estado local se representa como:

$$
S_t = \left(\mathrm{pc}_t, \rho_t, \sigma_t, M_t, \Gamma_t\right)
$$

- $\mathrm{pc}_t$: contador de programa.
- $\rho_t$: registros reservados para futuras extensiones.
- $\sigma_t$: pila de valores.
- $M_t$: heap direccionado mediante enteros no negativos.
- $\Gamma_t$: capacidades externas; todavía no hay opcodes de sistema.

## Valores

BCM/0.1-A admite valores JSON escalares:

- enteros con magnitud máxima de 4096 bits;
- booleanos;
- cadenas Unicode;
- `null`, representado como `None` dentro del intérprete.

Las operaciones aritméticas solo aceptan enteros y rechazan booleanos. Las direcciones y los destinos de salto son enteros no negativos.

Para un entero $x$, se define:

$$
\operatorname{bits}(x) =
\begin{cases}
0, & x = 0 \\
\left\lfloor \log_2 |x| \right\rfloor + 1, & x \ne 0
\end{cases}
$$

Todo entero BCM debe cumplir:

$$
\operatorname{bits}(x) \le 4096
$$

La restricción se aplica a operandos, pila, heap, registros, direcciones y resultados. Si una operación aritmética produciría un valor mayor, lanza `ResourceLimitError` antes de modificar la pila o avanzar `pc`.

## Instrucciones

En la notación de pila, el elemento situado más a la derecha es la cima.

| Instrucción | Transformación principal | Observaciones |
|---|---|---|
| `PUSH x` | $\sigma \mapsto \sigma \mathbin{+} [x]$ | Añade un valor escalar. |
| `POP` | $[...,x] \mapsto [...]$ | Falla si la pila está vacía. |
| `DUP` | $[...,x] \mapsto [...,x,x]$ | Respeta el límite de pila. |
| `LOAD a` | $\sigma \mapsto \sigma \mathbin{+} [M[a]]$ | Falla si la celda no existe. |
| `STORE a` | $[...,x],M \mapsto [...],M[a:=x]$ | Crea o sustituye una celda. |
| `ADD` | $[...,a,b] \mapsto [...,a+b]$ | Solo enteros. |
| `SUB` | $[...,a,b] \mapsto [...,a-b]$ | El orden es izquierda menos derecha. |
| `MUL` | $[...,a,b] \mapsto [...,a\cdot b]$ | Solo enteros. |
| `DIV` | $[...,a,b] \mapsto [...,a\mathbin{//}b]$ | División entera de suelo; $b\neq0$. |
| `JMP p` | $\mathrm{pc} \mapsto p$ | El destino debe pertenecer al programa. |
| `JZ p` | $[...,c] \mapsto [...]$ | Salta a $p$ si $c=0$; en otro caso continúa. |
| `YIELD` | devuelve el control | Avanza `pc` y conserva la continuación. |
| `HALT` | detiene el bloque | Avanza `pc` y marca el estado como finalizado. |

## Frontera del programa

La ISA no exige que la última instrucción física sea `HALT`, porque admite programas cíclicos mediante saltos. Sin embargo, un bloque activo siempre debe apuntar a una instrucción existente. Si la ejecución secuencial deja `pc` fuera del intervalo $[0, |C|)$, la VM lanza `ExecutionError`; nunca propaga `IndexError` del anfitrión.

## Quantum

El intérprete ejecuta como máximo $q$ instrucciones en cada ciclo:

$$
\operatorname{VM}(B_t,q) \longrightarrow \left(B_{t+1},e\right)
$$

El evento $e$ puede ser:

- `yielded`;
- `halted`;
- `quantum_expired`.

`YIELD` y `HALT` consumen una instrucción del quantum. Una ejecución que termina por error no consume la instrucción fallida.

El techo del protocolo es de 10.000 instrucciones por quantum. Un bloque puede declarar un límite menor, pero no elevarlo. Esta cuota limita el número de pasos; el máximo de 4096 bits limita adicionalmente el coste de cada operación entera.

## Techos del protocolo

| Recurso | Máximo BCM |
|---|---:|
| Instrucciones por quantum | 10.000 |
| Elementos de pila | 65.536 |
| Celdas de heap | 65.536 |
| Registros | 64 |
| Magnitud de un entero | 4096 bits |

Los campos `limits` de un bloque son restricciones solicitadas, no permisos para superar estos valores.

## Determinismo inicial

Para el mismo bloque válido y el mismo quantum, un intérprete conforme debe producir el mismo estado y el mismo evento. Toda implementación debe representar exactamente los enteros permitidos o rechazar el bloque como incompatible antes de ejecutarlo; no puede envolver silenciosamente a 32 o 64 bits. Esta garantía todavía excluye llamadas al sistema, concurrencia, tiempo, aleatoriedad y coma flotante.
