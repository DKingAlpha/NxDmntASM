#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import annotations
import re
import string
from abc import ABC, abstractmethod
from collections import OrderedDict

from .constants import *

STRICT_MODE = False

class _Properties(OrderedDict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = OrderedDict.get
    __setattr__ = OrderedDict.__setitem__
    __delattr__ = OrderedDict.__delitem__

def _int_from_hex(hexstr: str) -> int:
    return int(hexstr, 16)

def _aob_match(code_type: int|str, mc: str) -> bool:
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
            if '(V' in self.format and k == 'V':
                if 'T' in self.prop and self.prop.T == InstWidth.X:
                    real_width = 16
            raw[pos:pos+real_width] = list(f'{k_value:0{real_width}X}')
        
        # normalize
        self.raw = ''.join(raw)
        self.code = self._normalize_mc(self.raw)
        assert self.code
        return self.code

    def _load_format(self) -> None:
        format = self._gen_shortes_format() # it extends automatically
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
                if 'T' in self.prop and self.prop.T == InstWidth.X:
                    real_width = 16
            if start_pos + real_width > len(code):
                return False
            k_value = _int_from_hex(code[start_pos : start_pos + real_width])
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
                ins: vm_inst  = vm_cls()
                if ins.dism_mc_line_to_prop(mc_line):
                    return ins
    raise NotImplementedError(f'invalid instruction: {mc_line}')

def vm_inst_asm(asm_line: str) -> vm_inst:
    raise NotImplementedError(f'invalid instruction: {asm_line}')


class vm_nop(vm_inst):
    """
    peopel write 00000000 .... in credit section
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
    store {p.T} [base+offset{+rN}] = value
        where:
            base = main/heap/alias/aslr
            offset <= 0xFF,FFFFFFFF
            dtype = u8/u16/u32/u64/i8.../i64. default = u32
            offreg = 0 .. 16. default = 0
        example:
            StOre [maIn + 0x100 + reg2] = i8 -18

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
    CODE_NAME = 'store'
    CODE_TYPE = '0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '0TMR00AA AAAAAAAA VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            M = ('base', InstMemBase, int),
            R = ('offreg', int, int),
            A = ('offset', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            offset: int,    # uint40
            value: int,     # <= uintmax_of(width)
            offreg = 0,
            base = InstMemBase.MAIN,
            width = InstWidth.W,
        ) -> vm_store_imm:
        # verify args
        if (offreg >= 16):
            raise ValueError(f'reg {offreg} out of range')
        if (offset >> 10 * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        if value >= (1 << (int(InstWidth(width))*8)):
            raise ValueError(f'value {value} overflows width {width}')
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
        return f'{self.CODE_NAME} {p.T} [{p.M.name.lower()} + {p.A:#x} + r{p.R}], {int_to_dtype_hexstr(p.V, str(p.T), True)}'


class vm_if_off_COND_imm(vm_inst):
    """
    ### Syntax
    if {dtype} [base+offset] COND value {then}
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
    CODE_NAME = 'if'
    CODE_TYPE = '1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '1TMC00AA AAAAAAAA VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            M = ('base', InstMemBase, int),
            C = ('cond', InstCondition, int),
            A = ('offset', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            offset: int,    # uint40
            cond: InstCondition,
            value: int,     # <= uintmax_of(width)
            base = InstMemBase.MAIN,
            width = InstWidth.W,
        ) -> vm_if_off_COND_imm:
        # verify args
        if (offset >> self.format.count('A') * 4) != 0:
            raise ValueError(f'offset {offset} larger than 40 bits')
        if value >= (1 << (int(InstWidth(width))*8)):
            raise ValueError(f'value {value} overflows width {width}')
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
        return f'{self.CODE_NAME} {p.T} [{p.M.name.lower()} + {p.A:#x}] {p.C} {int_to_dtype_hexstr(p.V, str(p.T), True)}'


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
            R = ('reg', int, int),
            V = ('count', int, int),
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
            R = ('reg', int, int),
        )
        self._load_format()

    def build(self,
            reg: int
        ) -> vm_endloop:
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
        return f'{self.CODE_NAME} r{self.prop.R}'


