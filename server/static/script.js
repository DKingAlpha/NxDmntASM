var editor_left = null;
var editor_right = null;

function downloadTextToFile(text, filename) {
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
  
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
  
    document.body.appendChild(link);
    link.click();
  
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function setupNxDmntAsm()
    {
    // Register a new language
    monaco.languages.register({ id: "nx-dmnt-asm" });

    // Register a tokens provider for the language
    monaco.languages.setMonarchTokensProvider("nx-dmnt-asm", {
        tokenizer: {
            root: [
                [/^\{.*\}$/, "master-entry"],
                [/^\[.*\]$/, "entry"],
                [/^\s*#.*$/, "comment"],
                [/\b(?:if|key|else|endif|loop|to|endloop|save|restore|static|pause|resume|log|nop)\b/i, "keyword"],
                [/\b[r][\d]{1,2}\b/i, "register"],
                [/\b[ui][\d]{1,2}\b/i, "datatype"],
                [/\b(ptr|float|double)\b/i, "datatype"],
                [/\b(?:main|heap|alias|aslr)\b/i, "membase"],
                [/\b[\da-fA-F]{8}\b/, "vmmc"],
                [/\b(?:0b[01]+|0x[\dA-Fa-f]+|0o[0-7]+|\d+)\b/, "imm"],
            ],
        },
    });

    // Define a new theme that contains only rules that match this language
    monaco.editor.defineTheme("NxDmntAsmDefaultTheme", {
        base: "vs",
        inherit: false,
        rules: [
            { token: "master-entry", foreground: "cc00ff", fontStyle: "bold italic underline"},
            { token: "entry", foreground: "ff5050", fontStyle: "underline" },
            { token: "comment", foreground: "339933" },
            { token: "keyword", foreground: "0000cc", fontStyle: "bold" },
            { token: "register", foreground: "0033cc" },
            { token: "datatype", foreground: "00cc00" },
            { token: "membase", foreground: "ff3333", background: "ffff00", fontStyle: "bold" },
            { token: "imm", foreground: "cc7a00" },
            { token: "vmmc", foreground: "006600", background: "71ccde" },
        ],
        colors: {
            "editor.foreground": "#000000",
        },
    });

    // Register a completion item provider for the new language
    monaco.languages.registerCompletionItemProvider("nx-dmnt-asm", {
        provideCompletionItems: (model, position) => {
            var word = model.getWordUntilPosition(position);
            var range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn,
            };
            var suggestions = [
                {
                    label: "loop-endloop",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: [
                        "loop r$0",
                        "\t$1",
                        "endloop r$0",
                    ].join("\n"),
                    insertTextRules:
                        monaco.languages.CompletionItemInsertTextRule
                            .InsertAsSnippet,
                    documentation: "If-Else-Endif Statement",
                    range: range,
                },
                {
                    label: "if-else-endif",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: [
                        "if ${1:lvalue} ${2:COND} ${3:rvalue}",
                        "\t$0",
                        "else",
                        "\t",
                        "endif",
                    ].join("\n"),
                    insertTextRules:
                        monaco.languages.CompletionItemInsertTextRule
                            .InsertAsSnippet,
                    documentation: "If-Else-Endif Statement",
                    range: range,
                },
                {
                    label: "if-key-else-endif",
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: [
                        "if key ${1:KEY1|...}",
                        "\t$0",
                        "else",
                        "\t",
                        "endif",
                    ].join("\n"),
                    insertTextRules:
                        monaco.languages.CompletionItemInsertTextRule
                            .InsertAsSnippet,
                    documentation: "If-Key-Else-Endif Statement",
                    range: range,
                },
            ];
            return { suggestions: suggestions };
        },
    });

    editor_left = monaco.editor.create(document.getElementById("left-ce"), {
        theme: "NxDmntAsmDefaultTheme",
        value: "",
        language: "nx-dmnt-asm",
        automaticLayout: true,
    });

    editor_right = monaco.editor.create(document.getElementById("right-ce"), {
        theme: "NxDmntAsmDefaultTheme",
        value: "",
        language: "nx-dmnt-asm",
        automaticLayout: true,
    });

    editor_left.addAction({
        id: "ctrl-s-to-save",
        label: "Save File",
        keybindings: [
            monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS
        ],
        precondition: null,
        keybindingContext: null,
        contextMenuGroupId: "navigation",
        contextMenuOrder: 1.5,
        // Method that will be executed when the action is triggered.
        // @param editor The editor instance is passed in as a convenience
        run: function (ed) {
            downloadTextToFile(ed.getValue(), "NxDmntAsm.txt")
        },
    });
    editor_right.addAction({
        id: "ctrl-s-to-save",
        label: "Save File",
        keybindings: [
            monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS
        ],
        precondition: null,
        keybindingContext: null,
        contextMenuGroupId: "navigation",
        contextMenuOrder: 1.5,
        // Method that will be executed when the action is triggered.
        // @param editor The editor instance is passed in as a convenience
        run: function (ed) {
            downloadTextToFile(ed.getValue(), "NxDmntAsm.asm")
        },
    });
}

function setupAutoAsm() {
    const left_div = document.getElementById('left-ce');
    const right_div = document.getElementById('right-ce');
    var last_active_time = 0;
    var last_req_left_text = '';
    var last_req_right_text = '';
    var last_input_area = 'left';

    left_div.addEventListener('drop', (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        const reader = new FileReader();

        reader.onload = function (event) {
            editor_left.setValue(event.target.result);
            localStorage.setItem('left_code', editor_left.getValue());
            dmnt_dism(event.target.result);
        };

        reader.readAsText(file);
    });

    editor_left.onDidPaste((event) => {
        const newContent = editor_left.getValue();
        localStorage.setItem('left_code', editor_left.getValue());
        dmnt_dism(newContent);
    });

    editor_left.onKeyUp((event) => {
        last_active_time = Date.now();
        last_input_area = 'left';
        localStorage.setItem('left_code', editor_left.getValue());
    });

    right_div.addEventListener('drop', (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        const reader = new FileReader();

        reader.onload = function (event) {
            editor_right.value = event.target.result;
            localStorage.setItem('right_code', editor_right.getValue());
            dmnt_asm(event.target.result);
        };

        reader.readAsText(file);
    });

    editor_right.onDidPaste((event) => {
        const newContent = editor_right.getValue();
        localStorage.setItem('right_code', editor_right.getValue());
        dmnt_asm(newContent);
    });

    editor_right.onKeyUp((event) => {
        last_active_time = Date.now();
        last_input_area = 'right';
        localStorage.setItem('right_code', editor_right.getValue());
    });

    function dmnt_dism(text) {
        last_active_time = Date.now();
        last_req_left_text = text;

        fetch('/dmnt_dism', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `text=${encodeURIComponent(text)}`,
        })
            .then((response) => response.json())
            .then((data) => {
                editor_right.setValue(data.dism);
                localStorage.setItem('right_code', data.dism);
                var errmsg = '';
                if (data.errors.length > 0) {
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                }
                setLog(errmsg);
            })
            .catch((error) => console.error(error));
    }

    
    function dmnt_asm(text) {
        last_active_time = Date.now();
        last_req_right_text = text;

        fetch('/dmnt_asm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `text=${encodeURIComponent(text)}`,
        })
            .then((response) => response.json())
            .then((data) => {
                editor_left.setValue(data.asm);
                localStorage.setItem('left_code', data.asm);
                var errmsg = '';
                if (data.errors.length > 0) {
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                }
                setLog(errmsg);
            })
            .catch((error) => console.error(error));
    }

    const autoDism = setInterval(() => {
        if (Date.now() - last_active_time < 3000) {
            return;
        }
        if (last_input_area == 'left') {
            const leftSrc = editor_left.getValue();
            if (leftSrc == 0) {
                return;
            }
            if (leftSrc == last_req_left_text) {
                return;
            }
            dmnt_dism(leftSrc);
        } else if (last_input_area == 'right') {
            const rightSrc = editor_right.getValue();
            if (rightSrc == 0) {
                return;
            }
            if (rightSrc == last_req_right_text) {
                return;
            }
            dmnt_asm(rightSrc);
        } else {
            setLog('error');
        }
    }, 1000);
};

