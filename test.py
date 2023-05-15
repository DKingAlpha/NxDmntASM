#!/usr/bin/python3
#-*- coding:utf-8 -*-

from pathlib import Path
from pprint import pprint
from dmnt_asm.parser import *
from dmnt_asm.instructions import *

def test_ins(inst: vm_inst):
    print('-' * 32)
    mc_inst = inst.asm()
    dism_inst = inst.dism()
    # print(mc_inst, dism_inst)
    d_inst = vm_inst_dism(mc_inst)
    d_mc_inst = d_inst.asm()
    d_dism_inst = d_inst.dism()
    assert(str(inst) == str(d_inst))
    print(inst)

def test_parser():
    titles = Path(r'......\switch\EdiZon\cheats').rglob('cheats\\*.txt')
    for cheat_txt in titles:
        cheat_asm = cheat_txt.parent / (cheat_txt.stem + '.asm')
        parser = CheatParser()
        content = cheat_txt.read_text(encoding='utf-8', errors='backslashreplace')
        all_ok = parser.parse(content)
        cheat_asm.write_text(parser.dumps(indent=4), encoding='utf-8', errors='backslashreplace')
        #print(f"ALL_OK = {all_ok}: {cheat_asm}")
        if not all_ok:
            print(f"failure in parsing {cheat_txt} -> {cheat_asm}")

def test_error():
    errors = [
        '00000000 00000000 00000000',
    ]
    for err in errors:
        test_ins(vm_inst_dism(err))

def test_api():
    test_ins(vm_store_imm().build(0x5678aabbcc, 0x1234, 4, 'heap', 'u64'))
    test_ins(vm_if_off_COND_imm().build(0x1234, '>', 0x5678, 'heap', 'i32'))
    test_ins(vm_else().build())
    test_ins(vm_endif().build())
    test_ins(vm_loop().build(2, 10))
    test_ins(vm_endloop().build(2))
    test_ins(vm_move_reg().build(1, 0x1234))
    test_ins(vm_load().build(1, 0x1234, False, 'heap', 'u32'))
    test_ins(vm_store_reg_imm().build(1, 0x1234, True))
    test_ins(vm_legacy_set_imm().build(1, '+=', 0x1234, 'u64'))
    test_ins(vm_if_key().build('L | X'))
    test_ins(vm_set_reg_reg().build(1, 2, '+=', 2, 'u64'))
    test_ins(vm_set_reg_imm().build(1, 2, '+=', 0x1234, 'u16'))
    test_ins(vm_store_reg().build(InstOffsetType.MEMBASE_IMM_OFFREG, 1, False, 0x60, 'main', 2, 'i64'))
    test_ins(vm_if_reg_COND_off().build(1, '>', 0x1234, 'main', 'u32'))
    test_ins(vm_if_reg_COND_offreg().build(1, '>', 2, 'main', 'ptr'))
    test_ins(vm_if_reg_COND_reg_off().build(1, '>', 2, 0x1234, 'u64'))
    test_ins(vm_if_reg_COND_reg_reg().build(1, '>', 2, 4, 'u64'))
    test_ins(vm_if_reg_COND_imm().build(1, '>', 0x1234, 'u64'))
    test_ins(vm_if_reg_COND_imm().build(1, '>', 0x12, 'u8'))
    test_ins(vm_save_restore().build(1, InstSaveRestoreRegOp.SAVE, 2))
    test_ins(vm_save_restore().build(1, InstSaveRestoreRegOp.RESTORE, 2))
    test_ins(vm_save_restore().build(1, InstSaveRestoreRegOp.CLEAR, 2))
    test_ins(vm_save_restore().build(1, InstSaveRestoreRegOp.REG_ZERO, 2))
    test_ins(vm_save_restore_mask().build(InstSaveRestoreRegOp.SAVE, [2,3]))
    test_ins(vm_save_restore_mask().build(InstSaveRestoreRegOp.RESTORE, [2,3]))
    test_ins(vm_save_restore_mask().build(InstSaveRestoreRegOp.CLEAR, [2,3]))
    test_ins(vm_save_restore_mask().build(InstSaveRestoreRegOp.REG_ZERO, [2,3]))
    test_ins(vm_rw_static_reg().build(1, 2))
    test_ins(vm_rw_static_reg().build(1, 0x99))
    test_ins(vm_pause().build())
    test_ins(vm_resume().build())
    test_ins(vm_log_off().build(1, 0x1234))
    test_ins(vm_log_offreg().build(1, 2))
    test_ins(vm_log_reg_off().build(1, 2, 0x1234))
    test_ins(vm_log_reg_offreg().build(1, 2, 4))
    test_ins(vm_log_reg().build(1, 2))


if __name__ == '__main__':
    test_error()
    #test_parser()
    #test_api()
