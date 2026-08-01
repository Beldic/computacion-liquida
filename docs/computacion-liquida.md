# Computación Líquida

## Protocolo BCM: bloques de cómputo-memoria

**Título del proyecto:** Computación Líquida  
**Protocolo técnico provisional:** BCM — Bloques de Cómputo-Memoria  
**Versión del documento:** 0.1  
**Estado:** propuesta de arquitectura para investigación y prototipado  
**Lenguaje inicial:** Python 3.12 o posterior  
**Entorno inicial:** GNU/Linux y red local de confianza  
**Concepto original y autoría:** Jordi Casado Sobrepere | Filosofía Sobreperiana

**Material complementario:** infografía conceptual «Protocolo BCM: Bloques de Cómputo-Memoria».

---

## Abstract

**Computación Líquida** presenta un modelo experimental de ejecución distribuida en el que el código, la memoria y la continuación de una operación constituyen una única entidad transmisible: el **Bloque de Cómputo-Memoria** o **BCM**. La propuesta desplaza la identidad del cómputo desde el proceso anfitrión hacia una sucesión de estados operacionales completos. Cada bloque puede ejecutarse durante un quantum limitado, congelarse en una frontera segura entre instrucciones, fragmentarse físicamente y circular entre procesos o equipos de una red local sin perder su unidad lógica.

El sistema se articula mediante una máquina virtual portátil implementada inicialmente en Python, un protocolo de transferencia con propiedad exclusiva, verificación criptográfica, memoria direccionada mediante referencias internas y acceso al sistema operativo regulado por capacidades. El primer prototipo no pretende migrar procesos nativos arbitrarios, sino demostrar que una misma genealogía computacional puede proseguir en distintos intérpretes y producir un resultado equivalente al de una ejecución local. El documento establece el modelo formal, la arquitectura, el conjunto mínimo de instrucciones, las garantías de atomicidad y seguridad, y una hoja de ruta hacia un prototipo funcional en GNU/Linux.

**Palabras clave:** computación distribuida, máquina virtual, migración de estado, memoria portátil, bloques atómicos, redes locales, lógica operacional.

---

## 1. Planteamiento general

Computación Líquida propone una capa de ejecución distribuida en la que el código, la memoria y el punto de continuación de una operación forman una única unidad lógica transmisible: el **Bloque de Cómputo-Memoria** o **BCM**.

Un bloque puede suspenderse en un proceso, transmitirse a otro proceso del mismo ordenador o a otro equipo de la red local, verificarse y continuar allí su ejecución. La máquina física que lo interpreta puede cambiar, pero la continuidad lógica del cómputo se conserva.

La hipótesis central es:

> La unidad primaria del sistema no es el programa aislado ni el proceso anfitrión, sino la sucesión transmisible de estados completos de código-memoria.

El primer prototipo no intentará migrar procesos Linux arbitrarios. Construirá una **máquina virtual BCM** controlada por Python. Los programas escritos para esa máquina virtual podrán detenerse exactamente entre instrucciones, serializar su estado y proseguir en otro intérprete.

---

## 2. Objetivos

### 2.1. Objetivo general

Crear un intérprete y un protocolo que permitan ejecutar, suspender, transmitir y reanudar bloques autocontenidos de código y memoria entre procesos y nodos de una red local.

### 2.2. Objetivos específicos

1. Definir una arquitectura de instrucciones mínima y determinista.
2. Representar de manera transportable el código, la pila, los registros y la memoria.
3. Suspender la ejecución únicamente en fronteras seguras entre instrucciones.
4. Transferir la propiedad lógica de un bloque sin permitir dos ejecuciones simultáneas de la misma generación.
5. Fragmentar físicamente los bloques para su transmisión sin romper su atomicidad lógica.
6. Verificar integridad, versión, compatibilidad y límites antes de ejecutar.
7. Ejecutar el mismo bloque sucesivamente en dos procesos locales y, después, en dos ordenadores.
8. Registrar la genealogía completa de la ejecución: $B_0 \rightarrow B_1 \rightarrow B_2 \rightarrow \cdots \rightarrow B_n$.
9. Preparar una futura integración experimental con recursos de bajo nivel de GNU/Linux.

### 2.3. Fuera del alcance inicial

- Migrar cualquier proceso nativo de Linux sin preparación previa.
- Copiar punteros reales entre espacios de direcciones.
- Transportar directamente descriptores de archivos o sockets entre equipos.
- Ejecutar bytecode Python o contenido recibido mediante `pickle`.
- Ofrecer tolerancia bizantina o consenso distribuido en la versión inicial.
- Exponer nodos BCM directamente a Internet.
- Garantizar inicialmente efectos externos de tipo *exactly once*.

