#!/usr/bin/python3
#-*- coding:utf-8 -*-

from enum import IntEnum, StrEnum, IntFlag
import string
from .utils import is_imm, get_reg_num

class InstEnum(IntEnum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            # first check name to avoid hex(value) collision with name
            # for example, A = 0xA
            for member in cls:
                if member.name.lower() == str(value).lower():
                    return member

        for member in cls:
            if member.value == value:
                return member
            if member.name.lower() == str(value).lower():
                return member
            if isinstance(value, int):
                if member.name.lower() == str(value).lower():
                    return member
            if isinstance(value, str) and is_imm(value):
                if member.value == int(value ,0):
                    return member
        return None

class InstRegister(InstEnum):
    r0 = 0
    r1 = 1
    r2 = 2
    r3 = 3
    r4 = 4
    r5 = 5
    r6 = 6
    r7 = 7
    r8 = 8
    r9 = 9
    r10 = 10
    r11 = 11
    r12 = 12
    r13 = 13
    r14 = 14
    r15 = 15


class InstDataType(StrEnum):
    u8 = 'u8'
    u16 = 'u16'
    u32 = 'u32'
    u64 = 'u64'
    i8 = 'i8'
    i16 = 'i16'
    i32 = 'i32'
    i64 = 'i64'
    float = 'float'
    double = 'double'

    @classmethod
    def _missing_(cls, value):
        def width_to_datatype(width: int):
            if width == 1:
                return cls.u8
            elif width == 2:
                return cls.u16
            elif width == 4:
                return cls.u32
            elif width == 8:
                return cls.u64
            else:
                return None
        if isinstance(value, str):
            dtype = value.lower()
            if dtype == 'ptr' or '*' in dtype:
                return cls.u64
            if dtype == 'float':
                return cls.float
            if dtype == 'double':
                return cls.double
            if len(dtype) in [2,3] and dtype[0] in ['i', 'u'] and dtype[1:].isnumeric():
                bitwidth = int(dtype[1:])
                if bitwidth % 8 == 0 and bitwidth // 8 in [1,2,4,8]:
                    return width_to_datatype(bitwidth // 8)
        if isinstance(value, int):
            return width_to_datatype(value)
        return None

def InstDataType_to_int(width: InstDataType) -> int:
    if width in [InstDataType.u8, InstDataType.i8]:
        return 1
    elif width in [InstDataType.u16, InstDataType.i16]:
        return 2
    elif width in [InstDataType.u32, InstDataType.i32]:
        return 4
    elif width in [InstDataType.u64, InstDataType.i64]:
        return 8
    elif width == InstDataType.float:
        return 4
    elif width == InstDataType.double:
        return 8

class InstMemBase(InstEnum):
    MAIN = 0
    HEAP = 1
    ALIAS = 2
    ASLR = 3

class InstCondition(InstEnum):
    GT = 1
    GTE = 2
    LT = 3
    LTE = 4
    EQ = 5
    NEQ = 6
    
    def __str__(self):
        for sym in ConditionSymbolMapping:
            if ConditionSymbolMapping[sym] == self.value:
                return sym
        # assert False, f"Invalid condition: {self.value}"
        return str(self.name)


    @classmethod
    def _missing_(cls, value):
        if value in ConditionSymbolMapping:
            return ConditionSymbolMapping[value]
        return super()._missing_(value)


ConditionSymbolMapping: dict =  {
    '>': InstCondition.GT,
    '>=': InstCondition.GTE,
    '<': InstCondition.LT,
    '<=': InstCondition.LTE,
    '==': InstCondition.EQ,
    '!=': InstCondition.NEQ
}


class InstArithmetic(InstEnum):
    ADD = 0
    SUB = 1
    MUL = 2
    LSHIFT = 3
    RSHIFT = 4
    LOGICAL_AND = 5
    LOGICAL_OR = 6
    LOGICAL_NOT = 7
    LOGICAL_XOR = 8
    MOVE = 9

    def __str__(self):
        for sym in ArithmeticSymbolMapping:
            if ArithmeticSymbolMapping[sym] == self.value:
                return sym
        # assert False, f"Invalid condition: {self.value}"
        return str(self.name)


    @classmethod
    def _missing_(cls, value):
        if value in ArithmeticSymbolMapping:
            return ArithmeticSymbolMapping[value]
        return super()._missing_(value)

ArithmeticSymbolMapping: dict = {
    '+': InstArithmetic.ADD,
    '-': InstArithmetic.SUB,
    '*': InstArithmetic.MUL,
    '<<': InstArithmetic.LSHIFT,
    '>>': InstArithmetic.RSHIFT,
    '&': InstArithmetic.LOGICAL_AND,
    '|': InstArithmetic.LOGICAL_OR,
    '~': InstArithmetic.LOGICAL_NOT,
    '^': InstArithmetic.LOGICAL_XOR,
    '=': InstArithmetic.MOVE
}

class InstKeyName(InstEnum):
    A = 0x00000001
    B = 0x00000002
    X = 0x00000004
    Y = 0x00000008
    LSTICK = 0x00000010
    RSTICK = 0x00000020
    L = 0x00000040
    R = 0x00000080
    ZL = 0x00000100
    ZR = 0x00000200
    PLUS = 0x00000400
    MINUS = 0x00000800
    LEFT = 0x00001000
    UP = 0x00002000
    RIGHT = 0x00004000
    DOWN = 0x00008000
    LSTICK_LEFT = 0x00010000
    LSTICK_UP = 0x00020000
    LSTICK_RIGHT = 0x00040000
    LSTICK_DOWN = 0x00080000
    RSTICK_LEFT = 0x00100000
    RSTICK_UP = 0x00200000
    RSTICK_RIGHT = 0x00400000
    RSTICK_DOWN = 0x00800000
    SL = 0x01000000
    SR = 0x02000000

class InstKeyFlag(IntFlag):
    A = 0x00000001
    B = 0x00000002
    X = 0x00000004
    Y = 0x00000008
    LSTICK = 0x00000010
    RSTICK = 0x00000020
    L = 0x00000040
    R = 0x00000080
    ZL = 0x00000100
    ZR = 0x00000200
    PLUS = 0x00000400
    MINUS = 0x00000800
    LEFT = 0x00001000
    UP = 0x00002000
    RIGHT = 0x00004000
    DOWN = 0x00008000
    LSTICK_LEFT = 0x00010000
    LSTICK_UP = 0x00020000
    LSTICK_RIGHT = 0x00040000
    LSTICK_DOWN = 0x00080000
    RSTICK_LEFT = 0x00100000
    RSTICK_UP = 0x00200000
    RSTICK_RIGHT = 0x00400000
    RSTICK_DOWN = 0x00800000
    SL = 0x01000000
    SR = 0x02000000


class InstOffsetType(InstEnum):
    NO_OFFSET = 0
    OFF_REG = 1
    OFF_IMM = 2
    MEMBASE_REG = 3
    MEMBASE_IMM = 4
    MEMBASE_IMM_OFFREG = 5

class InstDebugType(InstEnum):
    MEMBASE_OFF = 0
    MEMBASE_REG = 1
    REG_OFF = 2
    REG_OFFREG = 3
    REG = 4

class InstSaveRestoreRegOp(InstEnum):
    RESTORE = 0
    SAVE = 1
    CLEAR = 2
    REG_ZERO = 2

def dtype_to_width(dtype: str) -> InstDataType:
    dtype = dtype.strip()
    assert dtype[0] in ('i', 'u')
    bit_width = int(dtype[1:])
    assert bit_width in (8, 16, 32, 64)
    width = int(bit_width / 8)
    return InstDataType(width)
