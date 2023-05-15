#!/usr/bin/python3
#-*- coding:utf-8 -*-

from enum import IntEnum, IntFlag
import string

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
            if isinstance(value, str) and set(value.lstrip('0xX')).issubset(string.hexdigits):
                if member.value == int(value ,0):
                    return member
        return None

class InstWidth(InstEnum):
    B = 1
    H = 2
    W = 4
    X = 8

    def __str__(self):
        if self == InstWidth.B:
            return 'u8'
        elif self == InstWidth.H:
            return 'u16'
        elif self == InstWidth.W:
            return 'u32'
        elif self == InstWidth.X:
            return 'u64'
        else:
            raise ValueError('Invalid width')

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            dtype = value.lower()
            if dtype == 'ptr' or '*' in dtype:
                return cls.X
            if len(dtype) in [2,3] and dtype[0] in ['i', 'u'] and dtype[1:].isnumeric():
                bitwidth = int(dtype[1:])
                if bitwidth % 8 == 0 and bitwidth // 8 in [1,2,4,8]:
                    return cls(bitwidth // 8)
        return None

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

def int_to_dtype_hexstr(num: int, dtype: str, short_hex: bool = False, truncate: bool = False) -> str:
    dtype = dtype.strip()
    assert dtype[0] in ('i', 'u')
    bit_width = int(dtype[1:])
    assert bit_width in (8, 16, 32, 64)
    if truncate:
        if dtype[0] == 'i':
            min_signed_value = -(1 << (bit_width - 1))
            max_signed_value = (1 << (bit_width - 1)) - 1
            if not (min_signed_value <= num <= max_signed_value):
                orig_num = num
                num = num & ((1 << bit_width) - 1)
                raise OverflowError(f'Number {orig_num:#x} does not fit in {dtype}')
        else:
            max_unsigned_value = (1 << (bit_width)) - 1
            if not (0 <= num <= max_unsigned_value):
                orig_num = num
                num = num & ((1 << bit_width) - 1)
                raise OverflowError(f'Number {orig_num:#x} does not fit in {dtype}')
    dtype_mask = (1 << (bit_width)) - 1
    hex_format = '#x' if short_hex else '#0' + str(int(bit_width / 8) * 2 + 2) + 'x'
    return f'{num & dtype_mask:{hex_format}}'

def hexstr_to_dtype_int(hexstr: str, dtype: str) -> int:
    if len(hexstr) == 0:
        return 0
    assert hexstr[0] != '-'
    assert set(hexstr.lstrip('0xX')).issubset(string.hexdigits)
    dtype = dtype.strip()
    assert dtype[0] in ('i', 'u')
    bit_width = int(dtype[1:])
    assert bit_width in (8, 16, 32, 64)
    dtype_mask = (1 << (bit_width)) - 1
    # check if the number is in range
    raw_num = int(hexstr, 0)
    max_unsigned_value = (1 << (bit_width)) - 1
    assert 0 <= raw_num <= max_unsigned_value
    # convert to signed if needed
    comp_num = int(hexstr, 0) & dtype_mask
    if dtype[0] == 'i':
        max_signed_value = (1 << (bit_width - 1)) - 1
        if comp_num > max_signed_value:
            comp_num -= (1 << bit_width)
    return comp_num


def dtype_to_width(dtype: str) -> InstWidth:
    dtype = dtype.strip()
    assert dtype[0] in ('i', 'u')
    bit_width = int(dtype[1:])
    assert bit_width in (8, 16, 32, 64)
    width = int(bit_width / 8)
    return InstWidth(width)