---

## 3. Conceptos fundamentales

### 3.1. Bloque de Cómputo-Memoria

Un bloque se representa conceptualmente como:

$$
B_n = \left\langle H, C, M, K, \Gamma, R, I \right\rangle
$$

| Símbolo | Componente | Contenido |
|---|---|---|
| $H$ | Cabecera | Identidad, versión, generación y procedencia |
| $C$ | Código | Secuencia de instrucciones BCM |
| $M$ | Memoria | Heap o memoria virtual propia del bloque |
| $K$ | Continuación | Contador, registros, pila y estado de llamada |
| $\Gamma$ | Capacidades | Operaciones externas expresamente permitidas |
| $R$ | Recursos | Límites de memoria, tiempo e instrucciones |
| $I$ | Integridad | Hashes, firma y manifiesto de fragmentos |

Código y memoria constituyen una unidad lógica inseparable, aunque su representación física pueda dividirse en fragmentos.

### 3.2. Estado operacional

El estado mínimo del intérprete en el instante $t$ es:

$$
S_t = \left(\mathrm{pc}_t, \rho_t, \sigma_t, M_t, \Gamma_t\right)
$$

Aquí, $\mathrm{pc}_t$ es el contador de programa; $\rho_t$, el conjunto de registros; $\sigma_t$, la pila; $M_t$, la memoria; y $\Gamma_t$, las capacidades disponibles.

Una instrucción $I_t$ produce una transición:

$$
\delta(S_t, I_t) = S_{t+1}
$$

La instrucción es atómica dentro de la máquina virtual. El bloque solo puede suspenderse antes o después de ella, nunca mientras modifica parcialmente el estado.

### 3.3. Quantum

Transmitir un bloque después de cada instrucción sería ineficiente. Cada intérprete ejecutará un presupuesto o **quantum** de $q$ instrucciones:

$$
\operatorname{VM}(B_t, q) \longrightarrow \left(B_{t+1}, e\right)
$$

El símbolo $e$ representa el evento que causa la devolución del control al supervisor.

La ejecución se detendrá cuando suceda alguno de estos eventos:

- agotamiento del quantum;
- instrucción `YIELD`;
- instrucción `HALT`;
- solicitud autorizada al sistema;
- error controlado;
- petición de suspensión del supervisor.

### 3.4. Genealogía

Un bloque no se entiende como un objeto estático, sino como una sucesión de generaciones. La ejecución de $B_n$ produce $B_{n+1}$. Cada generación conserva el identificador de su padre y su propio hash.

Esta decisión permite auditoría, reproducción, depuración y, en fases posteriores, recuperación desde puntos anteriores.

---

## 4. Atomicidad y tamaño

### 4.1. Decisión adoptada

> El bloque BCM tendrá tamaño lógico variable y limitado. Su representación física se dividirá en fragmentos de tamaño fijo.

La atomicidad es una propiedad de identidad, propiedad y confirmación; no una consecuencia del número de bytes.

| Nivel | Tamaño | Función |
|---|---:|---|
| Bloque lógico | Variable, con máximo negociado | Unidad de propiedad y ejecución |
| Página de memoria virtual | Fijo | Gestión interna del estado |
| Fragmento de transporte | Fijo salvo el último | Transmisión y reintentos |
| Trama de red | Determinada por el transporte | Circulación física por la LAN |

### 4.2. Manifiesto

El bloque incluirá un manifiesto con la lista ordenada de fragmentos:

```json
{
  "block_id": "bcm-0042",
  "generation": 7,
  "total_size": 153600,
  "chunk_size": 65536,
  "chunks": [
    {"index": 0, "size": 65536, "hash": "..."},
    {"index": 1, "size": 65536, "hash": "..."},
    {"index": 2, "size": 22528, "hash": "..."}
  ],
  "root_hash": "..."
}
```

El receptor podrá almacenar fragmentos a medida que llegan, pero no podrá ejecutar el bloque hasta verificar todos los hashes y confirmar el `root_hash`.

### 4.3. Valores iniciales propuestos

Los valores deberán ser configurables y negociables:

```text
fragmento de transporte:          64 KiB
bloque máximo del prototipo:      16 MiB
quantum ordinario:                10 000 instrucciones
pila máxima:                      65 536 valores
memoria máxima por bloque:        8 MiB
tiempo de vida de una oferta:     10 segundos
```

Son valores experimentales, no constantes definitivas del protocolo.

---

## 5. Frontera entre la máquina virtual y el sistema operativo

### 5.1. Por qué no se migrará inicialmente un proceso nativo

Un proceso real puede contener:

