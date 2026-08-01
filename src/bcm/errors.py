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