class vm_move_reg(vm_inst):
    """
    ### Syntax
    set rN = value

    ### Code Type 0x4: Load Register with Static Value
    Code type 0x4 allows setting a register to a constant value.

    #### Encoding
    `400R0000 VVVVVVVV VVVVVVVV`

    + R: Register to use.
    + V: Value to load.
    """
    CODE_NAME = 'set'
    CODE_TYPE = '4'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '400R0000 VVVVVVVV VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            R = ('reg', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            value: int,
        ) -> vm_move_reg:
        # verify args
        if (reg >= 16):
            raise ValueError(f'reg {reg} out of range')
        if (value >> self.format.count('V') * 4) != 0:
            raise ValueError(f'value {value} overflow')
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
        return f'{self.CODE_NAME} r{self.prop.R} = {self.prop.V}'
    

class vm_load(vm_inst):
    """
    ### Syntax
    load {p.T} rN = [base + offset]
    load {p.T} rN = [rN + offset]

    Note: load {p.T} rA = [rB + offset] is unsupported

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
    CODE_NAME = 'load'
    CODE_TYPE = '5'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '5TMRS0AA AAAAAAAA'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            M = ('base', InstMemBase, int),
            R = ('reg', int, int),
            A = ('offset', int, int),
            S = ('self_deref', bool, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            offset: int,    # uint40
            self_deref: bool,
            base = InstMemBase.MAIN,
            width = InstWidth.W,
        ) -> vm_load:
        # verify args
        if (reg >= 16):
            raise ValueError(f'reg {reg} out of range')
        if (offset >> self.format.count('A') * 4) != 0:
            raise ValueError(f'offset {offset} overflow')
        # bind args
        local_vars = locals()
        self.prop = _Properties({sym:
            self.binding[sym][1](   # run decoder on input value
                local_vars[self.binding[sym][0]]
            ) for sym in self.binding})
        return self

    def asm(self) -> str:
        if self.prop.S:
            self.prop.M = InstMemBase(0)    # manually set 0 to comply with format
        return super()._asm()

    def dism(self) -> str:
        p = self.prop
        if p.S:
            return f'{self.CODE_NAME} {str(p.T)} r{p.R} = [r{p.R} + {p.A:#x}]'
        else:
            return f'{self.CODE_NAME} {str(p.T)} r{p.R} = [{p.M.name.lower()} + {p.A:#x}]'


class vm_store_reg_imm(vm_inst):
    """
    ### Syntax
    store {p.T} [rN{++} {+ rN}] = value
        where:
            rN++ means rN+=width after operation
        example:
            store i32 [r0++ + r1] = 0x12345678
            store i32 [r0 + r1] = 0x12345678
            store i32 [r0++] = 0x12345678
            
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
    CODE_NAME = 'store'
    CODE_TYPE = '6'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '6T0RIor0 VVVVVVVV VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            R = ('basereg', int, int),
            I = ('basereg_inc', bool, int),
            o = ('off_by_reg', bool, int),
            r = ('offreg', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            basereg: int,
            value: int,
            basereg_inc: bool = False,
            off_by_reg: bool = False,
            offreg: int = 0,
            width = InstWidth.W,
        ) -> vm_store_reg_imm:
        # verify args
        if (offreg >= 16):
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
        return f'{self.CODE_NAME} {p.T} [{addr_reg}] = {p.V:#x}'


