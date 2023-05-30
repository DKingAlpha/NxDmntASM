#!/usr/bin/python3
# -*- coding:utf-8 -*-

from __future__ import annotations
import re


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
                raise OverflowError(
                    f'Number {orig_num:#x} does not fit in {dtype}')
        else:
            max_unsigned_value = (1 << (bit_width)) - 1
            if not (0 <= num <= max_unsigned_value):
                orig_num = num
                num = num & ((1 << bit_width) - 1)
                raise OverflowError(
                    f'Number {orig_num:#x} does not fit in {dtype}')
    dtype_mask = (1 << (bit_width)) - 1
    hex_format = '#x' if short_hex else '#0' + \
        str(int(bit_width / 8) * 2 + 2) + 'x'
    return f'{num & dtype_mask:{hex_format}}'


def hexstr_to_dtype_int(hexstr: str, dtype: str) -> int:
    if len(hexstr) == 0:
        return 0
    assert hexstr[0] != '-'
    assert is_imm(hexstr)
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


def is_imm(s: str) -> bool:
    """
    return True if s is safe for int(s, 0) or float(x)
    """
    if not s:
        return False
    try:
        int(s, 0)
        return True
    except ValueError:
        pass
    try:
        float(s)
        return True
    except ValueError:
        pass
    return False


def get_reg_num(s: str) -> int:
    if not s:
        return -1
    if len(s) < 2:
        return -1
    if s[0] != 'r':
        return -1
    if s[1:].isdigit():
        return int(s[1:])
    else:
        return -1


def extract_dtype(s: str) -> tuple[str, str]:
    """extract dtype from asm, also return the clean asm without dtype

    Returns:
        tuple[str, str]: (dtype, asm). dtype can be empty string
    """
    # find dtype.
    dtype = ''
    # regex find iXX/uXXX or ptr without digit
    m = re.findall(r'\b([ui]\d+|ptr|float|double)\b', s)
    if not m:
        return (dtype, s)
    if len(m) > 1:
        raise SyntaxError(f'illegal multiple dtypes in {s}')
    dtype = m[0]
    if dtype[0] in ['i', 'u'] and dtype[1:] not in ['8', '16', '32', '64']:
        raise SyntaxError(f'illegal dtype {dtype} in {s}')
    asm = re.sub(r'\b' + dtype + r'\b', '', s)
    asm = re.sub('\s+', ' ', asm).strip()
    return (dtype, asm)