- direcciones de memoria válidas únicamente en su espacio virtual;
- registros específicos de la arquitectura de CPU;
- hilos y mecanismos de sincronización;
- bibliotecas compartidas y código enlazado dinámicamente;
- archivos abiertos, sockets y otros objetos administrados por el kernel;
- memoria mapeada y dispositivos;
- estados que no pueden serializarse de forma portátil.

Por ello, el prototipo creará su propio entorno de ejecución portátil. La transparencia será real para los programas escritos para BCM, no todavía para cualquier binario nativo.

### 5.2. Funciones del adaptador del sistema operativo

El adaptador de GNU/Linux podrá emplear progresivamente:

- `multiprocessing` para crear trabajadores;
- `mmap` y `multiprocessing.shared_memory` para memoria local;
- `os.memfd_create()` para segmentos residentes en memoria;
- sockets Unix para el control interno de cada equipo;
- señales para solicitar suspensión;
- límites de CPU y memoria;
- afinidad de CPU;
- `/proc` para observación;
- posteriormente, CRIU o `ptrace` como línea experimental independiente.

Los mecanismos de bajo nivel no deberán filtrarse al formato portátil del bloque.

---

## 6. Arquitectura general

Cada ordenador ejecutará un servicio de nodo, provisionalmente denominado `bcmd`.

```text
Aplicación cliente
       │
       ▼
API local del nodo
       │
       ▼
Supervisor ─── Planificador ─── Registro de propiedad
       │
       ├── Intérprete BCM
       ├── Almacén de bloques
       ├── Adaptador del SO
       ├── Descubrimiento LAN
       └── Transporte seguro
```

### 6.1. Componentes

| Componente | Responsabilidad |
|---|---|
| Cliente | Crear un bloque, enviarlo y consultar su resultado |
| Supervisor | Coordinar ejecución, suspensión, propiedad y fallos |
| Intérprete | Ejecutar el ISA BCM de forma determinista |
| Planificador | Elegir nodo y quantum según recursos |
| Registro | Conservar propietario, generación y estado |
| Almacén | Guardar manifiestos y fragmentos verificados |
| Adaptador del SO | Traducir capacidades BCM a operaciones controladas |
| Descubrimiento | Encontrar nodos compatibles en la LAN |
| Transporte | Negociar, fragmentar, transmitir y confirmar |
| Observabilidad | Registrar eventos, tiempos, errores y genealogía |

### 6.2. Capas

1. **Capa BCM:** semántica del bloque y del estado.
2. **Capa VM:** instrucciones, ejecución, memoria y suspensión.
3. **Capa de propiedad:** quién puede ejecutar cada generación.
4. **Capa de transporte:** mensajes y fragmentos.
5. **Capa de nodo:** planificación, almacenamiento y descubrimiento.
6. **Capa del SO:** procesos, memoria compartida y recursos físicos.

---

## 7. Máquina virtual BCM

### 7.1. Conjunto inicial de instrucciones

| Grupo | Instrucciones iniciales |
|---|---|
| Pila | `PUSH`, `POP`, `DUP` |
| Memoria | `LOAD`, `STORE`, `ALLOC` |
| Movimiento | `MOV` |
| Aritmética | `ADD`, `SUB`, `MUL`, `DIV` |
| Comparación | `CMP`, `EQ`, `LT`, `GT` |
| Control | `JMP`, `JZ`, `JNZ`, `CALL`, `RET` |
| Ciclo de vida | `YIELD`, `HALT` |
| Sistema | `SYS` |

El ISA debe empezar pequeño. Cada nueva instrucción aumenta la superficie de errores, la complejidad de validación y las diferencias posibles entre intérpretes.

### 7.2. Representación de instrucciones

Durante el prototipo se usará una representación de datos explícita:

```json
[
  {"op": "PUSH", "args": [2]},
  {"op": "PUSH", "args": [2]},
  {"op": "ADD", "args": []},
  {"op": "STORE", "args": [0]},
  {"op": "YIELD", "args": []},
  {"op": "HALT", "args": []}
]
```

Posteriormente podrá codificarse en formato binario compacto.

### 7.3. Memoria

El primer modelo de memoria será una memoria virtual lineal o un mapa de objetos tipados. Las referencias serán offsets o identificadores, nunca punteros del anfitrión.

```python
state = {
    "pc": 0,
    "registers": {"r0": 0, "r1": 0},
    "stack": [],
    "heap": {"0": {"type": "int", "value": 0}},
}
```

Tipos iniciales permitidos:

- enteros con tamaño definido;
- booleanos;
- bytes;
- cadenas UTF-8 limitadas;
- listas y mapas acotados;
- referencias internas validadas.

