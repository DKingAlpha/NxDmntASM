# dmnt Cheat VM ASM

An assembler/disassembler for dmnt cheat vm.

Tested on Atmosphere.

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

### Python API
```py

```


## TLDR

All codes are case insensitive

No division, no floating point

Most opcodes has default width of u32 if omitted, unless otherwise specified in instruction syntax. User can specify dtype in opcode.

{ ... } : operands in brace { } are optional while writing assembly

## Syntax

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
