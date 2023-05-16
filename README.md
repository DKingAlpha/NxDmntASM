# dmnt Cheat VM ASM

An assembler/disassembler for dmnt cheat vm.

Tested on Atmosphere.

**WIP**

Disassembler and Python API have been implemented.

Assembler is stilling being working on. Should be quick.

## Feedback Needed!

Please leave a comment on issue page if you have any suggestions on syntax.

(I'm considering getting rid of store/load/set ...)

## Example

Disassembly Output

```lua
[Max Status]
u64 r15 = [main + 0x724070]
u64 r15 += 0x40
loop r14 to 7
    u32 [r15] = 0x270f
    u64 r15 += 0x4
endloop r14
endif
u64 r15 = [main + 0x724070]
u64 r15 += 0x60
loop r14 to 4
u32 [r15] = 0x270f
u64 r15 += 0x4
endloop r14
endif

[RS ←/→ Switch Sub-Weapon (AMS only)]
u64 r12 = [main + 0x1cc6f08]
u64 r12 = [r12 + 0x2c8]
u64 r12 = [r12 + 0x58]
u64 r12 = [r12 + 0x48]
u64 r12 = [r12 + 0x50]
u64 r12 += 0x1877e
u64 r13 = r12
u64 r13 = [r13 + 0x0]
if key RSTICK_RIGHT
    if u8 r13 < 0x6
        u32 r13 += 0x1
        u8 [r12] = r13
    endif
endif
if key RSTICK_LEFT
    if u8 r13 > 0x1
        u32 r13 -= 0x1
        u8 [r12] = r13
    endif
endif
```

### Python API
```py
from dmnt_asm.parser import CheatParser
from pathlib import Path
# parse vm code
parser = CheatParser()
content = Path('CHEAT.txt').read_text(encoding='utf-8', errors='backslashreplace')
all_ok = parser.parse(content)
print(parser.dumps(indent=2))

# generate vm code from api
from dmnt_asm.instructions import *
vm_XX().build( ... args ...).asm()
```

## ASM Syntax TLDR

Feels like asm, all codes are case-insensitive.

No division, no floating point.

User can explicitly specify dtype in opcode, or omit for default.

Most opcodes has default width of u32 if omitted, unless otherwise specified in instruction syntax.

## ASM Syntax

- Opcode/Operand Keywords:
  - set
  - load
  - store
  - rN (r0 - r16)
  - [ ... ]     # dereference like asm


- Memory Base Keywords:
  - main
  - heap
  - alias
  - aslr

- Data Type Keywords:
  - i8 i16 i32 i64
  - u8 u16 u32 u64
  - ptr
  - any* (=ptr)
  - B H W X (unsigned)

- Operator:
  - `+ - * / % & | ^ ~ << >>`
  - `+= -= *= /= %= &= |= ^= <<= >>=`
  - rN ++ in 'store' instruction

- Flow Control Keywords:
  - if ... {then}{:}    # optional
  - else
  - endif
  - 
  - if key L | X | ... {then}   # then is optional
  - ...
  - endif
  - 
  - loop rN to COUNT
  - ...
  - endloop
  

- Comment:
  - `# this is a comment to the end of line`

## Terms

### Memory / Address
Address in memory of switch game process

### Register
16 u64 vm registers of dmnt cheat vm.

These registers are shared context of all cheats in the same cheat file.

Cheat uses these vm registers, to store/load value.

### Static Register
Well, another set of 128+128 u64 vm "registers". I guess people use it as a larger vm memory.

It's exported to AMS dmnt API ReadStaticRegister / WriteStaticRegister.

### Save / Restore Registers
Well, another set of 0x16 registers, used to save/restore values of vm registers.
