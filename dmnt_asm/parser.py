#!/usr/bin/python3
#-*- coding:utf-8 -*-
from __future__ import annotations
from .instructions import vm_inst_dism, vm_inst_asm, vm_inst

class CheatParser:
    def __init__(self, err_handler = None) -> None:
        self.entries = []
        self.err_handler = err_handler if err_handler else (lambda *args,**kwargs : None)
    
    def load(self, content: str, append: bool = False) -> bool:
        all_ok = True
        if not append:
            self.entries.clear()
        # group by entry name
        cur_entry_name = ''
        cur_entry_block = []
        lines = content.splitlines()
        for line_number in range(0, len(lines)):
            orig_line = lines[line_number]
            line = orig_line.strip()
            sect_begins = ['{', '[']
            sect_ends = ['}', ']']
            found_sect_declaration = False
            for i in range(0, len(sect_begins)):
                sect_begin = sect_begins[i]
                sect_end = sect_ends[i]
                if line.startswith(sect_begin):
                    if not line.endswith(sect_end):
                        self.err_handler(f"line #{line_number}, {line}: invalid entry declaration, missing {sect_end}")
                    # finish previous entry
                    if cur_entry_name or cur_entry_block:
                        self.entries.append((cur_entry_name, cur_entry_block))
                    cur_entry_name = line
                    cur_entry_block = []
                    found_sect_declaration = True
                    break
            if found_sect_declaration:
                continue
            cur_entry_block.append(orig_line)
        if cur_entry_name or cur_entry_block:
            self.entries.append((cur_entry_name, cur_entry_block))

    def asm(self, indent = 0, strip_code = False, strip_comment = False) -> str:
        self._do_dism_or_asm(vm_inst_asm)
        return self._dumps(True, indent, strip_code, strip_comment)

    def dism(self, indent = 0) -> str:
        self._do_dism_or_asm(vm_inst_dism)
        return self._dumps(False, indent, False, False)
    
    def _dumps(self, is_asm, indent, strip_code, strip_comment) -> str:
        result = ''
        for name, insts in self.entries:
            cur_indent = 0
            result += name + '\n'
            for _inst in insts:
                if isinstance(_inst, str):                
                    if strip_comment and _inst.startswith('#'):
                        continue
                    result += _inst + '\n'
                else:
                    inst: vm_inst = _inst
                    inst_type_name = inst.__class__.__name__
                    if inst_type_name == 'vm_else':
                        cur_indent -= indent
                    if inst_type_name.startswith('vm_end'):
                        cur_indent -= indent
                    converted_line = inst.asm() if is_asm else inst.dism()
                    converted_line = ' ' * cur_indent + converted_line + '\n'
                    if strip_code:
                        converted_line = converted_line.lstrip()
                    result += converted_line
                    if inst_type_name.startswith('vm_if') or inst_type_name == 'vm_loop':
                        cur_indent += indent
        return result

    def _do_dism_or_asm(self, code_handler: callable):
        line_no = 0
        for entry_name, entry_block in self.entries:
            line_no += 1
            for code_no in range(0, len(entry_block)):
                line_no += 1
                orig_code: str = entry_block[code_no]
                code = orig_code.strip()
                if not code:
                    continue
                if code.startswith('#'):   # dialect, for comment.
                    continue
                try:
                    inst = code_handler(code)
                    entry_block[code_no] = inst
                except Exception as e:
                    self.err_handler(f"line #{line_no}, entry {entry_name}: failed to handle `{code}`: {e}")
                    all_ok = False