Los números de coma flotante requieren reglas expresas si se pretende reproducibilidad entre plataformas.

### 7.4. Capacidades y llamadas al sistema

`SYS` no realizará una llamada nativa directa. Emitirá un evento para el supervisor:

```text
SYS WRITE_RESULT
SYS READ_BLOB
SYS GET_NODE_INFO
SYS SPAWN_BLOCK
```

El bloque solo podrá solicitar operaciones presentes en su lista de capacidades. El supervisor validará parámetros, cuotas y procedencia antes de actuar.

Tiempo, aleatoriedad, red y archivos deberán entrar al cómputo como valores o eventos explícitos. Esto mejora la reproducción y limita los efectos ocultos.

---

## 8. Formato lógico del bloque

```json
{
  "protocol": "BCM/0.1",
  "block": {
    "id": "bcm-0042",
    "generation": 7,
    "parent_hash": "...",
    "owner": "node-a",
    "isa": "BCM-ISA/0.1",
    "code": [],
    "state": {
      "pc": 0,
      "registers": {},
      "stack": [],
      "heap": {}
    },
    "capabilities": [],
    "limits": {
      "max_instructions": 10000,
      "max_memory_bytes": 8388608
    },
    "requirements": {
      "runtime": "BCM-PY/0.1"
    },
    "manifest": {
      "chunks": [],
      "root_hash": "..."
    }
  }
}
```

### 8.1. Identidad

Conviene distinguir:

- `id`: identidad genealógica de la tarea;
- `generation`: número monotónico de versión;
- `parent_hash`: estado del que procede;
- `root_hash`: identidad criptográfica de la generación;
- `owner`: nodo autorizado para ejecutarla.

### 8.2. Serialización

Fases previstas:

1. JSON canónico para depuración inicial.
2. Codificación binaria segura, como CBOR, cuando la semántica se estabilice.
3. Fragmentación y compresión opcional de secciones grandes.
4. Posible direccionamiento por contenido para reutilizar código y páginas no modificadas.

No se utilizará `pickle` con datos procedentes de la red, porque su deserialización puede ejecutar código arbitrario.

---

## 9. Protocolo de red

### 9.1. Transporte inicial

- TCP mediante `asyncio` para el canal fiable de control y datos.
- UDP multicast únicamente para anunciar y descubrir nodos.
- TLS para cifrado y autenticación cuando se abandone el laboratorio local mínimo.
- Tramas con longitud prefijada para delimitar mensajes sobre TCP.
- Hash SHA-256 o equivalente para verificar contenido.

### 9.2. Cabecera de trama

Formato conceptual inicial:

```text
magic          4 bytes   "BCM1"
version        1 byte
message_type   1 byte
flags          2 bytes
request_id    16 bytes
payload_size   8 bytes
payload_hash  32 bytes
payload        N bytes
```

Los tamaños definitivos se fijarán tras experimentar con la primera implementación.

### 9.3. Mensajes

| Mensaje | Función |
|---|---|
| `HELLO` | Presentar nodo, versión y capacidades |
| `NODE_STATUS` | Publicar carga y recursos disponibles |
| `OFFER` | Ofrecer un bloque sin transmitirlo todavía |
| `ACCEPT` | Reservar recursos para recibirlo |
| `REJECT` | Rechazar explicando una causa normalizada |
| `MANIFEST` | Enviar identidad, límites y lista de fragmentos |
| `CHUNK` | Transmitir un fragmento |
| `CHUNK_ACK` | Confirmar un fragmento válido |
| `STORED` | Confirmar que el bloque completo está verificado |
| `COMMIT` | Transferir oficialmente la propiedad |
| `EXECUTE` | Autorizar la continuación |
| `CHECKPOINT` | Publicar una nueva generación suspendida |
| `RESULT` | Entregar resultado o bloque final |
| `ABORT` | Cancelar una operación no confirmada |
| `ERROR` | Comunicar un fallo protocolario o de ejecución |

### 9.4. Secuencia ordinaria

```text
Origen                                  Destino
  │── HELLO / negociación ───────────────▶│
  │── OFFER ─────────────────────────────▶│
  │◀─ ACCEPT ─────────────────────────────│
  │── MANIFEST ──────────────────────────▶│
  │── CHUNK 0..N ────────────────────────▶│
  │◀─ STORED ─────────────────────────────│
  │── COMMIT ────────────────────────────▶│
  │◀─ COMMIT_ACK ─────────────────────────│
  │── EXECUTE ───────────────────────────▶│
  │◀─ CHECKPOINT o RESULT ────────────────│
```

---

## 10. Propiedad y transferencia atómica

### 10.1. Invariante principal

