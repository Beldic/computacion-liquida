# BCM-ISA/0.1-A

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

- enteros de precisión arbitraria;
- booleanos;
- cadenas Unicode;
- `null`, representado como `None` dentro del intérprete.

Las operaciones aritméticas solo aceptan enteros y rechazan booleanos. Las direcciones y los destinos de salto son enteros no negativos.

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

## Determinismo inicial

Para el mismo bloque válido y el mismo quantum, un intérprete conforme debe producir el mismo estado y el mismo evento. Esta garantía todavía excluye llamadas al sistema, concurrencia, tiempo, aleatoriedad y coma flotante.
