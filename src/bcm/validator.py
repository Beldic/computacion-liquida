"""Validación estática y de estado para bloques BCM."""

from .errors import ValidationError
from .isa import ADDRESS_OPCODES, ARITY, JUMP_OPCODES, Opcode
from .model import BCMBlock, Instruction, is_vm_value


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def validate_instruction(instruction: Instruction, code_size: int) -> None:
    if not isinstance(instruction, Instruction):
        raise ValidationError("el programa contiene una entrada que no es Instruction")
    if not isinstance(instruction.opcode, Opcode):
        raise ValidationError("la instrucción contiene un opcode no tipado")

    expected_arity = ARITY[instruction.opcode]
    if len(instruction.args) != expected_arity:
        raise ValidationError(
            f"{instruction.opcode.value} espera {expected_arity} operandos; "
            f"recibió {len(instruction.args)}"
        )

    if instruction.opcode is Opcode.PUSH:
        if not is_vm_value(instruction.args[0]):
            raise ValidationError("PUSH contiene un valor no admitido")
        return

    if instruction.opcode in ADDRESS_OPCODES:
        address = instruction.args[0]
        if not _is_non_negative_int(address):
            raise ValidationError(
                f"{instruction.opcode.value} requiere una dirección no negativa"
            )
        return

    if instruction.opcode in JUMP_OPCODES:
        target = instruction.args[0]
        if not _is_non_negative_int(target) or target >= code_size:
            raise ValidationError(
                f"{instruction.opcode.value} apunta fuera del programa: {target!r}"
            )


def validate_block(block: BCMBlock) -> None:
    if not isinstance(block.block_id, str) or not block.block_id.strip():
        raise ValidationError("block_id debe ser una cadena no vacía")
    if type(block.generation) is not int or block.generation < 0:
        raise ValidationError("generation debe ser un entero no negativo")
    if not isinstance(block.owner, str) or not block.owner.strip():
        raise ValidationError("owner debe ser una cadena no vacía")
    if not all(isinstance(capability, str) and capability for capability in block.capabilities):
        raise ValidationError("capabilities contiene una entrada no válida")
    if not block.code:
        raise ValidationError("el bloque debe contener al menos una instrucción")

    for instruction in block.code:
        validate_instruction(instruction, len(block.code))

    state = block.state
    limits = block.limits

    limit_values = {
        "max_instructions_per_quantum": limits.max_instructions_per_quantum,
        "max_stack_items": limits.max_stack_items,
        "max_heap_cells": limits.max_heap_cells,
        "max_registers": limits.max_registers,
    }
    for name, value in limit_values.items():
        if type(value) is not int or value <= 0:
            raise ValidationError(f"{name} debe ser un entero positivo")

    if type(state.executed_total) is not int or state.executed_total < 0:
        raise ValidationError("executed_total debe ser un entero no negativo")

    if state.halted:
        if state.pc > len(block.code):
            raise ValidationError("el contador detenido está fuera del programa")
    elif state.pc >= len(block.code):
        raise ValidationError("el contador de un bloque activo debe apuntar al programa")

    if len(state.stack) > limits.max_stack_items:
        raise ValidationError("la pila inicial excede max_stack_items")
    if len(state.heap) > limits.max_heap_cells:
        raise ValidationError("el heap inicial excede max_heap_cells")
    if len(state.registers) > limits.max_registers:
        raise ValidationError("los registros iniciales exceden max_registers")

    if not all(is_vm_value(value) for value in state.stack):
        raise ValidationError("la pila contiene un valor no admitido")
    if not all(
        _is_non_negative_int(address) and is_vm_value(value)
        for address, value in state.heap.items()
    ):
        raise ValidationError("el heap contiene una celda no válida")
    if not all(
        isinstance(name, str) and name and is_vm_value(value)
        for name, value in state.registers.items()
    ):
        raise ValidationError("los registros contienen una entrada no válida")
