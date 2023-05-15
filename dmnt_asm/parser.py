#!/usr/bin/python3
#-*- coding:utf-8 -*-

from .instructions import vm_inst_dism, vm_inst

class CheatParser:
    def __init__(self) -> None:
        self.entries = []
    
    def parse(self, content: str, append: bool = False) -> bool:
        all_ok = True
        if not append:
            self.entries.clear()
        cur_entry_name = None
        cur_entry_block = []
        lines = content.splitlines()
        for line_number in range(0, len(lines)):
            line = lines[line_number]
            line = line.strip()
            try:
                if not line:
                    continue
                if line.startswith('#'):
                    # unofficial, comment syntax
                    continue
                elif line.startswith('{'):
                    # master code block
                    if not line.endswith('}'):
                        raise SyntaxError(f"line #{line_number}, {line}: invalid master code declaration, missing }}")
                    # finish previous entry
                    if cur_entry_name or cur_entry_block:
                        self.entries.append((cur_entry_name, cur_entry_block))
                    cur_entry_name = line
                    cur_entry_block = []
                    pass
                elif line.startswith('['):
                    # entry block
                    if not line.endswith(']'):
                        raise SyntaxError(f"line #{line_number}, {line}: invalid entry declaration, missing ]")
                    # finish previous entry
                    if cur_entry_name or cur_entry_block:
                        self.entries.append((cur_entry_name, cur_entry_block))
                    cur_entry_name = line
                    cur_entry_block = []
                    pass
                elif cur_entry_name:
                    inst: str = line
                    try:
                        inst : vm_inst = vm_inst_dism(line)
                    except Exception as e:                
                        all_ok = False
                        print(f"failed to dism Line.{line_number}, {line}: {e}")
                    cur_entry_block.append(inst)
                else:
                    raise SyntaxError(f"Line #{line_number}, {line}: code does not belong to an entry.")
            except Exception as e:
                all_ok = False
                print(f"failed to dism Line.{line_number}, {line}: {e}")
        return all_ok
    
    def dumps(self, indent = 0) -> str:
        result = ''
        for name, insts in self.entries:
            cur_indent = 0
            result += name + '\n'
            for _inst in insts:
                if isinstance(_inst, str):
                    result += _inst + '\n'
                else:
                    inst: vm_inst = _inst
                    inst_type_name = inst.__class__.__name__
                    if inst_type_name == 'vm_else':
                        cur_indent -= indent
                    if inst_type_name.startswith('vm_end'):
                        cur_indent -= indent
                    result += ' ' * cur_indent + inst.dism() + '\n'
                    if inst_type_name.startswith('vm_if') or inst_type_name == 'vm_loop':
                        cur_indent += indent
            result += '\n'
        return result