> Para cada par `(id, generation)` debe existir como máximo un propietario con permiso de ejecución.

Pueden existir copias físicas para transmisión o respaldo, pero únicamente la copia asociada al token de propiedad puede ejecutarse.

### 10.2. Estados de ciclo de vida

```text
CREATED
   ↓
FROZEN
   ↓
OFFERED
   ↓
TRANSFERRING
   ↓
VERIFIED
   ↓
COMMITTED
   ↓
RUNNING
   ↓
YIELDED | COMPLETED | FAILED
```

### 10.3. Coordinador inicial

El prototipo utilizará un coordinador dentro de la red local. Registrará:

- bloque y generación;
- propietario actual;
- destino propuesto;
- fase de la transferencia;
- plazo de la operación;
- último checkpoint confirmado.

Esta solución simplifica la exclusión mutua y la recuperación. Una versión posterior podrá investigar leases distribuidos o consenso.

### 10.4. Fallos

- Si falla antes de `STORED`, el origen conserva la propiedad.
- Si falla después de `STORED` pero antes de `COMMIT`, el destino conserva datos sin permiso de ejecución.
- Si falla durante `COMMIT`, el coordinador resuelve el propietario mediante su registro duradero.
- Si falla durante la ejecución, se recupera el último checkpoint confirmado.
- Los efectos externos deberán ser idempotentes o transaccionales para evitar duplicación.

TCP entrega un flujo fiable mientras la conexión existe, pero no resuelve por sí solo la propiedad, los reinicios ni la ejecución exactamente una vez.

---

## 11. Descubrimiento y planificación

### 11.1. Descubrimiento LAN

Cada nodo podrá emitir periódicamente un anuncio mínimo:

```json
{
  "node_id": "node-b",
  "protocol": "BCM/0.1",
  "address": "192.168.1.32",
  "port": 7420,
  "runtime": "BCM-PY/0.1",
  "available_memory": 268435456,
  "load": 0.31
}
```

Los anuncios no deberán contener secretos. Toda información deberá considerarse no confiable hasta autenticar el canal TCP/TLS.

### 11.2. Planificador inicial

La primera política puede ser sencilla:

1. descartar nodos incompatibles;
2. descartar nodos sin memoria suficiente;
3. preferir el nodo local mientras no supere un umbral de carga;
4. seleccionar el nodo remoto con menor carga declarada;
5. evitar devolver inmediatamente un bloque al nodo del que acaba de llegar;
6. limitar el número de saltos mediante `hop_count` y `max_hops`.

Más adelante podrán añadirse afinidad de datos, coste de transferencia, prioridad y especialización de nodos.

---

## 12. Seguridad

Recibir código ejecutable por red equivale a abrir una superficie de ejecución remota. El aislamiento no es opcional.

### 12.1. Reglas mínimas

1. El intérprete solo aceptará opcodes conocidos.
2. Todos los operandos, saltos y referencias se validarán antes de ejecutar.
3. Código y datos se tratarán como estructuras, no como objetos Python ejecutables.
4. No se usará `eval`, `exec` ni `pickle` con contenido remoto.
5. La memoria, la pila y el quantum tendrán límites estrictos.
6. Las llamadas externas pasarán por capacidades.
7. Cada nodo tendrá identidad criptográfica.
8. Los bloques deberán estar firmados o proceder de un nodo autorizado.
9. El prototipo se ejecutará en una red de laboratorio, no expuesto a Internet.
10. Los trabajadores podrán aislarse en procesos con privilegios reducidos.

### 12.2. Validación previa

Antes de aceptar un bloque se comprobará:

- versión del protocolo y del ISA;
- tamaño total y número de fragmentos;
- hashes;
- firma y propietario;
- límites solicitados;
- saltos dentro del código;
- profundidad máxima de estructuras;
- referencias internas válidas;
- capacidades permitidas;
- ausencia de campos desconocidos críticos.

---

## 13. Estructura propuesta del proyecto Python

```text
protocolo-bcm/
├── README.md
├── pyproject.toml
├── src/
│   └── bcm/
│       ├── __init__.py
│       ├── block.py
│       ├── manifest.py
│       ├── state.py
│       ├── isa.py
│       ├── instruction.py
│       ├── vm.py
│       ├── validator.py
│       ├── codec.py
│       ├── framing.py
│       ├── protocol.py
│       ├── transport.py
│       ├── discovery.py
│       ├── ownership.py
│       ├── scheduler.py
│       ├── supervisor.py
│       ├── worker.py
│       ├── node.py
│       ├── os_adapter.py
│       └── cli.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── network/
├── examples/
│   ├── suma.json
│   └── migracion_dos_nodos.py
├── docs/
│   ├── protocolo.md
│   └── isa.md
└── scripts/
    └── run_lab.sh
```

