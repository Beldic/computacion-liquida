# Computación Líquida

## Intérprete experimental del Protocolo BCM

Computación Líquida investiga un modelo en el que código, memoria y continuación forman una única entidad transmisible: el **Bloque de Cómputo-Memoria** o **BCM**.

> Concepto original y autoría: **Jordi Casado Sobrepere | Filosofía Sobreperiana**

Este repositorio contiene el primer hito técnico, **BCM/0.1-A**: una máquina virtual local, determinista y sin dependencias externas de ejecución. Todavía no transmite bloques entre procesos ni equipos; establece la semántica mínima que hará posible esa migración.

La fundamentación completa se encuentra en [docs/computacion-liquida.md](docs/computacion-liquida.md) y la semántica ejecutable del primer conjunto de instrucciones, en [docs/isa-0.1.md](docs/isa-0.1.md).

## Estado actual

El núcleo implementa:

- bloque compuesto por código, estado, límites y capacidades;
- pila, heap, registros y contador de programa;
- trece instrucciones: `PUSH`, `POP`, `DUP`, `LOAD`, `STORE`, `ADD`, `SUB`, `MUL`, `DIV`, `JMP`, `JZ`, `YIELD` y `HALT`;
- ejecución atómica entre instrucciones;
- quantum configurable;
- suspensión mediante `YIELD` y reanudación local;
- validación de instrucciones, saltos, memoria y recursos;
- carga y salida documental en JSON;
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

BCM/0.1-A es un prototipo de laboratorio. No debe exponerse todavía a redes no confiables ni emplearse para ejecutar tareas críticas.

## Próximos hitos

1. **BCM/0.1-B:** serialización canónica, hashes y snapshots inmutables.
2. **BCM/0.2:** transferencia entre dos procesos locales.
3. **BCM/0.3:** fragmentación física de bloques variables.
4. **BCM/0.4:** comunicación entre dos equipos de una LAN.

## Licencia

Pendiente de decisión. La ausencia de una licencia explícita no concede permisos de copia, modificación o redistribución.
