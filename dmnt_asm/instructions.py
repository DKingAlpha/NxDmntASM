#!/usr/bin/python3
# -*- coding:utf-8 -*-

from __future__ import annotations
import re
import string
from abc import ABC, abstractmethod
from collections import OrderedDict
import struct

from .utils import *
from .constants import *

STRICT_MODE = False


class _Properties(OrderedDict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = OrderedDict.get
    __setattr__ = OrderedDict.__setitem__
    __delattr__ = OrderedDict.__delitem__


def _int_from_hex(hexstr: str) -> int:
    return int(hexstr, 16)


def reinterpret_cast_to_int(value: str | int | float, width: InstDataType) -> int:
    if width == InstDataType.float:
        if '.' not in value:
            value = int(value, 0)
        return struct.unpack('>I', struct.pack('>f', float(value)))[0]
    elif width == InstDataType.double:
        if '.' not in value:
            value = int(value, 0)
        return struct.unpack('>Q', struct.pack('>d', float(value)))[0]
    else:
        if isinstance(value, str):
            hexint = int(value, 0)
        else:
            hexint = int(value)
        if width == InstDataType.i8:
            return struct.unpack('>B', struct.pack('>b', hexint))[0]
        elif width == InstDataType.i16:
            return struct.unpack('>H', struct.pack('>h', hexint))[0]
        elif width == InstDataType.i32:
            return struct.unpack('>I', struct.pack('>i', hexint))[0]
        elif width == InstDataType.i64:
            return struct.unpack('>Q', struct.pack('>q', hexint))[0]
        elif width == InstDataType.u8:
            return struct.unpack('>B', struct.pack('>B', hexint))[0]
        elif width == InstDataType.u16:
            return struct.unpack('>H', struct.pack('>H', hexint))[0]
        elif width == InstDataType.u32:
            return struct.unpack('>I', struct.pack('>I', hexint))[0]
        elif width == InstDataType.u64:
            return struct.unpack('>Q', struct.pack('>Q', hexint))[0]


def _aob_match(code_type: int | str, mc: str) -> bool:
    if isinstance(code_type, int):
        code_type = hex(code_type).lower()[2:]
    if len(code_type) > len(mc):
        return False
    code_type = code_type.lower()
    if not code_type:
        assert False, f'Invalid code type: {code_type}'
        return False
    for i in range(0, len(code_type)):
        c1 = code_type[i]
        c2 = mc[i]
        if c1 == '?':
            continue
        if c1 != c2:
            return False
    return True


class vm_inst(ABC):
    def __init__(self) -> None:
        self.format = ''
        self.format_info = {}
        self.binding = _Properties()
        self.prop = _Properties()

    @abstractmethod
    def build(self) -> vm_inst:
        pass

    @abstractmethod
    def dism(self) -> str:
        pass

    @abstractmethod
    def asm(self) -> str:
        pass

    def _asm(self) -> str:
        raw = list(self._gen_shortes_format())
        for k in self.prop:
            p = self.prop[k]
            pos, width = self.format_info[k]
            real_width = width
            k_value = self.binding[k][2](p)
            if k == 'V' and '(V' in self.format:
                if 'T' in self.prop and InstDataType_to_int(self.prop.T) == 8:
                    real_width = 16
            raw[pos:pos+real_width] = list(f'{k_value:0{real_width}X}')

        # normalize
        self.raw = ''.join(raw)
        self.code = self._normalize_mc(self.raw)
        assert self.code
        return self.code

    def _load_format(self) -> None:
        format = self._gen_shortes_format()  # it extends automatically
        self.format_info = {}
        for k in self.binding:
            # start_pos, [widths]
            assert k in format, f'{k} not found in format'
            self.format_info[k] = [format.find(k), format.count(k)]

    def dism_mc_line_to_prop(self, mc_line: str) -> bool:
        code = self._normalize_mc(mc_line)
        if not code:
            return False
        code = code.replace(' ', '').lower()
        if code[0] == 'a' and _int_from_hex(code[5]) in [2, 4, 5]:
            self.format_info['a'] = (7, 9)
        if code[:3] == 'fff' and _int_from_hex(code[5]) in [0, 2]:
            self.format = 'FFFTIXmn nnnnnnnn'
            self.format_info['n'] = (7, 9)
        # parse code
        self.prop.clear()
        for k in self.binding:
            start_pos, width = self.format_info[k]
            real_width = width
            if '(V' in self.format and k == 'V':
                # only allow expansion if format has (VVVVVVVV)
                if 'T' in self.prop and self.prop.T == InstDataType.u64:
                    real_width = 16
            if start_pos + real_width > len(code):
                return False
            k_value = _int_from_hex(code[start_pos: start_pos + real_width])
            self.prop[k] = self.binding[k][1](k_value)
        return True

    def _gen_shortes_format(self) -> str:
        return re.sub(r'(\(.+\))', '', self.format).replace(' ', '')

    @staticmethod
    def _normalize_mc(raw_mc: str) -> str:
        mc = raw_mc.replace(' ', '')
        if not set(mc.replace(' ', '')).issubset(string.hexdigits):
            return ''
        # dont enable this, it will break a lot of things
        # dword alignment, compatible with ams
        if (not STRICT_MODE) and ' ' in raw_mc:
            well_spaced_mc = re.sub(r'\s+', r' ', raw_mc)
            mcs = well_spaced_mc.split(' ')
            for i in range(0, len(mcs)):
                if len(mcs[i]) > 8:
                    if mcs[i][:-8].replace('0', '') != '':
                        raise ValueError(f'Invalid value {mcs[i]} in {raw_mc}')
                    mcs[i] = mcs[i][-8:]
                if len(mcs[i]) < 8:
                    mcs[i] = mcs[i].zfill(8)
            mc = ''.join(mcs)
        groupsize = 8
        if len(mc) % groupsize != 0:
            return ''
        code_sep = [mc[i:i+groupsize] for i in range(0, len(mc), groupsize)]
        return ' '.join(code_sep).upper()

    def __str__(self) -> str:
        return f'{self.asm()} ; {self.dism()}'


def vm_inst_dism(mc_line: str) -> vm_inst:
    lower_line = mc_line.strip().lower()
    # dirty check for nop
    if mc_line.replace(' ', '').replace('0', '') == '':
        return vm_nop()
    # find a match
    global_names = globals()
    for i in global_names:
        vm_cls = global_names[i]
        if i.startswith('vm_') and (not i.startswith('vm_inst')) and isinstance(vm_cls, type):
            assert 'CODE_TYPE' in dir(vm_cls)
            if _aob_match(vm_cls.CODE_TYPE, lower_line):
                ins: vm_inst = vm_cls()
                if ins.dism_mc_line_to_prop(mc_line):
                    return ins
    raise SyntaxError(f'invalid instruction: {mc_line}')


def _get_bracket_elems(s: str, merge_offset: bool = True) -> list[int | InstMemBase | tuple[int, bool]]:
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
            # we have done the check above, so it's safe to blind rstrip '+
            p = p.rstrip('+')
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

# helper


def _get_base_offset_regs_from_bracket(s: str) -> list[InstMemBase | None, int, list[tuple[int, bool]]]:
    elems = _get_bracket_elems(s)
    base = None
    offset = 0
    regs = []
    for elem in elems:
        if isinstance(elem, InstMemBase):
            if base is not None:
                raise SyntaxError(f'duplicate base in {s}')
            base = elem
        elif isinstance(elem, int):
            offset = elem
        elif isinstance(elem, tuple):
            regs.append(elem)
    return (base, offset, regs)


def vm_inst_asm(raw_line: str) -> vm_inst:
    # fast check for nested expression
    if raw_line.count('[') > 1 or raw_line.count(']') > 1:
        raise SyntaxError('nested expression is not supported')
    if raw_line.count('(') > 1 or raw_line.count(')') > 1:
        raise SyntaxError('( ) are not supported')

    lower_line = raw_line.strip().lower()
    parts = [i.strip() for i in lower_line.split(' ') if i.strip()]
    dtype, asm_line = extract_dtype(lower_line)
    if asm_line == 'nop':
        return vm_nop().build()
    elif parts[0] == 'if':
        # if
        if len(parts) <= 1:
            raise SyntaxError('invalid if statement')
        # if key
        if parts[1] == 'key':
            if len(parts) <= 2:
                raise SyntaxError('invalid if key statement')
            keys = ''.join(parts[2:]).replace(' ', '')
            return vm_if_key().build(keys)
        # if conditions
        op1_cond_op2 = asm_line[2:].strip()
        if asm_line.endswith('then'):
            op1_cond_op2 = op1_cond_op2[:-4].strip()
        match = re.match(r'^(.+)\s+([=><!]+)\s+(.+)$', op1_cond_op2)
        if not match:
            raise SyntaxError('invalid if statement')
        op1 = match.group(1)
        cond = match.group(2)
        op2 = match.group(3)
        if cond not in ['==', '!=', '>', '<', '>=', '<=']:
            raise SyntaxError(f'illegal condition {cond} if statement')
        cond = InstCondition(cond)
        if op1[0] == '[' and op1[-1] == ']':
            if not is_imm(op2):
                raise SyntaxError(f'{op2} is not imm in if statement')
            value: str = op2
            base, offset, regs = _get_base_offset_regs_from_bracket(op1)
            if base is None:
                raise SyntaxError(f'missing mem base here')
            if len(regs):
                raise SyntaxError(
                    f'regs are not supported as left operand in if statement')
            return vm_if_off_COND_imm().build(offset, cond, value, base, dtype)
        elif op2[0] == '[' and op2[-1] == ']':
            rN = get_reg_num(op1)
            if rN < 0:
                raise SyntaxError(f'illegal {op1} in if statement')
            base, offset, regs = _get_base_offset_regs_from_bracket(op2)
            for reg in regs:
                if reg[1]:
                    raise SyntaxError(
                        f'r{reg[0]}++ is not supported in if statement')
            regs = [reg[0] for reg in regs]
            if base is not None:
                if len(regs) >= 2:
                    raise SyntaxError(f'illegal {op2} in if statement')
                if len(regs) == 0:
                    return vm_if_reg_COND_off().build(rN, cond, offset, base, dtype)
                else:
                    if offset:
                        raise SyntaxError(f'offset unsupported here')
                    return vm_if_reg_COND_offreg().build(rN, cond, regs[0], base, dtype)
            elif len(regs) == 1:
                return vm_if_reg_COND_reg_off().build(rN, cond, regs[0], offset, dtype)
            elif len(regs) == 2:
                if offset:
                    raise SyntaxError(f'offset unsupported here')
                return vm_if_reg_COND_reg_reg().build(rN, cond, regs[0], regs[1], dtype)
            else:
                raise SyntaxError(f'illegal {op2} in if statement')
        elif op1[0] == 'r':
            if not is_imm(op2):
                raise SyntaxError(f'{op2} is not imm in if statement')
            value: str = op2
            rN = get_reg_num(op1)
            if rN < 0:
                raise SyntaxError(f'illegal {op1} in if statement')
            return vm_if_reg_COND_imm().build(rN, cond, value, dtype)
        elif op1[0] == 'r' and op2[0] == 'r':
            rN = get_reg_num(op1)
            rM = get_reg_num(op2)
            if rN < 0:
                raise SyntaxError(f'illegal {op1} in if statement')
            if rM < 0:
                raise SyntaxError(f'illegal {op2} in if statement')
            return vm_if_reg_COND_reg().build(rN, cond, rM, dtype)
        else:
            raise SyntaxError('invalid if statement')
    elif asm_line == 'else':
        return vm_else().build()
    elif asm_line == 'endif':
        return vm_endif().build()
    elif asm_line == 'pause':
        return vm_pause().build()
    elif asm_line == 'resume':
        return vm_resume().build()
    elif parts[0] == 'loop':
        if len(parts) != 4:
            raise SyntaxError('invalid loop statement')
        match = re.match(r'^loop\s+r(\d+)\s+to\s(\d+)$', asm_line)
        if not match:
            raise SyntaxError('invalid loop statement')
        reg = int(match.group(1))
        count = int(match.group(2))
        return vm_loop().build(reg, count)
    elif parts[0] == 'endloop':
        if len(parts) != 2:
            raise SyntaxError('invalid endloop statement')
        reg = get_reg_num(parts[1])
        if reg < 0:
            raise SyntaxError(
                f'illegal register {parts(1)} in endloop statement')
        return vm_endloop().build(reg)
    elif parts[0] == 'log':
        match = re.match(r'^log\s+(\d+)\s+(.*)$', asm_line)
        if not match:
            raise SyntaxError('invalid log statement')
        logid = int(match.group(1))
        base, offset, regs = _get_base_offset_regs_from_bracket(match.group(2))
        for reg in regs:
            if reg[1]:
                raise SyntaxError(
                    f'r{reg[0]}++ is not supported in if statement')
        regs = [reg[0] for reg in regs]
        if base is not None:
            if regs:
                if len(regs) >= 2:
                    raise SyntaxError(
                        f'too many regs {regs} in mem-based log statement.')
                if offset:
                    raise SyntaxError(f'offset unsupported here')
                return vm_log_offreg().build(logid, regs[0], base, dtype)
            else:
                return vm_log_off().build(logid, offset, base, dtype)
        elif regs:
            if len(regs) == 1:
                if offset == 0:    # rM
                    return vm_log_reg().build(logid, regs[0], dtype)
                else:              # rM + offset
                    return vm_log_reg_off().build(logid, regs[0], offset, dtype)
            elif len(regs) == 2:   # rM + rN
                if offset:
                    raise SyntaxError(f'offset unsupported here')
                return vm_log_reg_offreg().build(logid, regs[0], regs[1], dtype)
            else:
                raise SyntaxError(
                    f'too many regs {regs} in reg-based log statement.')
        else:
            raise SyntaxError('invalid log statement')
    elif 'static' in asm_line:
        # rN = static[i]  # when i < 0x80
        # static[i] = rN  # when i >= 0x80
        if '=' not in asm_line:
            raise SyntaxError('invalid static statement')
        op1, op2 = asm_line.split('=')
        op1 = op1.strip()
        op2 = op2.strip()
        if op1.startswith('r') and op2.startswith('static'):
            return vm_rw_static_reg().build(int(op1[1:]), int(op2[6:].strip('[]'), 0))
        elif op1.startswith('static') and op2.startswith('r'):
            return vm_rw_static_reg().build(int(op2[1:]), int(op1[6:].strip('[]'), 0))
        else:
            raise SyntaxError('invalid static statement')
    elif 'save' in asm_line:
        # save[i] = rN
        # rN = save[i]
        # save[i] = 0
        # save rA, rB, ..., rN
        # save[i,j,...k] = 0
        if '=' in asm_line:
            op1, op2 = asm_line.split('=')
            op1 = op1.strip()
            op2 = op2.strip()
            if op1.startswith('save') and op2.startswith('r'):
                save_indices = op1[4:].strip('[]')
                if ',' in save_indices:
                    return vm_save_restore_mask().build(InstSaveRestoreRegOp.SAVE, save_indices)
                else:
                    return vm_save_restore().build(int(save_indices, 0), InstSaveRestoreRegOp.SAVE, int(op2[1:]))
            elif op1.startswith('r') and op2.startswith('save'):
                return vm_save_restore().build(int(op1[1:]), InstSaveRestoreRegOp.RESTORE, int(op2[4:].strip('[]'), 0))
            elif op1.startswith('save') and op2.strip() == '0':
                dests = op1[4:].strip('[]')
                if ',' in dests:
                    return vm_save_restore_mask().build(InstSaveRestoreRegOp.CLEAR, dests)
                else:
                    destreg = int(dests, 0)
                    return vm_save_restore().build(destreg, InstSaveRestoreRegOp.CLEAR, 0)
        else:
            if parts[0] != 'save':
                raise SyntaxError('invalid save statement')
            return vm_save_restore_mask().build(InstSaveRestoreRegOp.SAVE, ' '.join(parts[1:]))
    elif 'restore' in asm_line:
        # restore rA, rB, ..., rN
        return vm_save_restore_mask().build(InstSaveRestoreRegOp.RESTORE, ' '.join(parts[1:]))
    elif re.match(r'r[r\d,]+=0', asm_line.replace(' ', '')):
        # rN = 0
        # r1,r2,... = 0
        if '=' not in asm_line:
            raise SyntaxError('invalid statement')
        regs, _ = asm_line.replace(' ', '').replace('=')
        if ',' in asm_line:
            return vm_save_restore_mask().build(InstSaveRestoreRegOp.REG_ZERO, regs)
        else:
            return vm_save_restore().build(int(parts[0].strip()[1:]), InstSaveRestoreRegOp.REG_ZERO, 0)
    elif '=' in asm_line:
        # this must be an r/w instruction.
        # we have dealt with other instructions with '=' above
        return _vm_inst_asm_rw(dtype, asm_line)
    else:
        raise SyntaxError(f'invalid statement')


def _vm_inst_asm_rw(dtype: str, asm_line: str) -> vm_inst:
    # reg<->reg
    # {dtype} rD = rS
    # {dtype} rD = !rS
    match = re.match(r'^r(\d+)\s*=\s*(~?)r(\d+)$', asm_line)
    if match:
        if match.group(2) == '~':
            return vm_set_reg_reg().build(int(match.group(1)), int(match.group(3)), InstArithmetic.LOGICAL_NOT, 0, dtype)
        else:
            return vm_set_reg_reg().build(int(match.group(1)), int(match.group(3)), InstArithmetic.MOVE, 0, dtype)

    # {dtype} rD = rS OP value
    # {dtype} rD = rS OP rs
    match = re.match(
        r'^r(\d+)\s*=\s*r(\d+)\s*([\+\-\*<>&|^]{1,2})\s*(.+)$', asm_line)
    if match:
        op = match.group(3)
        if op not in ['+', '-', '*', '<<', '>>', '&', '|', '^']:
            raise SyntaxError(f'unknown arithmetic operator {op}')
        rD = int(match.group(1))
        op = InstArithmetic(op)
        rS = int(match.group(2))
        if match.group(4).startswith('r'):
            rs = get_reg_num(match.group(4))
            if rs < 0:
                raise SyntaxError(f'invalid register {op1}')
            return vm_set_reg_reg().build(rD, rS, op, rs, dtype)
        elif is_imm(match.group(4)):
            return vm_set_reg_imm().build(rD, rS, op, match.group(4), dtype)
        else:
            raise SyntaxError(f'invalid operand {match.group(4)}')

    # reg update (legacy, use next instruction instead)
    # {dtype} rN OP= value
    match = re.match(r'^r(\d+)\s*([\+\-\*<>]{1,2})=\s*(.+)$', asm_line)
    if match:
        op = match.group(2)
        if op not in ['+', '-', '*', '<<', '>>']:
            raise SyntaxError(f'unknown arithmetic operator {op}')
        rN = int(match.group(1))
        op = InstArithmetic(op)
        if is_imm(match.group(3)):
            return vm_legacy_set_imm().build(rN, op, match.group(3), dtype)
        else:
            raise SyntaxError(f'invalid imm {match.group(3)}')

    # reg<-imm
    # rN = value  # always 64-bit
    match = re.match(r'^r(\d+)\s*=\s*([^r]+)$', asm_line)
    if match:
        if is_imm(match.group(2)):
            return vm_move_reg().build(int(match.group(1)), match.group(2))
        else:
            # well could be and [...] expression. dont raise error here
            pass

    # the worst part comes
    op1, op2 = asm_line.replace(' ', '').split('=')
    op1 = op1.strip()
    op2 = op2.strip()
    if op1[0] == '[' and op1[-1] == ']':
        # {dtype} [base + rN {+offset}] = value
        # {dtype} [rM{++} {+rN}] = value
        # {dtype} [rM{++} {+offset}] = rS
        # {dtype} [rM{++} {+rN}] = rS
        # {dtype} [base + {+offset {+rM{++}}}] = rS
        base, offset, regs = _get_base_offset_regs_from_bracket(op1)
        if is_imm(op2):
            value: str = op2
            if base is not None:
                if len(regs) == 0 or len(regs) > 2:
                    raise SyntaxError(f'illegal registers in {op1}')
                if regs[0][1] == True:
                    raise SyntaxError(f'r{regs[0]}++ is not supported here')
                return vm_store_imm().build(offset, value, regs[0][0], base, dtype)
            else:
                if offset:
                    raise SyntaxError(f'offset is not supported here')
                if len(regs) == 0 or len(regs) > 2:
                    raise SyntaxError(f'illegal registers in {op1}')
                if len(regs) > 1 and regs[1][1] == True:
                    raise SyntaxError(f'r{regs[1]}++ is not supported here')
                if len(regs) == 1:
                    return vm_store_reg_imm().build(regs[0][0], value, regs[0][1], False, 0, dtype)
                else:
                    return vm_store_reg_imm().build(regs[0][0], value, regs[0][1], True, regs[1][0], dtype)
        else:
            rS = int(op2[1:])
            if base is not None:
                # [base + {+offset {+rM{++}}}] = rS
                if len(regs) > 1:
                    raise SyntaxError(f'illegal registers in {op1}')
                if len(regs) == 1:
                    if offset == 0:
                        return vm_store_reg().build(InstOffsetType.MEMBASE_REG, regs[0][0], regs[0][1], 0, base, rS, dtype)
                    else:
                        return vm_store_reg().build(InstOffsetType.MEMBASE_IMM_OFFREG, regs[0][0], regs[0][1], offset, base, rS, dtype)
                else:
                    return vm_store_reg().build(InstOffsetType.MEMBASE_IMM, 0, False, offset, base, rS, dtype)
            else:
                # [rM{++} {+offset {+rN}}] = rS
                if len(regs) == 0 or len(regs) > 2:
                    raise SyntaxError(f'illegal registers in {op1}')
                if len(regs) > 1 and regs[1][1] == True:
                    raise SyntaxError(f'r{regs[1]}++ is not supported here')
                if offset and len(regs) == 2:
                    raise SyntaxError(
                        f'offset {offset} and offreg r{regs[1][0]} can not exist at the same time')
                if len(regs) == 2:
                    return vm_store_reg().build(InstOffsetType.OFF_REG, regs[0][0], regs[0][1], regs[1][0], rS, dtype)
                else:
                    return vm_store_reg().build(InstOffsetType.OFF_IMM, regs[0][0], regs[0][1], offset, rS, dtype)

    elif op2[0] == '[' and op2[-1] == ']':
        # {dtype} rN = [base {+offset}]
        # {dtype} rN = [rN {+ offset}]  # Note: {dtype} rA = [rB + offset] is unsupported
        rN = get_reg_num(op1)
        if rN < 0:
            raise SyntaxError(f'invalid register {op1}')
        base, offset, regs = _get_base_offset_regs_from_bracket(op2)
        if len(regs) and base is not None:
            raise SyntaxError(
                'either `{dtype} rN = [base {+offset}]` or {dtype} rN = [rN {+offset}] is supported')
        if base is not None:
            return vm_load().build(rN, offset, False, base, dtype)
        else:
            if len(regs) != 1 or regs[0][1] == True or regs[0][0] != rN:
                raise SyntaxError('only support {dtype} rN = [rN {+offset}]')
            return vm_load().build(rN, offset, True, 0, dtype)
    else:
        raise SyntaxError(f'invalid statement')


class vm_nop(vm_inst):
    """
    well, people write 00000000 .... in credit section
    """
    CODE_NAME = 'nop'
    CODE_TYPE = '000000000'

    def build(self) -> vm_inst:
        return self

    def asm(self) -> str:
        return '00000000 00000000 00000000'

    def dism(self) -> str:
        return 'nop'


class vm_store_imm(vm_inst):
    """
    ### Syntax
    {dtype} [base + rN {+offset}] = value
        where:
            offset <= 0xFFFFFFFFFF
            dtype: default = u32
        example:
            i8 [maIn + r2 + 0x100] = -18

    ### Code Type 0x0: Store Static Value to Memory
    Code type 0x0 allows writing a static value to a memory address.

    #### Encoding
    `0TMR00AA AAAAAAAA VVVVVVVV (VVVVVVVV)`

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + M: Memory region to write to (0 = Main NSO, 1 = Heap, 2 = Alias, 3 = Aslr).
    + R: Register to use as an offset from memory region base.
    + A: Immediate offset to use from memory region base.
    + V: Value to write.
    """
    CODE_TYPE = '0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '0TMR00AA AAAAAAAA VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            M=('base', InstMemBase, int),
            R=('offreg', int, int),
            A=('offset', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              offset: int,    # uint40
              value: str | int | float,     # <= uintmax_of(width)
              offreg=0,
              base=InstMemBase.MAIN,
              width=InstDataType.u32,
              ) -> vm_store_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if offreg >= 16 or offreg < 0:
            raise ValueError(f'reg {offreg} out of range')
        if (offset >> 10 * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'{p.T} [{p.M.name.lower()} + {p.A:#x} + r{p.R}] = {int_to_dtype_hexstr(p.V, str(p.T), True)}'


class vm_if_off_COND_imm(vm_inst):
    """
    ### Syntax
    if {dtype} [base {+offset}] COND value {then}
        where:
            COND = >, >=, <, <=, ==, !=
            THEN is optional keyword


    ### Code Type 0x1: Begin Conditional Block
    Code type 0x1 performs a comparison of the contents of memory to a static value.

    If the condition is not met, all instructions until the appropriate End or Else conditional block terminator are skipped.

    #### Encoding
    `1TMC00AA AAAAAAAA VVVVVVVV (VVVVVVVV)`

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + M: Memory region to write to (0 = Main NSO, 1 = Heap, 2 = Alias, 3 = Aslr).
    + C: Condition to use, see below.
    + A: Immediate offset to use from memory region base.
    + V: Value to compare to.

    #### Conditions
    + 1: >
    + 2: >=
    + 3: <
    + 4: <=
    + 5: ==
    + 6: !=
    """
    CODE_TYPE = '1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '1TMC00AA AAAAAAAA VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            M=('base', InstMemBase, int),
            C=('cond', InstCondition, int),
            A=('offset', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              offset: int,    # uint40
              cond: InstCondition,
              value: str | int | float,     # <= uintmax_of(width)
              base=InstMemBase.MAIN,
              width=InstDataType.u32,
              ) -> vm_if_off_COND_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if (offset >> self.format.count('A') * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} [{p.M.name.lower()} + {p.A:#x}] {p.C} {int_to_dtype_hexstr(p.V, str(p.T), True)}'


class vm_endif(vm_inst):
    """
    ### Syntax
    endif

    ### Code Type 0x2: End Conditional Block
    Code type 0x2 marks the end of a conditional block (started by Code Type 0x1 or Code Type 0x8).

    When an Else is executed, all instructions until the appropriate End conditional block terminator are skipped.

    #### Encoding
    `2X000000`

    + X: End type (0 = End, 1 = Else).
    """
    CODE_NAME = 'endif'
    CODE_TYPE = '20'

    def build(self) -> vm_endif:
        return self

    def asm(self) -> str:
        return '20000000'

    def dism(self) -> str:
        return self.CODE_NAME


class vm_else(vm_inst):
    """
    ### Syntax
    else
    """
    CODE_NAME = 'else'
    CODE_TYPE = '21'

    def build(self) -> vm_else:
        return self

    def asm(self) -> str:
        return '21000000'

    def dism(self) -> str:
        return self.CODE_NAME


class vm_loop(vm_inst):
    """
    ### Syntax
    loop rN to count
        examples:
            loop r2 to 100

    ### Code Type 0x3: Start/End Loop
    Code type 0x3 allows for iterating in a loop a fixed number of times.

    #### Start Loop Encoding
    `300R0000 VVVVVVVV`

    + R: Register to use as loop counter.
    + V: Number of iterations to loop.

    #### End Loop Encoding
    `310R0000`

    + R: Register to use as loop counter.
    """
    CODE_NAME = 'loop'
    CODE_TYPE = '30'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '300R0000 VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            R=('reg', int, int),
            V=('count', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              count: int,
              ) -> vm_loop:
        # verify args
        if (reg >= 16):
            raise ValueError(f'reg {reg} out of range')
        if (count >> self.format.count('V') * 4) != 0:
            raise ValueError(f'count {count} overflow')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        return f'{self.CODE_NAME} r{self.prop.R} to {self.prop.V}'


class vm_endloop(vm_inst):
    """
    endloop rN
    """
    CODE_NAME = 'endloop'
    CODE_TYPE = '31'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '310R0000'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            R=('reg', int, int),
        )
        self._load_format()

    def build(self,
              reg: int
              ) -> vm_endloop:
        # verify args
        if reg >= 16 or reg < 0:
            raise ValueError(f'reg {reg} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        return f'{self.CODE_NAME} r{self.prop.R}'


class vm_move_reg(vm_inst):
    """
    ### Syntax
    rN = value  # always 64-bit

    ### Code Type 0x4: Load Register with Static Value
    Code type 0x4 allows setting a register to a constant value.

    #### Encoding
    `400R0000 VVVVVVVV VVVVVVVV`

    + R: Register to use.
    + V: Value to load.
    """
    CODE_TYPE = '4'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '400R0000 VVVVVVVV VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            R=('reg', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              value: str | int | float,
              width=InstDataType.u64,
              ) -> vm_move_reg:
        # fix arguments
        if not width:
            width = InstDataType.u64
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if (reg >= 16):
            raise ValueError(f'reg {reg} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        return f'r{self.prop.R} = {self.prop.V:#x}'


class vm_load(vm_inst):
    """
    ### Syntax
    {dtype} rN = [base {+offset}]
    {dtype} rN = [rN {+offset}]

    Note: {dtype} rA = [rB + offset] is unsupported

    ### Code Type 0x5: Load Register with Memory Value
    Code type 0x5 allows loading a value from memory into a register, either using a fixed address or by dereferencing the destination register.

    #### Load From Fixed Address Encoding
    `5TMR00AA AAAAAAAA`

    + T: Width of memory read (1, 2, 4, or 8 bytes).
    + M: Memory region to write to (0 = Main NSO, 1 = Heap, 2 = Alias, 3 = Aslr).
    + R: Register to load value into.
    + A: Immediate offset to use from memory region base.

    #### Load from Register Address Encoding
    `5T0R10AA AAAAAAAA`

    + T: Width of memory read (1, 2, 4, or 8 bytes).
    + R: Register to load value into. (This register is also used as the base memory address).
    + A: Immediate offset to use from register R.
    """
    CODE_TYPE = '5'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '5TMRS0AA AAAAAAAA'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            M=('base', InstMemBase, int),
            R=('reg', int, int),
            A=('offset', int, int),
            S=('self_deref', bool, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              offset: int,    # uint40
              self_deref: bool,
              base=InstMemBase.MAIN,
              width=InstDataType.u32,
              ) -> vm_load:
        # verify args
        if (reg >= 16):
            raise ValueError(f'reg {reg} out of range')
        if (offset >> self.format.count('A') * 4) != 0:
            raise ValueError(f'offset {offset} overflow')
        if not width:
            width = InstDataType.u32
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        if self.prop.S:
            # manually set 0 to comply with format
            self.prop.M = InstMemBase(0)
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.S:
            return f'{str(p.T)} r{p.R} = [r{p.R} + {p.A:#x}]'
        else:
            return f'{str(p.T)} r{p.R} = [{p.M.name.lower()} + {p.A:#x}]'


class vm_store_reg_imm(vm_inst):
    """
    ### Syntax
    {dtype} [rM{++} {+rN}] = value
        where:
            rM++ means rM += width after operation
        example:
            i32 [r0++ + r1] = 0x12345678
            i32 [r0 + r1] = 0x12345678
            i32 [r0++] = 0x12345678

    ### Code Type 0x6: Store Static Value to Register Memory Address
    Code type 0x6 allows writing a fixed value to a memory address specified by a register.

    #### Encoding
    `6T0RIor0 VVVVVVVV VVVVVVVV`

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + R: Register used as base memory address.
    + I: Increment register flag (0 = do not increment R, 1 = increment R by T).
    + o: Offset register enable flag (0 = do not add r to address, 1 = add r to address).
    + r: Register used as offset when o is 1.
    + V: Value to write to memory.
    """
    CODE_TYPE = '6'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '6T0RIor0 VVVVVVVV VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            R=('basereg', int, int),
            I=('basereg_inc', bool, int),
            o=('off_by_reg', bool, int),
            r=('offreg', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              basereg: int,
              value: str | int | float,
              basereg_inc: bool = False,
              off_by_reg: bool = False,
              offreg: int = 0,
              width=InstDataType.u32,
              ) -> vm_store_reg_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if offreg >= 16 or offreg < 0:
            raise ValueError(f'reg {offreg} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        addr_reg = f'r{p.R}'
        if p.I:
            addr_reg += '++'
        if p.o:
            addr_reg += f' + r{p.r}'
        return f'{p.T} [{addr_reg}] = {p.V:#x}'


class vm_legacy_set_imm(vm_inst):
    """
    ### Syntax
    {dtype} rN OP= value
        where:
            OP is one of +, -, *, <<, >>
        example:
            r0 += 0x12345678

    ### Code Type 0x7: Legacy Arithmetic
    Code type 0x7 allows performing arithmetic on registers.

    However, it has been deprecated by Code type 0x9, and is only kept for backwards compatibility.

    #### Encoding
    `7T0RC000 VVVVVVVV`

    + T: Width of arithmetic operation (1, 2, 4, or 8 bytes).
    + R: Register to apply arithmetic to.
    + C: Arithmetic operation to apply, see below.
    + V: Value to use for arithmetic operation.

    #### Arithmetic Types
    + 0: Addition
    + 1: Subtraction
    + 2: Multiplication
    + 3: Left Shift
    + 4: Right Shift
    """
    CODE_TYPE = '7'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '7T0RC000 VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            R=('reg', int, int),
            C=('op', InstArithmetic, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              op: InstArithmetic,
              value: str | int | float,
              width=InstDataType.u32,
              ) -> vm_store_reg_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if reg >= 16 or reg < 0:
            raise ValueError(f'reg out of range')
        # bind args
        if isinstance(op, str) and op != '=' and op.endswith('='):
            op = InstArithmetic(op[:-1])
        assert op <= InstArithmetic.RSHIFT, f'invalid legacy arithmetic type {op}'
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'{p.T} r{p.R} {p.C}= {p.V:#x}'


class vm_if_key(vm_inst):
    """
    ### Syntax
    if key KEYNAME | KEYNAME | ...


    ### Code Type 0x8: Begin Keypress Conditional Block
    Code type 0x8 enters or skips a conditional block based on whether a key combination is pressed.

    #### Encoding
    `8kkkkkkk`

    + k: Keypad mask to check against, see below.

    Note that for multiple button combinations, the bitmasks should be ORd together.
    """
    CODE_TYPE = '8'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '8kkkkkkk'

        def key_decoder(keys: int | str | InstKeyName | list[int | str | InstKeyName]) -> InstKeyFlag:
            keycomb = InstKeyFlag(0)

            def _parse_key(key: int | str | InstKeyName):
                result = InstKeyFlag(0)
                if isinstance(key, str):
                    if '|' in key:
                        for k in key.split('|'):
                            result |= InstKeyName(k.strip()).value
                    else:
                        result |= InstKeyName(key.strip()).value
                elif isinstance(key, int):
                    result |= key
                elif isinstance(key, InstKeyName):
                    result |= key.value
                else:
                    assert False, f'invalid key type {type(key)} {key}'
                return result
            if isinstance(keys, (tuple, list)):
                for key in keys:
                    keycomb |= _parse_key(key)
            else:
                keycomb = _parse_key(keys)
            return keycomb

        def key_encoder(keycomb: InstKeyFlag):
            return keycomb.value

        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            k=('keys', key_decoder, key_encoder),
        )
        self._load_format()

    def build(self, keys: str | list[str | InstKeyName]) -> vm_if_off_COND_imm:
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if key {p.k.name}'


class vm_set_reg_reg(vm_inst):
    """
    ### Syntax
    {dtype} rD = rS OP rs
    {dtype} rD = rS
    {dtype} rD = ~rS
        where:
            OP is one of +, -, *, <<, >> & | ^

    ### Code Type 0x9: Perform Arithmetic
    Code type 0x9 allows performing arithmetic on registers.

    #### Register Arithmetic Encoding
    `9TCRS0s0`

    + T: Width of arithmetic operation (1, 2, 4, or 8 bytes).
    + C: Arithmetic operation to apply, see below.
    + R: Register to store result in.
    + S: Register to use as left-hand operand.
    + s: Register to use as right-hand operand.
    """
    CODE_TYPE = '9????0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '9TCRS0s0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            C=('op', InstArithmetic, int),
            R=('dest', int, int),
            S=('op1', int, int),
            s=('op2', int, int),
        )
        self._load_format()

    def build(self,
              dest: int,
              op1: int,
              op: InstArithmetic,
              op2: int,
              width=InstDataType.u32,
              ) -> vm_store_reg_imm:
        if dest >= 16 or dest < 0 or op1 >= 16 or op1 < 0 or op2 >= 16 or op2 < 0:
            raise ValueError(f'reg out of range')
        if not width:
            width = InstDataType.u32
        # bind args
        if isinstance(op, str) and op != '=' and op.endswith('='):
            op = InstArithmetic(op[:-1])
        local_vars = locals()
        for sym in ('dest', 'op1', 'op2'):
            assert local_vars[sym] < 16, f'invalid register {sym} {local_vars[sym]}'
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.C == InstArithmetic.MOVE:
            return f'{p.T} r{p.R} = r{p.S}'
        elif p.C == InstArithmetic.LOGICAL_NOT:
            return f'{p.T} r{p.R} = !r{p.S}'
        return f'{p.T} r{p.R} = r{p.S} {p.C} r{p.s}'


class vm_set_reg_imm(vm_inst):
    """
    ### Syntax
    {dtype} rD = rS OP value
    {dtype} rD = rS
    {dtype} rD = !rS
        where:
            OP is one of +, -, *, <<, >> & | ^

    #### Immediate Value Arithmetic Encoding
    `9TCRS100 VVVVVVVV (VVVVVVVV)`

    + T: Width of arithmetic operation (1, 2, 4, or 8 bytes).
    + C: Arithmetic operation to apply, see below.
    + R: Register to store result in.
    + S: Register to use as left-hand operand.
    + V: Value to use as right-hand operand.
    """
    CODE_TYPE = '9????1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '9TCRS100 VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            C=('op', InstArithmetic, int),
            R=('dest', int, int),
            S=('src', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              dest: int,
              src: int,
              op: InstArithmetic,
              value: str | int | float,
              width=InstDataType.u32,
              ) -> vm_set_reg_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if dest >= 16 or dest < 0 or src >= 16 or src < 0:
            raise ValueError(f'reg out of range')
        # bind args
        if isinstance(op, str) and op != '=' and op.endswith('='):
            op = InstArithmetic(op[:-1])
        local_vars = locals()
        for sym in ('dest', 'src'):
            if local_vars[sym] >= 16:
                raise ValueError(f'invalid register {sym} {local_vars[sym]}')
        if (value >> self.format.count('V') * 4) != 0:
            raise ValueError(f'value {value} overflow')
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.C == InstArithmetic.MOVE:
            return f'{p.T} r{p.R} = r{p.S}'
        elif p.C == InstArithmetic.LOGICAL_NOT:
            return f'{p.T} r{p.R} = !r{p.S}'
        return f'{p.T} r{p.R} = r{p.S} {p.C} {int_to_dtype_hexstr(p.V, str(p.T), True)}'


class vm_store_reg(vm_inst):
    """
    ### Syntax
    {dtype} [rM{++} {+offset}] = rS
    {dtype} [rM{++} {+rN}] = rS
    {dtype} [BASE + {+offset {+rM{++}}}] = rS
        where:
            rM ++ means rM +=width after operation
        example:
            u32 [r2++ ] = r5
            u32 [r2++ + 2 + r3] = r4


    ### Code Type 0xA: Store Register to Memory Address
    Code type 0xA allows writing a register to memory.

    #### Encoding
    `ATSRIOxa (aaaaaaaa)`

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + S: Register to write to memory.
    + R: Register to use as base address.
    + I: Increment register flag (0 = do not increment R, 1 = increment R by T).
    + O: Offset type, see below.
    + x: Register used as offset when O is 1, Memory type when O is 3, 4 or 5.
    + a: Value used as offset when O is 2, 4 or 5.

    #### Offset Types
    + 0: No Offset
    + 1: Use Offset Register
    + 2: Use Fixed Offset
    + 3: Memory Region + Base Register
    + 4: Memory Region + Relative Address (ignore address register)
    + 5: Memory Region + Relative Address + Base Register as offset
    """
    CODE_TYPE = 'A'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'ATSRIOxa (aaaaaaaa)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            S=('srcreg', int, int),
            R=('basereg', int, int),
            I=('basereg_inc', bool, int),
            O=('offset_type', InstOffsetType, int),
            x=('offreg_or_membase', int, int),
            a=('offset', int, int),
        )
        self._load_format()

    def build(self,
              offset_type: InstOffsetType,
              basereg: int,
              basereg_inc: bool,
              offset: int,
              offreg_or_membase: int | InstMemBase,
              srcreg: int,
              width=InstDataType.u32,
              ) -> vm_store_reg:
        # verify args
        if srcreg >= 16 or basereg >= 16 or (int(offset_type) <= 1 and offreg_or_membase >= 16):
            raise ValueError(f'reg out of range')
        if (offset >> (self.format.count('a')) * 4) != 0:
            raise ValueError(f'offset {offset} overflow')
        if not width:
            width = InstDataType.u32
        # bind args
        if not isinstance(offreg_or_membase, int):
            # make it works for string 'main'
            offreg_or_membase = InstMemBase(offreg_or_membase)
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        if int(self.prop.O) in [2, 4, 5]:
            self.format_info['a'] = (7, 9)  # fix special format
        return self

    def asm(self) -> str:
        if int(self.prop.O) in [2, 4, 5]:
            self.format_info['a'] = (7, 9)  # fix special format
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        addr_expr = ''
        if p.O <= InstOffsetType.OFF_IMM:
            addr_expr = f'r{p.R}{"++" if p.I else ""}'
            if p.O == InstOffsetType.OFF_IMM:
                addr_expr += f' + {p.a:#x}'
            elif p.O == InstOffsetType.OFF_REG:
                addr_expr += f' + r{p.x}'
        else:
            addr_expr = InstMemBase(p.x).name.lower()
            if p.O == InstOffsetType.MEMBASE_REG:
                addr_expr += f' + r{p.R}'
            elif p.O == InstOffsetType.MEMBASE_IMM:
                addr_expr += f' + {p.a:#x}'
            elif p.O == InstOffsetType.MEMBASE_IMM_OFFREG:
                addr_expr += f' + {p.a:#x} + r{p.R}'
            else:
                assert False, f'invalid offset type {p.O}'
        return f'{p.T} [{addr_expr}] = r{p.S}'


class vm_if_reg_COND_off(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [base {+offset}] {then}
        where:
            COND = >, >=, <, <=, ==, !=
            THEN is optional keyword

    ### Code Type 0xC0: Begin Register Conditional Block
    Code type 0xC0 performs a comparison of the contents of a register and another value. This code support multiple operand types, see below.

    If the condition is not met, all instructions until the appropriate conditional block terminator are skipped.

    #### Encoding
    ```
    C0TcSX##
    C0TcS0Ma aaaaaaaa
    C0TcS1Mr
    C0TcS2Ra aaaaaaaa
    C0TcS3Rr
    C0TcS400 VVVVVVVV (VVVVVVVV)
    C0TcS5X0
    ```

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + c: Condition to use, see below.
    + S: Source Register.
    + X: Operand Type, see below.
    + M: Memory Type (operand types 0 and 1).
    + R: Address Register (operand types 2 and 3).
    + a: Relative Address (operand types 0 and 2).
    + r: Offset Register (operand types 1 and 3).
    + X: Other Register (operand type 5).
    + V: Value to compare to (operand type 4).

    #### Operand Type
    + 0: Memory Base + Relative Offset
    + 1: Memory Base + Offset Register
    + 2: Register + Relative Offset
    + 3: Register + Offset Register
    + 4: Static Value
    + 5: Other Register

    #### Conditions
    + 1: >
    + 2: >=
    + 3: <
    + 4: <=
    + 5: ==
    + 6: !=
    """
    CODE_TYPE = 'C0???0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS0Ma aaaaaaaa'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            M=('base', InstMemBase, int),
            a=('offset', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              offset: int,    # uint36
              base=InstMemBase.MAIN,
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_off:
        # verify args
        if (offset >> self.format.count('a') * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} [{p.M.name.lower()}+{p.a:#x}]'


class vm_if_reg_COND_offreg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [base + rM] {then}
        where:
            dtype default = u64
    """
    CODE_TYPE = 'C0???1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS1Mr'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            M=('base', InstMemBase, int),
            r=('offreg', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              offreg: int,
              base=InstMemBase.MAIN,
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_offreg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if offreg >= 16:
            raise ValueError(f'reg {offreg} out of range')
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} [{p.M.name.lower()}+r{p.r}]'


class vm_if_reg_COND_reg_off(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [rM {+offset}] {then}
        where:
            dtype default = u64
            COND = >, >=, <, <=, ==, !=
            THEN is optional keyword

    C0TcS2Ra aaaaaaaa
    """
    CODE_TYPE = 'C0???2'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS2Ra aaaaaaaa'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            R=('basereg', int, int),
            a=('offset', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              basereg: int,
              offset: int,    # uint36
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_reg_off:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if basereg >= 16:
            raise ValueError(f'reg {basereg} out of range')
        if (offset >> self.format.count('a') * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} [r{p.R}+{p.a:#x}]'


class vm_if_reg_COND_reg_reg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [rBase + rOffset] {then}
        where:
            dtype default = u64
    """
    CODE_TYPE = 'C0???3'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS3Rr'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            R=('basereg', int, int),
            r=('offreg', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              basereg: int,
              offreg: int,
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_reg_reg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if basereg >= 16:
            raise ValueError(f'reg {basereg} out of range')
        if offreg >= 16:
            raise ValueError(f'reg {offreg} out of range')
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} [r{p.R}+r{p.r}]'


class vm_if_reg_COND_imm(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND value {then}
        where:
            dtype default = u64
    """
    CODE_TYPE = 'C0???400'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS400 VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            V=('value', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              value: str | int | float,
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_imm:
        # fix arguments
        if not width:
            width = InstDataType.u32
        width = InstDataType(width)
        value = reinterpret_cast_to_int(value, width)
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} {p.V:#x}'


class vm_if_reg_COND_reg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND rM {then}
        where:
            dtype default = u64
    """
    CODE_TYPE = 'C0???50'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS5X0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            c=('cond', InstCondition, int),
            S=('reg', int, int),
            X=('reg_other', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              cond: InstCondition,
              reg_other: int,
              width=InstDataType.u64,
              ) -> vm_if_reg_COND_reg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if reg_other >= 16:
            raise ValueError(f'reg {reg_other} out of range')
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        return f'if {p.T} r{p.S} {p.c} r{p.X}'


class vm_save_restore(vm_inst):
    """
    ### Syntax
    save[i] = rN
    rN = save[i]
    save[i] = 0
    rN = 0
        where:
            i is save index, N is reg id
            i < 16 and N < 16
        example:
            save[3] = r3

    ### Code Type 0xC1: Save or Restore Register
    Code type 0xC1 performs saving or restoring of registers.

    #### Encoding
    `C10D0Sx0`

    + D: Destination index.
    + S: Source index.
    + x: Operand Type, see below.

    #### Operand Type
    + 0: Restore register
    + 1: Save register
    + 2: Clear saved value
    + 3: Clear register
    """
    CODE_TYPE = 'C1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C10D0Sx0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            D=('dest', int, int),
            S=('src', int, int),
            x=('op', InstSaveRestoreRegOp, int),
        )
        self._load_format()

    def build(self,
              dest: int,
              op: InstSaveRestoreRegOp,
              src: int,
              ) -> vm_save_restore:
        # verify args
        if dest >= 16:
            raise ValueError(f'reg {dest} out of range')
        if src >= 16:
            raise ValueError(f'reg {src} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.x == InstSaveRestoreRegOp.SAVE:
            return f'save[{p.D}] = r{p.S}'
        elif p.x == InstSaveRestoreRegOp.RESTORE:
            return f'r{p.D} = save[{p.S}]'
        elif p.x == InstSaveRestoreRegOp.CLEAR:
            return f'save[{p.D}] = 0'
        elif p.x == InstSaveRestoreRegOp.REG_ZERO:
            return f'r{p.D} = 0'


class vm_save_restore_mask(vm_inst):
    """
    ### Syntax
    save rA, rB, ..., rN
    restore rA, rB, ..., rN
    save[i,j,...k] = 0
    rA, rB, ..., rN = 0
        where:
            i,..k are save indicies, A,..N are reg ids
        example:
            save r3, r4, r5
            restore r3, r4, r5
            save[3,4,5] = 0
            r0, r1, r2 = 0

    ### Code Type 0xC2: Save or Restore Register with Mask
    Code type 0xC2 performs saving or restoring of multiple registers using a bitmask.

    #### Encoding
    `C2x0XXXX`

    + x: Operand Type, see below.
    + X: 16-bit bitmask, bit i == save or restore register i.

    #### Operand Type
    + 0: Restore register
    + 1: Save register
    + 2: Clear saved value
    + 3: Clear register
    """
    CODE_TYPE = 'c2'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C2x0XXXX'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            x=('op', InstSaveRestoreRegOp, int),
            X=('mask', int, int),
        )
        self._load_format()

    def build(self,
              op: InstSaveRestoreRegOp,
              indicies: str | list[int],
              ) -> vm_save_restore_mask:
        # verify args
        mask = 0
        if isinstance(indicies, str):
            for index in indicies.split(','):
                index = index.strip().lstrip('r')
                assert index.isdigit()
                index = int(index)
                assert 0 <= index < 16
                mask |= 1 << index
        elif isinstance(indicies, list):
            for index in indicies:
                assert 0 <= index < 16
                mask |= 1 << index
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        regs = [f'r{i}' for i in range(0, 16) if p.X & (1 << i)]
        indices = [f'{i}' for i in range(0, 16) if p.X & (1 << i)]
        if p.x == InstSaveRestoreRegOp.SAVE:
            return f'save {", ".join(regs)}'
        elif p.x == InstSaveRestoreRegOp.RESTORE:
            return f'restore {", ".join(regs)}'
        elif p.x == InstSaveRestoreRegOp.CLEAR:
            return f'save[{", ".join(indices)}] = 0'
        elif p.x == InstSaveRestoreRegOp.REG_ZERO:
            return f'{", ".join(regs)} = 0'


class vm_rw_static_reg(vm_inst):
    """
    ### Syntax
    rN = static[i]  # when i < 0x80
    static[i] = rN  # when i >= 0x80

    ### Code Type 0xC3: Read or Write Static Register
    Code type 0xC3 reads or writes a static register with a given register.

    #### Encoding
    `C3000XXx`

    + XX: Static register index, 0x00 to 0x7F for reading or 0x80 to 0xFF for writing.
    + x: Register index.
    """

    CODE_NAME = 'static'
    CODE_TYPE = 'c3'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C3000XXx'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            X=('static_reg', int, int),
            x=('reg', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              static_reg: int,
              ) -> vm_rw_static_reg:
        # verify args
        if reg >= 16 or reg < 0:
            raise ValueError(f'reg {reg} out of range')
        if static_reg > 0xFF or static_reg < 0:
            raise ValueError(f'static_reg {static_reg} out of range')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        return self

    def asm(self) -> str:
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.X > 80:
            return f'static[{p.X}] = r{p.x}'
        else:
            return f'r{p.x} = static[{p.X}]'


class vm_pause(vm_inst):
    """
    ### Syntax
    pause

    ### Code Type 0xFF0: Pause Process
    Code type 0xFF0 pauses the current process.

    #### Encoding
    `FF0?????`
    """
    CODE_NAME = 'pause'
    CODE_TYPE = 'ff0'

    def build(self) -> vm_pause:
        return self

    def asm(self) -> str:
        return 'FF000000'

    def dism(self) -> str:
        return self.CODE_NAME


class vm_resume(vm_inst):
    """
    ### Syntax
    resume

    ### Code Type 0xFF1: Resume Process
    Code type 0xFF1 resumes the current process.

    #### Encoding
    `FF1?????`
    """
    CODE_NAME = 'resume'
    CODE_TYPE = 'ff1'

    def build(self) -> vm_resume:
        return self

    def asm(self) -> str:
        return 'FF100000'

    def dism(self) -> str:
        return self.CODE_NAME


class _vm_log(vm_inst):
    """
    ### Syntax
    log ID {dtype} [base {+offset}]
    log ID {dtype} [base + rN]
    log ID {dtype} [rM {+offset}]
    log ID {dtype} [rM + rN]
    log ID {dtype} [rM]
        where:
            0 <= ID <= 0xF

    Code type 0xFFF writes a debug log to the SD card under the folder `/atmosphere/cheat_vm_logs/`.

    #### Encoding
    ```
    FFFTIX##
    FFFTI0Ma aaaaaaaa
    FFFTI1Mr
    FFFTI2Ra aaaaaaaa
    FFFTI3Rr
    FFFTI4X0
    ```

    + T: Width of memory write (1, 2, 4, or 8 bytes).
    + I: Log id.
    + X: Operand Type, see below.
    + M: Memory Type (operand types 0 and 1).
    + R: Address Register (operand types 2 and 3).
    + a: Relative Address (operand types 0 and 2).
    + r: Offset Register (operand types 1 and 3).
    + X: Value Register (operand type 4).

    #### Operand Type
    + 0: Memory Base + Relative Offset
    + 1: Memory Base + Offset Register
    + 2: Register + Relative Offset
    + 3: Register + Offset Register
    + 4: Register Value
    """
    CODE_NAME = 'log'
    CODE_TYPE = 'fff'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'FFFTIXmn'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T=('width', InstDataType, InstDataType_to_int),
            I=('id', int, int),
            X=('type', InstDebugType, int),
            m=('mem_or_reg', int, int),
            n=('value_or_reg', int, int),
        )
        self._load_format()

    def build(self,
              id: int,
              type: InstDebugType,
              mem_or_reg: int | InstMemBase,
              value_or_reg: int,
              width=InstDataType.u64,
              ) -> _vm_log:
        # verify args
        if id >= 16:
            raise ValueError(f'reg {id} out of range')
        if type in [InstDebugType.MEMBASE_OFF, InstDebugType.MEMBASE_REG]:
            mem_or_reg = InstMemBase(mem_or_reg)    # verify
        elif type in [InstDebugType.REG_OFF, InstDebugType.REG_OFFREG, InstDebugType.REG]:
            assert mem_or_reg < 16, f'reg {mem_or_reg} out of range'
        else:
            assert False, f'unknown log type {type}'
        if not width:
            width = InstDataType.u64
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
                                 self.binding[sym][1](   # run decoder on input value
                                     local_vars[self.binding[sym][0]]
                                 ) for sym in self.binding})
        # fix n width
        if self.prop.X in [0, 2]:
            self.format = 'FFFTIXmn nnnnnnnn'
            self.format_info['n'] = (7, 9)
        return self

    def asm(self) -> str:
        # fix n width.
        if self.prop.X in [0, 2]:
            self.format = 'FFFTIXmn nnnnnnnn'
            self.format_info['n'] = (7, 9)
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.X == InstDebugType.MEMBASE_OFF:
            return f'{self.CODE_NAME} {p.I} {p.T} [{InstMemBase(p.m).name.lower()} + {p.n}]'
        elif p.X == InstDebugType.MEMBASE_REG:
            return f'{self.CODE_NAME} {p.I} {p.T} [{InstMemBase(p.m).name.lower()} + r{p.n}]'
        elif p.X == InstDebugType.REG_OFF:
            return f'{self.CODE_NAME} {p.I} {p.T} [r{p.m} + {p.n}]'
        elif p.X == InstDebugType.REG_OFFREG:
            return f'{self.CODE_NAME} {p.I} {p.T} [r{p.m} + r{p.n}]'
        elif p.X == InstDebugType.REG:
            return f'{self.CODE_NAME} {p.I} {p.T} [r{p.m}]'


class vm_log_off(_vm_log):
    CODE_TYPE = 'fff??0'

    def build(self, id: int, offset: int, base=InstMemBase.MAIN, width=InstDataType.u64) -> vm_log_off:
        return super().build(id, InstDebugType.MEMBASE_OFF, base, offset, width)


class vm_log_offreg(_vm_log):
    CODE_TYPE = 'fff??1'

    def build(self, id: int, offreg: int, base=InstMemBase.MAIN, width=InstDataType.u64) -> vm_log_off:
        return super().build(id, InstDebugType.MEMBASE_REG, base, offreg, width)


class vm_log_reg_off(_vm_log):
    CODE_TYPE = 'fff??2'

    def build(self, id: int, reg: int, offset: int, width=InstDataType.u64) -> vm_log_off:
        return super().build(id, InstDebugType.REG_OFF, reg, offset, width)


class vm_log_reg_offreg(_vm_log):
    CODE_TYPE = 'fff??3'

    def build(self, id: int, reg: int, offreg: int, width=InstDataType.u64) -> vm_log_off:
        return super().build(id, InstDebugType.REG_OFFREG, reg, offreg, width)


class vm_log_reg(_vm_log):
    CODE_TYPE = 'fff??4'

    def build(self, id: int, reg: int, width=InstDataType.u64) -> vm_log_off:
        return super().build(id, InstDebugType.REG, reg, 0, width)