### 13.1. Responsabilidades esenciales

- `block.py`: modelo inmutable de la generación congelada.
- `state.py`: registros, pila, heap y contador.
- `isa.py`: opcodes y especificación de operandos.
- `vm.py`: bucle de ejecución.
- `validator.py`: validación estructural y semántica.
- `codec.py`: serialización canónica.
- `framing.py`: delimitación binaria sobre TCP.
- `ownership.py`: tokens, generaciones y transiciones.
- `supervisor.py`: coordinación de trabajadores.
- `os_adapter.py`: operaciones autorizadas sobre Linux.

---

## 14. Modelos Python preliminares

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VMState:
    pc: int = 0
    registers: dict[str, int] = field(default_factory=dict)
    stack: list[Any] = field(default_factory=list)
    heap: dict[int, Any] = field(default_factory=dict)
    halted: bool = False


@dataclass(slots=True, frozen=True)
class Limits:
    max_instructions: int
    max_memory_bytes: int
    max_stack_items: int


@dataclass(slots=True)
class BCMBlock:
    block_id: str
    generation: int
    parent_hash: str | None
    owner: str
    code: list[dict[str, Any]]
    state: VMState
    capabilities: frozenset[str]
    limits: Limits
```

El modelo cambiará durante el prototipo. La prioridad inicial será hacer explícitas las invariantes, no congelar prematuramente una API.

### 14.1. Bucle conceptual del intérprete

```python
def run_quantum(block: BCMBlock, quantum: int) -> str:
    executed = 0

    while not block.state.halted and executed < quantum:
        instruction = fetch(block.code, block.state.pc)
        validate_instruction(instruction, block)
        event = execute_atomic(instruction, block.state)
        executed += 1

        if event in {"yield", "syscall", "halt", "error"}:
            return event

    return "quantum_expired"
