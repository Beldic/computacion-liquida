# BCM-WIRE/0.2

## Transporte local de bloques de cómputo-memoria

> Concepto original y autoría: **Jordi Casado Sobrepere | Filosofía Sobreperiana**

BCM/0.2-A introduce la primera circulación efectiva de una generación BCM entre dos procesos. La unidad transmitida es un snapshot `BCM-SNAPSHOT/0.1` completo: código, estado, límites, capacidades e identidad genealógica viajan juntos.

## Alcance

Esta fase usa una conexión TCP sobre IPv4 de loopback. El emisor y el receptor deben ejecutarse en el mismo entorno de red local del sistema operativo, por ejemplo dos terminales dentro de una misma distribución WSL.

El módulo rechaza direcciones como `0.0.0.0` o una IP de la LAN. La restricción es intencionada: todavía no hay autenticación, cifrado ni autorización entre nodos.

## Frame

Cada conexión transporta una petición y una respuesta. Cada mensaje ocupa exactamente un frame:

| Campo | Tamaño | Codificación |
|---|---:|---|
| Longitud | 4 bytes | entero sin signo, big-endian |
| Documento | longitud declarada | JSON canónico BCM en UTF-8 |

Si $P$ representa los bytes del documento, el frame es:

$$
F = \operatorname{uint32be}(|P|) \mathbin{\Vert} P
$$

El límite predeterminado cumple:

$$
0 < |P| \le 8\,388\,608\ \text{bytes}
$$

El receptor comprueba el tamaño antes de reservar y leer el cuerpo completo. Una conexión cerrada prematuramente, un tiempo de espera agotado, una longitud nula o un tamaño superior al límite invalidan la transferencia.

## Representación única

El documento recibido debe coincidir byte por byte con la codificación canónica obtenida después de interpretarlo. No se aceptan variantes equivalentes con espacios adicionales, claves desordenadas, Unicode sin normalizar, claves duplicadas, números de coma flotante o enteros superiores a 4096 bits.

Esta condición hace que cada mensaje admitido tenga una representación UTF-8 única dentro del subconjunto canónico de BCM.

## Petición `snapshot`

```json
{
  "wire_protocol": "BCM-WIRE/0.2",
  "message_type": "snapshot",
  "request_id": "0123456789abcdef0123456789abcdef",
  "snapshot": {
    "snapshot_format": "BCM-SNAPSHOT/0.1",
    "hash_algorithm": "sha256",
    "content_hash": "<hash>",
    "payload": {}
  }
}
```

El ejemplo está indentado y abreviado para facilitar su lectura; el frame real usa la representación compacta canónica.

`request_id` contiene 32 caracteres hexadecimales y correlaciona petición y respuesta. No identifica el contenido ni sustituye a `content_hash`.

## Respuesta `accepted`

```json
{
  "wire_protocol": "BCM-WIRE/0.2",
  "message_type": "accepted",
  "request_id": "0123456789abcdef0123456789abcdef",
  "content_hash": "<hash confirmado>",
  "stored": true
}
```

El emisor exige que `request_id` y `content_hash` coincidan con la transferencia iniciada. `stored` vale `false` cuando el receptor ya poseía exactamente el mismo snapshot.

## Respuesta `rejected`

```json
{
  "wire_protocol": "BCM-WIRE/0.2",
  "message_type": "rejected",
  "request_id": null,
  "code": "invalid-request",
  "detail": "descripción controlada del rechazo"
}
```

`request_id` puede ser `null` si la petición estaba dañada y no fue posible recuperar un identificador válido.

## Algoritmo de recepción

El proceso receptor sigue este orden:

1. acepta una conexión de loopback;
2. lee la cabecera y comprueba el límite;
3. lee exactamente la cantidad declarada de bytes;
4. valida UTF-8 y la codificación JSON canónica;
5. valida el esquema cerrado de `BCM-WIRE/0.2`;
6. reconstruye y verifica el snapshot y su SHA-256;
7. almacena el documento como `<content_hash>.snapshot.json`;
8. responde `accepted` con la identidad comprobada;
9. cierra la conexión sin interpretar el bloque.

El orden es una propiedad de seguridad: ningún contenido se acepta ni persiste antes de comprobar su identidad.

## Almacenamiento dirigido por contenido

Los snapshots se guardan usando su hash completo como nombre. Esto evita derivar rutas de valores controlados como `block.id` y proporciona idempotencia natural.

Si el archivo ya existe, se vuelve a cargar y verificar. Solo se responde `stored: false` cuando representa exactamente el mismo snapshot; una discrepancia bajo la misma identidad se trata como error de integridad.

## Operaciones de consola

Receptor, terminal 1:

```bash
bcm receive --inbox /tmp/bcm-inbox
```

Emisor, terminal 2:

```bash
bcm send examples/suma-yield.snapshot.json
```

Ambos comandos usan de manera predeterminada `127.0.0.1:7337`. `receive` acepta una sola conexión y termina, por lo que aún no constituye un servicio persistente.

## Garantías y límites

BCM/0.2-A garantiza:

- delimitación inequívoca del mensaje;
- límite de tamaño antes de leer el cuerpo;
- representación canónica única;
- detección de alteraciones del snapshot;
- correlación entre petición y respuesta;
- persistencia por identidad e idempotencia;
- ausencia de ejecución automática.

Todavía no garantiza:

- identidad o autorización del proceso emisor;
- confidencialidad frente a observadores del sistema;
- validez semántica de una transición entre generaciones;
- tolerancia a múltiples clientes o funcionamiento continuo;
- transporte entre WSL, Windows, máquinas virtuales o equipos físicos.

Estas propiedades quedan reservadas para las siguientes fases del protocolo.
