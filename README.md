# dmnt Cheat VM ASM

An assembler/disassembler for dmnt cheat vm.

Tested on Atmosphere.

**WIP**

Disassembler and Python API have been implemented.

Assembler is stilling being working on. Should be quick.

## Feedback Needed!

Please leave a comment on issue page if you have any suggestions on syntax.

(I'm considering getting rid of store/load/set ...)

## Demo

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


## ASM Syntax TLDR

Feel the vibe in example, and write your own code. I believe you can get it.

### About Cheat VM
In the Cheat VM, you are provided with:
  - 0-15 registers as rN
  - 0-15 save slots as save[N]
  - 0-0x7f static registers as read-only static registers
  - 0x80-0xff static registers as write-only static registers

No division, no floating point.

### About Syntax
Each line is translated to one instruction in the end, so do not nest with other complex expressions, will not work.

The assembler does not support variable. You must use vm register directly.

You can omit data type but it's strongly recommended to specify it. Otherwise it will be u32 in most case.

All codes are case in-sensitive.

As for immediate value, you can use `0x` prefix for hex, `0b` prefix for binary, `0o` prefix for octal, or just plain decimal.

#### Glossary

- `reg`: vm reg
- `mem`: game process memory.
- No real registers are involved. The vm does not have memory space either.
- `value`: immediate value.
- `off` or `offset`: offset immediate value.
- `offreg`: offset register.
- `base`: memory base, one of `main`, `heap`, `alias`, `aslr`.
- `dtype`: u8/u16/u32/u64/i8.../i64/ptr
- `{ .. }`: optional

### R/W Memory

`=` means an read/write instruction.

You can do reg<->mem, reg<->reg, reg<->save, reg<->static
You can also do reg<-imm, mem<-imm, save<-0

Use `[ .. ]` to dereference memory. The usage and limitation are the same as other ASM. 

You can NOT do mem<->mem in one line.

You may even add offset imm or/and offset register to reg/mem while reading/writing.

**For Accurate Rules, Check Syntax Below**

```bash
# mem<-imm
{dtype} [base + rN {+offset}] = value
    where:
        offset <= 0xFFFFFFFFFF
        dtype: default = u32
    example:
        i8 [maIn + r2 + 0x100] = -1

# reg<-imm
rN = value  # always 64-bit

# reg<-mem
{dtype} rN = [base {+offset}]
{dtype} rN = [rN {+ offset}]  # Note: {dtype} rA = [rB + offset] is unsupported

# mem<-imm
{dtype} [rM{++} {+rN}] = value
    where:
        rM++ means rM += width after operation
    example:
        i32 [r0++ + r1] = 0x12345678
        i32 [r0 + r1] = 0x12345678
        i32 [r0++] = 0x12345678

# reg update (legacy, use next instruction instead)
{dtype} rN OP= value
    where:
        OP is one of +, -, *, <<, >>
    example:
        r0 += 0x12345678

# reg<->reg
{dtype} rD = rS OP value
{dtype} rD = rS OP rs
{dtype} rD = rS
{dtype} rD = ~rS
    where:
        OP is one of +, -, *, <<, >> & | ^

# mem<-reg
{dtype} [rM{++} {+offset {+rN}}] = rS
{dtype} [base + {+offset {+rM{++}}}] = rS
    where:
        rM ++ means rM +=width after operation
    example:
        u32 [r2++] = r5
        u32 [r2++ + 2 + r3] = r4

```

## Control Flow

```bash
#####################
if {dtype} [base {+offset}] COND value {then}
if {dtype} rN COND [base {+offset}] {then}
if {dtype} rN COND [base + rM] {then}
if {dtype} rN COND [rM {+offset}] {then}
if {dtype} rN COND [rBase + rOffset] {then}
if {dtype} rN COND value {then}
if {dtype} rN COND rM {then}
    where:
        COND = >, >=, <, <=, ==, !=
        THEN is optional keyword
else
endif

# other if syntax
# examples
if [main + 0x1234] > 0x1234
else  # optional
endif

#####################

# If keys are pressed
if key KEYNAME|KEYNAME2|...
  # examples of valid keyname
  # A/B/X/Y
  # LSTICK/RSTICK/../LSTICK_UP
  # ZL/ZR/SL/SR
  # PLUS/MINUS
  # UP/DOWN/LEFT/RIGHT
else    # not sure if this works. TIY.
endif


loop rN to COUNT
  # DONT FORGET to specify rN
endloop rN

```

### Other Commands
```bash
# save/restore
save[i] = rN
rN = save[i]
save[i] = 0
rN = 0
    where:
        i is save index, N is reg id
        i < 16 and N < 16
    example:
        save[3] = r3

# batch save/restore
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

# static registers (I don't understand why people use it)
rN = static[i]  # when i < 0x80
static[i] = rN  # when i >= 0x80

# pause the game
pause

# resume the game
resume

# log data to file
log ID {dtype} [base {+offset}]
log ID {dtype} [base + rN]
log ID {dtype} [rM {+offset}]
log ID {dtype} [rM + rN]
log ID {dtype} [rM]
    where:
        0 <= ID <= 0xF

# use it as a placeholder in credit section
nop

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