```

`execute_atomic` deberá modificar el estado por completo o no modificarlo. Para operaciones complejas podrá calcular primero el nuevo estado y publicarlo al finalizar.

---

## 15. Plan de implementación

### Fase 0 — Fundamentos y laboratorio

**Resultado:** repositorio ejecutable y decisiones registradas.

1. Crear el proyecto con `src/` y pruebas.
2. Elegir Python 3.12 o posterior.
3. Configurar `venv` y `pyproject.toml`.
4. Definir nombres, versión y vocabulario.
5. Registrar decisiones arquitectónicas breves.
6. Limitar el laboratorio a `localhost`.

### Fase 1 — Máquina virtual local

**Resultado:** un bloque calcula un valor, se suspende y continúa en el mismo intérprete.

1. Implementar `VMState`, `BCMBlock` y `Limits`.
2. Crear los opcodes básicos.
3. Implementar `fetch`, validación y despacho.
4. Añadir `YIELD`, `HALT` y quantum.
5. Ejecutar el programa `2 + 2`.
6. Verificar que el estado solo cambia en fronteras de instrucción.

### Fase 2 — Congelación y serialización

**Resultado:** un bloque suspendido se guarda y se reconstruye sin pérdida.

1. Separar estado mutable de snapshot congelado.
2. Crear una representación JSON canónica.
3. Calcular el hash de cada generación.
4. Validar esquemas, tipos, límites y saltos.
5. Añadir pruebas de ida y vuelta:

   ```text
   bloque → bytes → bloque reconstruido
   ```

6. Comprobar que ambos estados son semánticamente equivalentes.

### Fase 3 — Dos procesos en un ordenador

**Resultado:** el proceso B continúa un bloque suspendido por el proceso A.

1. Crear supervisor y dos trabajadores con `multiprocessing`.
2. Usar pipes o sockets Unix para el control.
3. Congelar el bloque en A.
4. Transferirlo a B.
5. Revocar la ejecución en A.
6. Continuar en B.
7. Devolver el resultado al supervisor.
8. Registrar `B₀ → B₁ → B₂`.

### Fase 4 — Fragmentación física

**Resultado:** un bloque variable se transmite como fragmentos fijos.

1. Crear manifiesto y `root_hash`.
2. Dividir en fragmentos.
3. Verificar cada fragmento.
4. Reordenar fragmentos recibidos fuera de orden.
5. Detectar duplicados y corrupción.
6. Confirmar el bloque únicamente cuando esté completo.

### Fase 5 — Dos equipos en la LAN

**Resultado:** el mismo cómputo continúa en una segunda máquina.

1. Implementar servidor TCP asíncrono.
2. Definir framing con longitud prefijada.
3. Implementar `HELLO`, `OFFER`, `ACCEPT`, `MANIFEST`, `CHUNK` y `STORED`.
4. Añadir `COMMIT` y cambio de propietario.
5. Ejecutar el nodo A y el nodo B.
6. Migrar una generación suspendida.
7. Continuarla en B y devolver el resultado.

### Fase 6 — Descubrimiento y planificación

**Resultado:** el nodo de origen encuentra automáticamente un destino adecuado.

1. Añadir anuncios UDP multicast.
2. Mantener una tabla de nodos con caducidad.
3. Publicar versión, carga y memoria disponible.
4. Implementar el planificador simple.
5. Añadir `max_hops` para evitar circulación infinita.

### Fase 7 — Seguridad y recuperación

**Resultado:** laboratorio autenticado con fallos recuperables.

1. Incorporar TLS.
2. Asignar identidad a cada nodo.
3. Firmar manifiestos.
4. Persistir el registro de propiedad.
5. Implementar expiración y abortos.
6. Recuperar desde el último checkpoint.
7. Aislar trabajadores y reducir privilegios.
8. Realizar pruebas con mensajes malformados.

### Fase 8 — Integración de bajo nivel

**Resultado:** optimizaciones y experimentación específica de Linux.

1. Sustituir copias locales grandes por memoria compartida.
2. Evaluar `memfd_create` y mapeos de solo lectura.
3. Investigar copy-on-write para generaciones.
4. Aplicar límites reales de recursos.
5. Medir coste de serialización, red y reanudación.
6. Mantener CRIU/`ptrace` como proyecto experimental separado.

---

## 16. Primer experimento funcional

### 16.1. Programa

```json
[
  {"op": "PUSH", "args": [2]},
  {"op": "PUSH", "args": [2]},
  {"op": "YIELD", "args": []},
  {"op": "ADD", "args": []},
  {"op": "STORE", "args": [0]},
  {"op": "HALT", "args": []}
]
```

### 16.2. Secuencia esperada

1. El nodo A ejecuta los dos `PUSH`.
2. `YIELD` cierra la generación con pila `[2, 2]`.
3. El supervisor congela y serializa el bloque.
4. El bloque se fragmenta y viaja al nodo B.
5. B verifica, reconstruye y recibe la propiedad.
6. B ejecuta `ADD`, `STORE 0` y `HALT`.
7. La memoria final contiene `heap[0] = 4`.
8. El registro muestra qué instrucciones se ejecutaron en cada nodo.

### 16.3. Prueba conceptual

La demostración será válida si el resultado y la genealogía son idénticos a los de una ejecución completa en un solo intérprete.

---

## 17. Estrategia de pruebas

### 17.1. Pruebas unitarias

- semántica de cada opcode;
- límites de pila y memoria;
- saltos válidos e inválidos;
- canonicalización y hashes;
- fragmentación y reconstrucción;
- transición de estados de propiedad;
- rechazo de capacidades no autorizadas.

### 17.2. Pruebas generativas

- secuencias aleatorias de instrucciones válidas;
- datos serializables de distintos tamaños;
- fragmentos duplicados, ausentes y corruptos;
- ejecución local frente a ejecución migrada;
- invariantes tras cada instrucción.

### 17.3. Pruebas de integración

- dos trabajadores locales;
- caída del origen antes de `COMMIT`;
- caída del destino después de `STORED`;
- desconexión durante un fragmento;
- reanudación desde checkpoint;
- nodo incompatible;
- bloque que excede cuotas.

### 17.4. Pruebas de seguridad

- opcode desconocido;
- salto fuera del programa;
- crecimiento ilimitado de la pila;
- estructura JSON excesivamente profunda;
- hash incorrecto;
- firma incorrecta;
- solicitud de sistema sin capacidad;
- intento de reutilización de una generación ya consumida.

---

## 18. Observabilidad

Cada transición producirá un evento estructurado:

```json
{
  "event": "BLOCK_YIELDED",
  "block_id": "bcm-0042",
  "generation": 7,
  "node_id": "node-b",
  "pc": 18,
  "instructions_executed": 10000,
  "memory_bytes": 18432,
  "timestamp": "..."
}
```

Métricas iniciales:

- instrucciones por segundo;
- tiempo de serialización;
- tiempo de transmisión;
- tamaño del bloque;
- fragmentos reenviados;
- tiempo de verificación;
- número de migraciones;
- memoria usada;
- fallos por tipo;
- longitud de la genealogía.

La traza completa permitirá visualizar el devenir operacional del bloque a través de los nodos.

---

## 19. Criterios de aceptación del prototipo BCM/0.1

El prototipo será funcional cuando cumpla simultáneamente:

- [ ] Ejecuta al menos diez opcodes definidos.
- [ ] Suspende sin estado parcial entre instrucciones.
- [ ] Serializa y reconstruye un bloque completo.
- [ ] Detecta cualquier modificación de un fragmento.
- [ ] Impide ejecutar una generación sin propiedad.
- [ ] Migra un bloque entre dos procesos locales.
- [ ] Migra un bloque entre dos equipos de la LAN.
- [ ] Obtiene el mismo resultado local y distribuido.
- [ ] Conserva la genealogía de generaciones.
- [ ] Rechaza entradas malformadas sin ejecutar código Python.
- [ ] Aplica límites de instrucciones y memoria.
- [ ] Recupera al menos desde el último checkpoint confirmado.

---

## 20. Preguntas abiertas de investigación

1. ¿El código debe repetirse en cada generación o referenciarse por hash?
2. ¿La memoria será lineal, estructurada o híbrida?
3. ¿Qué parte de la historia debe conservarse físicamente?
4. ¿Cuándo compensa migrar frente a continuar localmente?
5. ¿Puede dividirse un bloque en subbloques ejecutables en paralelo sin destruir su unidad lógica?
6. ¿Cómo representar efectos externos dentro de la genealogía?
7. ¿Qué semántica tendrá el fallo: reintento, bifurcación o restauración?
8. ¿La propiedad debe ser centralizada, arrendada o consensuada?
9. ¿Debe el planificador decidir el destino o puede hacerlo el propio bloque dentro de límites?
10. ¿Cómo se relaciona el tiempo físico de los nodos con el orden lógico de las generaciones?
11. ¿Puede considerarse cada generación un hecho y cada transición un acto dentro de una lógica operacional?
12. ¿Qué propiedades emergen si la red completa se concibe como una única superficie de ejecución?

---

## 21. Riesgos principales

| Riesgo | Consecuencia | Mitigación inicial |
|---|---|---|
| Bloques demasiado grandes | La migración cuesta más que la ejecución | Cuotas y planificador sensible al tamaño |
| Doble ejecución | Inconsistencia de estado o efectos duplicados | Propietario único y coordinador |
| Código malicioso | Compromiso del nodo | ISA cerrada, validación y capacidades |
| Diferencias entre plataformas | Resultados no reproducibles | Semántica numérica definida y VM portátil |
| Fallo durante `COMMIT` | Propiedad ambigua | Registro duradero del coordinador |
| Demasiados checkpoints | Sobrecoste de almacenamiento | Intervalos y copy-on-write futuro |
| Memoria no transportable | Imposibilidad de reanudación | Offsets y objetos tipados |
| Efectos externos repetidos | Duplicación de acciones | Operaciones idempotentes o transaccionales |

---

## 22. Hoja de ruta resumida

```text
BCM/0.1  Máquina virtual local
   ↓
