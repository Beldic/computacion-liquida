# Computación Líquida

## Intérprete experimental del Protocolo BCM

Computación Líquida investiga un modelo en el que código, memoria y continuación forman una única entidad transmisible: el **Bloque de Cómputo-Memoria** o **BCM**.

> Concepto original y autoría: **Jordi Casado Sobrepere | Filosofía Sobreperiana**

Este repositorio contiene el tercer hito técnico, **BCM/0.2-A**: dos procesos locales ya pueden transferirse snapshots BCM mediante TCP de loopback. El receptor delimita el mensaje, comprueba su codificación canónica y su identidad SHA-256, lo almacena por contenido y confirma la aceptación sin ejecutarlo automáticamente.

La revisión **0.2.0a2** endurece la máquina virtual tras una auditoría externa reproducible: caer fuera del programa produce ahora un `ExecutionError` controlado y los enteros BCM tienen un máximo portátil de 4096 bits. Las cuotas declaradas por un bloque pueden reducir los techos del protocolo, pero nunca ampliarlos.

La fundamentación completa se encuentra en [docs/computacion-liquida.md](docs/computacion-liquida.md), la semántica ejecutable en [docs/isa-0.1.md](docs/isa-0.1.md), el formato genealógico en [docs/snapshots-0.1.md](docs/snapshots-0.1.md) y el protocolo de transporte en [docs/wire-0.2.md](docs/wire-0.2.md).

## Estado actual

El núcleo implementa:

- bloque compuesto por código, estado, límites y capacidades;
- pila, heap, registros y contador de programa;
- trece instrucciones: `PUSH`, `POP`, `DUP`, `LOAD`, `STORE`, `ADD`, `SUB`, `MUL`, `DIV`, `JMP`, `JZ`, `YIELD` y `HALT`;
- ejecución atómica entre instrucciones;
- quantum configurable;
- techo innegociable de 10.000 instrucciones por quantum;
- enteros limitados a 4096 bits de magnitud;
- resultados aritméticos fuera de cuota rechazados antes de modificar el estado;
- caída fuera del código convertida en `ExecutionError` controlado;
- suspensión mediante `YIELD` y reanudación local;
- validación de instrucciones, saltos, memoria y recursos;
- JSON canónico BCM con UTF-8, Unicode NFC y claves ordenadas;
- rechazo de claves duplicadas, coma flotante y valores no canónicos;
- snapshots inmutables con hashes SHA-256;
- genealogía mediante `generation` y `parent_hash`;
- congelación, verificación y restauración desde la CLI;
- framing TCP con longitud explícita en orden de red;
- transferencia restringida a IPv4 de loopback;
- límite predeterminado de 8 MiB y tiempos de espera finitos;
- mensajes `snapshot`, `accepted` y `rejected` con correlación;
- almacenamiento idempotente dirigido por `content_hash`;
- separación estricta entre recepción y ejecución;
- interfaz de consola;
- pruebas unitarias con la biblioteca estándar.

## Instalación para desarrollo

Se requiere Python 3.12 o posterior.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Primeros comandos

Inspeccionar el bloque de ejemplo:

```bash
bcm inspect examples/suma.json
```

Ejecutar solamente hasta el primer `YIELD`:

```bash
bcm run examples/suma.json
```

Reanudar automáticamente hasta `HALT`:

```bash
bcm run examples/suma.json --until-halt
```

También puede usarse el módulo directamente:

```bash
python -m bcm run examples/suma.json --until-halt
```

El resultado final del ejemplo debe contener:

```json
{
  "heap": {
    "0": 4
  }
}
```

## Crear una genealogía

Congelar el estado inicial como generación cero:

```bash
bcm checkpoint examples/suma.json \
  -o /tmp/suma-genesis.snapshot.json
```

Ejecutar hasta `YIELD` y guardar el bloque mutable resultante:

```bash
bcm run examples/suma.json \
  --output-block /tmp/suma-yield.block.json
```

Crear la generación uno enlazada con su progenitora:

```bash
bcm checkpoint /tmp/suma-yield.block.json \
  --parent /tmp/suma-genesis.snapshot.json \
  -o /tmp/suma-yield.snapshot.json
```

Verificar contenido y filiación:

```bash
bcm verify /tmp/suma-yield.snapshot.json \
  --parent /tmp/suma-genesis.snapshot.json
```

Restaurar el bloque para continuar su ejecución:

```bash
bcm restore /tmp/suma-yield.snapshot.json \
  -o /tmp/suma-restored.block.json
```

Los archivos `suma-genesis.snapshot.json`, `suma-yield.snapshot.json` y `suma-final.snapshot.json` incluidos en `examples/` forman una genealogía completa y verificable.

## Transferir entre dos procesos

En una primera terminal WSL, iniciar un receptor para una única transferencia:

```bash
mkdir -p /tmp/bcm-inbox
bcm receive --inbox /tmp/bcm-inbox
```

En una segunda terminal WSL, enviar un snapshot:

```bash
bcm send examples/suma-yield.snapshot.json
```

El receptor valida el frame, el esquema y el hash antes de escribir un archivo con esta forma:

```text
/tmp/bcm-inbox/<content_hash>.snapshot.json
```

Enviar de nuevo el mismo snapshot es una operación idempotente: se acepta, pero la respuesta contiene `"stored": false` porque el contenido ya existe.

El receptor termina después de una conexión y nunca ejecuta el bloque. Para interpretarlo hay que restaurarlo expresamente:

```bash
bcm restore /tmp/bcm-inbox/<content_hash>.snapshot.json \
  -o /tmp/bcm-restored.json
bcm run /tmp/bcm-restored.json --until-halt
```

## Pruebas

Después de la instalación editable:

```bash
python -m unittest discover -s tests -v
```

Sin instalar el paquete:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Estructura

```text
computacion-liquida/
├── src/bcm/          Núcleo del intérprete
├── tests/            Pruebas unitarias
├── examples/         Bloques BCM ejecutables
└── docs/             Fundamentos conceptuales
```

## Frontera de seguridad

El intérprete nunca usa `eval`, `exec` ni `pickle` con el documento BCM. El código recibido se representa exclusivamente mediante un conjunto cerrado de opcodes y operandos validados. Los límites del bloque solo pueden restringir los techos de recursos fijados por BCM, no elevarlos.

BCM/0.2-A es un prototipo de laboratorio. SHA-256 detecta alteraciones y proporciona identidad por contenido, pero no autentica al emisor, cifra el canal ni demuestra que una transición haya sido ejecutada legítimamente. Por ello el código obliga a usar loopback IPv4 y no debe exponerse todavía a una LAN, a redes no confiables ni a tareas críticas.

## Próximos hitos

1. **BCM/0.2-B:** receptor persistente y registro local de genealogías.
2. **BCM/0.3:** fragmentación física de bloques variables.
3. **BCM/0.4:** comunicación entre dos equipos de una LAN.
4. **BCM/0.5:** firmas, capacidades y autenticación entre nodos.

## Licencia

Pendiente de decisión. La ausencia de una licencia explícita no concede permisos de copia, modificación o redistribución.