class vm_legacy_set_imm(vm_inst):
    """
    ### Syntax
    set {p.T} rN OP= value
        where:
            OP is one of +, -, *, <<, >>
        example:
            set r0 += 0x12345678
    
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
    CODE_NAME = 'set'
    CODE_TYPE = '7'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '7T0RC000 VVVVVVVV'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            R = ('reg', int, int),
            C = ('op', InstArithmetic, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            op: InstArithmetic,
            value: int,
            width = InstWidth.W,
        ) -> vm_store_reg_imm:
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
        return f'{self.CODE_NAME} {p.T} r{p.R} {p.C}= {p.V:#x}'


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
    CODE_NAME = 'if key'
    CODE_TYPE = '8'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '8kkkkkkk'

        def key_decoder(keys: int | str | InstKeyName | list[int|str|InstKeyName]) -> InstKeyFlag:
            keycomb = InstKeyFlag(0)
            def _parse_key(key: int|str|InstKeyName):
                result = InstKeyFlag(0)
                if isinstance(key, str):
                    if '|' in key:
                        for k in key.split('|'):
                            result |= InstKeyName(k.strip()).value
                    else:
                        result |= InstKeyName(key.strip()).value
                elif isinstance(key, int):
                    result |=  key
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
            k = ('keys', key_decoder, key_encoder),
        )
        self._load_format()

    def build(self, keys : str|list[str|InstKeyName]) -> vm_if_off_COND_imm:
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
        return f'{self.CODE_NAME} {p.k.name}'


class vm_set_reg_reg(vm_inst):
    """
    ### Syntax
    set {p.T} rD = rS OP rT
    set {p.T} rD = rS
    set {p.T} rD = !rS
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
    CODE_NAME = 'set'
    CODE_TYPE = '9????0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '9TCRS0s0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            C = ('op', InstArithmetic, int),
            R = ('dest', int, int),
            S = ('src1', int, int),
            s = ('src2', int, int),
        )
        self._load_format()

    def build(self,
            dest: int,
            src1: int,
            op: InstArithmetic,
            src2: int,
            width = InstWidth.W,
        ) -> vm_store_reg_imm:
        # bind args
        if isinstance(op, str) and op != '=' and op.endswith('='):
            op = InstArithmetic(op[:-1])
        local_vars = locals()
        for sym in ('dest', 'src1', 'src2'):
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
            return f'{self.CODE_NAME} {p.T} r{p.R} = r{p.S}'
        elif p.C == InstArithmetic.LOGICAL_NOT:
            return f'{self.CODE_NAME} {p.T} r{p.R} = !r{p.S}'
        return f'{self.CODE_NAME} {p.T} r{p.R} = r{p.S} {p.C} r{p.s}'


class vm_set_reg_imm(vm_inst):
    """
    ### Syntax
    set {p.T} rD = rS OP value
    set {p.T} rD = rS
    set {p.T} rD = !rS
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
    CODE_NAME = 'set'
    CODE_TYPE = '9????1'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = '9TCRS100 VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            C = ('op', InstArithmetic, int),
            R = ('dest', int, int),
            S = ('src', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            dest: int,
            src: int,
            op: InstArithmetic,
            value: int,
            width = InstWidth.W,
        ) -> vm_set_reg_imm:
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
            return f'{self.CODE_NAME} {p.T} r{p.R} = r{p.S}'
        elif p.C == InstArithmetic.LOGICAL_NOT:
            return f'{self.CODE_NAME} {p.T} r{p.R} = !r{p.S}'
        return f'{self.CODE_NAME} {p.T} r{p.R} = r{p.S} {p.C} {int_to_dtype_hexstr(p.V, str(p.T), True)}'


class vm_store_reg(vm_inst):
    """
    ### Syntax
    store {p.T} [rM{++} {+offset {+rN}}] = rS
    store {p.T} [BASE + {+offset {+rM{++}}}] = rS
        where:
            rM ++ means rM +=width after operation
        example:
            store u32 [r2++ ]
            store u32 [r2++ + 2 + r3] = r4


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
    CODE_NAME = 'store'
    CODE_TYPE = 'A'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'ATSRIOxa (aaaaaaaa)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            S = ('srcreg', int, int),
            R = ('basereg', int, int),
            I = ('basereg_inc', bool, int),
            O = ('offset_type', InstOffsetType, int),
            x = ('offreg_or_membase', int, int),
            a = ('offset', int, int),
        )
        self._load_format()

    def build(self,
            offset_type: InstOffsetType,
            basereg: int,
            basereg_inc: bool,
            offset: int,
            offreg_or_membase: int | InstMemBase,
            srcreg: int,
            width = InstWidth.W,
        ) -> vm_store_reg:
        # verify args
        if srcreg >= 16 or basereg >= 16 or (int(offset_type) <= 1 and offreg_or_membase >= 16):
            raise ValueError(f'reg out of range')
        if (offset >> (self.format.count('a')) * 4) != 0:
            raise ValueError(f'offset {offset} overflow')
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
                addr_expr += f' + {p.a:#x} + r{p.x}'
            else:
                assert False, f'invalid offset type {p.O}'
        return f'{self.CODE_NAME} {p.T} [{addr_expr}] = r{p.S}'