BCM/0.2  Serialización y genealogía
   ↓
BCM/0.3  Migración entre procesos
   ↓
BCM/0.4  Fragmentación y protocolo TCP
   ↓
BCM/0.5  Migración entre dos equipos
   ↓
BCM/0.6  Descubrimiento y planificación
   ↓
BCM/0.7  Seguridad y recuperación
   ↓
BCM/0.8  Memoria compartida y optimización Linux
```

---

## 23. Glosario

**BCM:** unidad lógica formada por código, memoria y continuación.  
**Generación:** versión inmutable de un bloque suspendido.  
**Continuación:** información necesaria para proseguir la ejecución.  
**Quantum:** máximo de instrucciones ejecutadas antes de devolver el control.  
**Checkpoint:** generación confirmada desde la que puede reanudarse.  
**Fragmento:** parte física verificable de un bloque transmitido.  
**Manifiesto:** descripción de los fragmentos y de la identidad completa.  
**Propietario:** nodo autorizado para ejecutar una generación.  
**Capacidad:** permiso explícito para solicitar un efecto externo.  
**ISA:** conjunto y semántica de instrucciones de la máquina virtual.  
**Nodo:** equipo que ejecuta el servicio BCM.  
**Supervisor:** componente que coordina ejecución, suspensión y recursos.  
**Devenir computacional:** sucesión ordenada de generaciones y actos de ejecución.

---

## 24. Principio rector

> El bloque puede dividirse físicamente para circular, pero permanece lógicamente unido para existir, ser poseído y ejecutarse.

La red local se convierte así en una capa transparente de continuidad: diferentes procesos y máquinas interpretan sucesivamente una misma genealogía computacional.

---

## 25. Créditos

**Concepto original y autoría:** Jordi Casado Sobrepere | Filosofía Sobreperiana
