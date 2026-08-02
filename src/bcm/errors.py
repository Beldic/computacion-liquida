"""Excepciones propias del intérprete BCM."""


class BCMError(Exception):
    """Error base controlado por el entorno BCM."""


class DecodeError(BCMError):
    """El documento no puede convertirse en un bloque BCM."""


class ValidationError(BCMError):
    """El bloque viola la especificación estática del protocolo."""


class ExecutionError(BCMError):
    """La ejecución no puede continuar sin violar la semántica de la VM."""


class StackUnderflowError(ExecutionError):
    """La instrucción requiere más valores de los disponibles en la pila."""


class ResourceLimitError(ExecutionError):
    """La operación excedería un límite declarado por el bloque."""


class CanonicalizationError(BCMError):
    """Un valor no pertenece al subconjunto JSON canónico de BCM."""


class IntegrityError(BCMError):
    """El contenido no coincide con la identidad criptográfica declarada."""


class GenealogyError(BCMError):
    """Dos generaciones no forman una relación genealógica válida."""


class TransportError(BCMError):
    """La transmisión no pudo completarse de forma segura."""


class WireProtocolError(TransportError):
    """Un mensaje no cumple el protocolo de transporte BCM."""


class RemoteRejectedError(TransportError):
    """El proceso receptor rechazó expresamente la transferencia."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"el receptor rechazó el bloque ({code}): {detail}")