class vm_if_reg_COND_off(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [base+offset] {then}
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
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???0'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS0Ma aaaaaaaa'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            M = ('base', InstMemBase, int),
            a = ('offset', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            offset: int,    # uint36
            base = InstMemBase.MAIN,
            width = InstWidth.X,
        ) -> vm_if_reg_COND_off:
        # verify args
        if (offset >> self.format.count('a') * 4) != 0:
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} [{p.M.name.lower()}+{p.a:#x}]'


class vm_if_reg_COND_offreg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [base+rM] {then}
        where:
            dtype default = u64
    """
    
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???1'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS1Mr'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            M = ('base', InstMemBase, int),
            r = ('offreg', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            offreg: int,
            base = InstMemBase.MAIN,
            width = InstWidth.X,
        ) -> vm_if_reg_COND_offreg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if offreg >= 16:
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} [{p.M.name.lower()}+r{p.r}]'


class vm_if_reg_COND_reg_off(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [rM+offset] {then}
        where:
            dtype default = u64
            COND = >, >=, <, <=, ==, !=
            THEN is optional keyword

    C0TcS2Ra aaaaaaaa
    """
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???2'

    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS2Ra aaaaaaaa'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            R = ('basereg', int, int),
            a = ('offset', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            basereg: int,
            offset: int,    # uint36
            width = InstWidth.X,
        ) -> vm_if_reg_COND_reg_off:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if basereg >= 16:
            raise ValueError(f'reg {basereg} out of range')
        if (offset >> self.format.count('a') * 4) != 0:
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} [r{p.R}+{p.a:#x}]'


class vm_if_reg_COND_reg_reg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND [rBase+rOffset] {then}
        where:
            dtype default = u64
    """
    
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???3'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS3Rr'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            R = ('basereg', int, int),
            r = ('offreg', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            basereg: int,
            offreg: int,
            width = InstWidth.X,
        ) -> vm_if_reg_COND_reg_reg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if basereg >= 16:
            raise ValueError(f'reg {basereg} out of range')
        if offreg >= 16:
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} [r{p.R}+r{p.r}]'


class vm_if_reg_COND_imm(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND value {then}
        where:
            dtype default = u64
    """
    
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???400'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS400 VVVVVVVV (VVVVVVVV)'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            V = ('value', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            value: int,
            width = InstWidth.X,
        ) -> vm_if_reg_COND_imm:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if value >= (1 << (int(InstWidth(width))*8)):
            raise ValueError(f'value {value} overflows width {width}')
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} {p.V:#x}'


class vm_if_reg_COND_reg(vm_inst):
    """
    ### Syntax
    if {dtype} rN COND rM {then}
        where:
            dtype default = u64
    """
    
    CODE_NAME = 'if'
    CODE_TYPE = 'C0???50'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C0TcS5X0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            T = ('width', InstWidth, int),
            c = ('cond', InstCondition, int),
            S = ('reg', int, int),
            X = ('reg_other', int, int),
        )
        self._load_format()

    def build(self,
            reg: int,
            cond: InstCondition,
            reg_other: int,
            width = InstWidth.X,
        ) -> vm_if_reg_COND_reg:
        # verify args
        if reg >= 16:
            raise ValueError(f'reg {reg} out of range')
        if reg_other >= 16:
            raise ValueError(f'reg {reg_other} out of range')
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
        return f'{self.CODE_NAME} {p.T} r{p.S} {p.c} r{p.X}'


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
    CODE_NAME = 'save_restore'
    CODE_TYPE = 'C1'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C10D0Sx0'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            D = ('dest', int, int),
            S = ('src', int, int),
            x = ('op', InstSaveRestoreRegOp, int),
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
    CODE_NAME = 'save_restore_mask'
    CODE_TYPE = 'c2'
    
    def __init__(self) -> None:
        super().__init__()
        # setup
        self.format = 'C2x0XXXX'
        self.binding = _Properties(
            # sym: (name, decoder, encoder)
            x = ('op', InstSaveRestoreRegOp, int),
            X = ('mask', int, int),
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
                index = index.strip()
                assert index.startswith('r')
                assert index[1:].isdigit()
                index = int(index[1:])
                assert index < 16
                mask |= 1 << index
        elif isinstance(indicies, list):
            for index in indicies:
                assert index < 16
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
    rN = static[i]
    static[i] = rN
        where:
            i < 0x80

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
            X = ('static_reg', int, int),
            x = ('reg', int, int),
        )
        self._load_format()

    def build(self,
              reg: int,
              static_reg: int,
        ) -> vm_rw_static_reg:
        # verify args
        if reg >= 16:
            assert f'reg {reg} out of range'
        if static_reg > 0xFF:
            assert f'static_reg {static_reg} out of range'
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
    log ID {dtype} [base + off]
    log ID {dtype} [base + rN]
    log ID {dtype} [rM + offset]
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
            T = ('width', InstWidth, int),
            I = ('id', int, int),
            X = ('type', InstDebugType, int),
            m = ('mem_or_reg', int, int),
            n = ('value_or_reg', int, int),
        )
        self._load_format()

    def build(self,
            id: int,
            type: InstDebugType,
            mem_or_reg: int | InstMemBase,
            value_or_reg: int,
            width = InstWidth.X,
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
            return f'{self.CODE_NAME} {p.I} {p.T} [r{p.n}]'


class vm_log_off(_vm_log):
    CODE_TYPE = 'fff??0'
    def build(self, id: int, offset: int, base = InstMemBase.MAIN, width=InstWidth.X) -> vm_log_off:
        return super().build(id, InstDebugType.MEMBASE_OFF, base, offset, width)

class vm_log_offreg(_vm_log):
    CODE_TYPE = 'fff??1'
    def build(self, id: int, offreg: int, base = InstMemBase.MAIN, width=InstWidth.X) -> vm_log_off:
        return super().build(id, InstDebugType.MEMBASE_REG, base, offreg, width)

class vm_log_reg_off(_vm_log):
    CODE_TYPE = 'fff??2'
    def build(self, id: int, reg: int, offset: int, width=InstWidth.X) -> vm_log_off:
        return super().build(id, InstDebugType.REG_OFF, reg, offset, width)

class vm_log_reg_offreg(_vm_log):
    CODE_TYPE = 'fff??3'
    def build(self, id: int, reg: int, offreg: int, width=InstWidth.X) -> vm_log_off:
        return super().build(id, InstDebugType.REG_OFFREG, reg, offreg, width)

class vm_log_reg(_vm_log):
    CODE_TYPE = 'fff??4'
    def build(self, id: int, reg: int, width=InstWidth.X) -> vm_log_off:
        return super().build(id, InstDebugType.REG, reg, 0, width)

