# Computación Líquida

## Intérprete experimental del Protocolo BCM

Computación Líquida investiga un modelo en el que código, memoria y continuación forman una única entidad transmisible: el **Bloque de Cómputo-Memoria** o **BCM**.

> Concepto original y autoría: **Jordi Casado Sobrepere | Filosofía Sobreperiana**

Este repositorio contiene el segundo hito técnico, **BCM/0.1-B**: una máquina virtual local y determinista cuyos estados pueden congelarse como snapshots inmutables, canónicos y enlazados mediante SHA-256. Todavía no transmite bloques entre procesos ni equipos; establece la identidad histórica que hará verificable esa migración.

La fundamentación completa se encuentra en [docs/computacion-liquida.md](docs/computacion-liquida.md), la semántica ejecutable del conjunto de instrucciones en [docs/isa-0.1.md](docs/isa-0.1.md) y el formato genealógico en [docs/snapshots-0.1.md](docs/snapshots-0.1.md).

## Estado actual

El núcleo implementa:

- bloque compuesto por código, estado, límites y capacidades;
- pila, heap, registros y contador de programa;
- trece instrucciones: `PUSH`, `POP`, `DUP`, `LOAD`, `STORE`, `ADD`, `SUB`, `MUL`, `DIV`, `JMP`, `JZ`, `YIELD` y `HALT`;
- ejecución atómica entre instrucciones;
- quantum configurable;
- suspensión mediante `YIELD` y reanudación local;
- validación de instrucciones, saltos, memoria y recursos;
- JSON canónico BCM con UTF-8, Unicode NFC y claves ordenadas;
- rechazo de claves duplicadas, coma flotante y valores no canónicos;
- snapshots inmutables con hashes SHA-256;
- genealogía mediante `generation` y `parent_hash`;
- congelación, verificación y restauración desde la CLI;
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

El intérprete nunca usa `eval`, `exec` ni `pickle` con el documento BCM. El código recibido se representa exclusivamente mediante un conjunto cerrado de opcodes y operandos validados.

BCM/0.1-B es un prototipo de laboratorio. SHA-256 detecta alteraciones y proporciona identidad por contenido, pero todavía no autentica al autor ni demuestra que una transición haya sido ejecutada legítimamente. No debe exponerse a redes no confiables ni emplearse para tareas críticas.

## Próximos hitos

1. **BCM/0.2:** transferencia entre dos procesos locales.
2. **BCM/0.3:** fragmentación física de bloques variables.
3. **BCM/0.4:** comunicación entre dos equipos de una LAN.
4. **BCM/0.5:** firmas, capacidades y autenticación entre nodos.

## Licencia

Pendiente de decisión. La ausencia de una licencia explícita no concede permisos de copia, modificación o redistribución.
