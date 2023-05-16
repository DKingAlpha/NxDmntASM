#!/usr/bin/python3
#-*- coding:utf-8 -*-

from enum import IntEnum, IntFlag
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

def dtype_to_width(dtype: str) -> InstWidth:
    dtype = dtype.strip()
    assert dtype[0] in ('i', 'u')
    bit_width = int(dtype[1:])
    assert bit_width in (8, 16, 32, 64)
    width = int(bit_width / 8)
    return InstWidth(width)


def get_bracket_elems(s: str, merge_offset: bool = True) -> list[int|InstMemBase|tuple[int,bool]]:
    """
    Returns:
        list[object]: list of elements in the bracket.
            tuple[int,bool]: (reg, ++)
            int: imm
            InstMemBase: base
    """
    assert s.lower() == s   # must be lower case

    s = s.strip(' []').replace(' ', '')
    if not s:
        return []
    parts = s.split('+')
    # merge ['x', '', ''] to ['x++']
    if len(parts) >= 3:
        for i in range(0, len(parts)-2):
            if parts[i] and not parts[i+1] and not parts[i+2]:
                parts[i] += '++'
                parts[i+1] = parts[i+2] = None
    parts = [p for p in parts if p is not None]
    if '' in parts:
        # why is there still '+' unmerged?
        raise SyntaxError(f'illegal address expression {s}')
    result = []
    offset = 0
    has_offset = False
    for p in parts:
        if p.startswith('r'):
            self_inc = p.endswith('++')
            p = p.rstrip('+')   # we have done the check above, so it's safe to blind rstrip '+
            reg_num = get_reg_num(p)
            if reg_num < 0:
                raise SyntaxError(f'illegal register r{p}')
            result.append((reg_num, self_inc))
        elif is_imm(p):
            if merge_offset:
                has_offset = True
                offset += int(p, 0)
            else:
                result.append(int(p, 0))
        elif p in ['main', 'heap', 'alias', 'aslr']:
            result.append(InstMemBase(p))
        else:
            raise SyntaxError(f'illegal `{p}` in address expression {s}')
    if merge_offset and has_offset:
        result.append(offset)
    return result
