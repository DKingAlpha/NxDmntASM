#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from pathlib import Path

from .parser import CheatParser


def main():
    for file in sys.argv[1:]:
        if not file.endswith('.txt'):
            continue
        cheat_txt = Path(file)
        cheat_asm = cheat_txt.parent / (cheat_txt.stem + '.asm')
        parser = CheatParser()
        content = cheat_txt.read_text(
            encoding='utf-8', errors='backslashreplace')
        all_ok = parser.parse(content)
        cheat_asm.write_text(parser.dumps(indent=4),
                             encoding='utf-8', errors='backslashreplace')
        print(f"{cheat_txt} -> {cheat_asm.name}")
        input("press enter to exit")


if __name__ == '__main__':
    main()