function setLog(log) {
    const bottom_log = document.getElementById("bottom-log");
    bottom_log.value = log;
    localStorage.setItem("log", log);
}

window.addEventListener('DOMContentLoaded', ()=>{
    setupNxDmntAsm();
    setupAutoAsm();
    for (const k of ['left_code', 'right_code', 'log']) {
        if (localStorage.getItem(k) == null) {
            localStorage.setItem(k, '')
        }
    }
    editor_left.setValue(localStorage.getItem('left_code'));
    editor_right.setValue(localStorage.getItem('right_code'));
    // document.getElementById("bottom-log").value = localStorage.getItem("log");

    if (editor_left.getValue().length == 0 && editor_right.getValue().length == 0) {
        editor_left.setValue(getExampleCode());
    }
});


function getExampleCode() {
return `[Moon Jump]
80000002
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
580F1000 00000110
580F1000 00000050
780F0000 0000002C
640F0000 00000000 C3500000
20000000

[Inf HP]
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
780F0000 00000160
640F0000 00000000 00000050

[Invincible]
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
780F0000 00000250
680F0000 50000000 50000000


[Inf Ammo]
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
580F1000 00000390
780F1000 000005E0
300E0000 0000000B
640F0000 00000000 000003E8
780F0000 000000E0
310E0000
20000000


[MAX Ammo]
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
580F1000 00000390
780F1000 0000056C
300E0000 0000000B
640F0000 00000000 000003E8
780F0000 000000E0
310E0000
20000000

[Weapon ATK]
580F0000 05C3FA50
580F1000 00000260
580F1000 00000058
580F1000 00000390
780F1000 0000055C
300E0000 0000000B
640F0000 00000000 461C3C00
780F0000 000000E0
310E0000
20000000
`;
}
