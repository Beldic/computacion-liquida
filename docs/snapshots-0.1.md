# BCM-SNAPSHOT/0.1

## Identidad histórica del bloque de cómputo-memoria

> Concepto original y autoría: **Jordi Casado Sobrepere | Filosofía Sobreperiana**

BCM/0.1-B convierte un estado ejecutable y mutable en una generación inmutable identificada por su contenido. La operación se denomina **checkpoint** o congelación.

## Modelo

Sea $C$ la codificación canónica definida por BCM y sea $B_n$ la generación $n$ de un bloque. Su identidad es:

$$
h_n = \operatorname{SHA256}\!\left(C(B_n, h_{n-1})\right)
$$

Para la generación inicial:

$$
h_{-1} = \varnothing
$$

Cada hash cubre el código, el estado, los límites, las capacidades, el propietario, el número de generación y el hash progenitor. El campo `content_hash` queda fuera del material resumido para evitar una definición circular.

## Envoltorio

```json
{
  "snapshot_format": "BCM-SNAPSHOT/0.1",
  "hash_algorithm": "sha256",
  "content_hash": "<64 caracteres hexadecimales>",
  "payload": {
    "protocol": "BCM/0.1",
    "block": {
      "id": "ejemplo",
      "generation": 1,
      "parent_hash": "<hash de la generación 0>",
      "owner": "node-a",
      "code": [],
      "state": {},
      "capabilities": [],
      "limits": {}
    }
  }
}
```

El ejemplo abreviado muestra la forma del documento, no un snapshot ejecutable completo.

## Codificación canónica BCM

La función $C$ aplica estas reglas:

1. codificación UTF-8;
2. normalización Unicode NFC de claves y cadenas;
3. claves de objetos ordenadas lexicográficamente;
4. separadores JSON compactos, sin espacios prescindibles;
5. enteros de hasta 4096 bits, booleanos, cadenas y `null` como únicos valores escalares;
6. prohibición de coma flotante, `NaN` e infinitos;
7. rechazo de claves duplicadas, incluso si solo difieren antes de normalizar Unicode;
8. rechazo de campos desconocidos dentro del esquema del snapshot.

BCM/0.1-B define su propio subconjunto canónico. No afirma todavía conformidad con RFC 8785 ni con otro estándar externo de JSON canónico.

## Invariantes genealógicas

- La generación cero tiene `parent_hash: null`.
- Toda generación $n>0$ declara un `parent_hash` válido.
- Una descendiente directa tiene número $n+1$.
- `parent_hash` coincide exactamente con `content_hash` de la progenitora.
- La identidad `block.id` permanece constante.
- El código, las capacidades y los límites permanecen constantes en BCM/0.1-B.
- El propietario puede cambiar para preparar la futura migración.
- Un snapshot detenido mediante `HALT` no puede generar descendencia.

## Inmutabilidad

`BlockSnapshot` y `FrozenVMState` son dataclasses congeladas. Las colecciones mutables del bloque se convierten en tuplas ordenadas. Modificar después el bloque fuente no cambia el snapshot ni su identidad.

La restauración crea nuevas listas y diccionarios; nunca entrega referencias mutables a la generación congelada.

## Operaciones Python

```python
from bcm.snapshot import BlockSnapshot, create_snapshot, verify_parent

genesis = create_snapshot(block)
genesis.verify()

child = create_snapshot(executed_block, parent=genesis)
verify_parent(child, genesis)

restored_block = child.thaw()
```

## Operaciones de consola

```bash
bcm checkpoint block.json -o generation-0.snapshot.json
bcm verify generation-0.snapshot.json
bcm restore generation-0.snapshot.json -o restored.block.json
```

Para generaciones posteriores se añade `--parent` a `checkpoint` y `verify`.

## Garantías y límites

La verificación demuestra:

- que el contenido coincide con `content_hash`;
- que una descendiente identifica el documento progenitor aportado;
- que se cumplen las invariantes estructurales de la genealogía.

No demuestra todavía:

- quién creó o autorizó el snapshot;
- que la transición de estado resulte realmente de ejecutar el código;
- que el propietario declarado controle legítimamente el bloque;
- que la cadena sea la única historia posible.

Estas propiedades exigirán firmas, una autoridad de propiedad y verificación de transiciones en fases posteriores.
