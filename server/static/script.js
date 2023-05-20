var editor_left = null;
var editor_right = null;

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
                [/^#.*/, "comment"],
                [/\b(?:if|key|else|endif|loop|to|endloop|save|restore|static|pause|resume|log|nop)\b/i, "keyword"],
                [/\b[r][\d]{1,2}\b/i, "register"],
                [/\b[ui][\d]{1,2}\b/i, "datatype"],
                [/\bptr\b/i, "datatype"],
                [/\b(?:main|heap|alias|aslr\b)/i, "membase"],
                [/\b[\da-fA-F]{8}\b/, "vmmc"],
                [/\b(?:0b[01]+|0x[\dA-Fa-f]+|0o[0-7]+|\d+)\b/, "imm"],
            ],
        },
    });

    // Define a new theme that contains only rules that match this language
    monaco.editor.defineTheme("myCoolTheme", {
        base: "vs",
        inherit: false,
        rules: [
            { token: "master-entry", foreground: "cc00ff", fontStyle: "bold"},
            { token: "entry", foreground: "ff5050", fontStyle: "bold" },
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
                    label: "simpleText",
                    kind: monaco.languages.CompletionItemKind.Text,
                    insertText: "simpleText",
                    range: range,
                },
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
            ];
            return { suggestions: suggestions };
        },
    });

    editor_left = monaco.editor.create(document.getElementById("left-ce"), {
        theme: "myCoolTheme",
        value: "",
        language: "nx-dmnt-asm",
    });

    editor_right = monaco.editor.create(document.getElementById("right-ce"), {
        theme: "myCoolTheme",
        value: "",
        language: "nx-dmnt-asm",
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
                if (data.errors.length > 0) {
                    var errmsg = '';
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                    setLog(errmsg);
                }
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
                editor_left.value = data.asm;
                localStorage.setItem('left_code', data.asm);
                if (data.errors.length > 0) {
                    var errmsg = '';
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                    setLog(errmsg);
                }
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
    document.getElementById("bottom-log").value = localStorage.getItem("log");

    if (editor_left.getValue().length == 0) {
        editor_left.setValue(getExampleCode());
    }
});


function getExampleCode() {
    return `{Diablo II Resurrected Version 1.0.0.2 TID 0100726014352000 BID 7E78CC35BAF51EA2}

[60 FPS]
04000000 0412A204 00000001

[Default 30 FPS]
04000000 0412A204 00000002
[By Hazerou]

[Upgrade Points 30]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 00040000
640F0000 00000000 0000001E
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000

[Skill Points 30]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 00050000
640F0000 00000000 0000001E
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000

[Money 65000]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000E0000
640F0000 00000000 0000E8FD
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000
[Monsey is Capped to Level]

[Money 500,000]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000E0000
640F0000 00000000 0007A120
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000
[Monsey is Capped to Level]

[Money 1,500,000]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000E0000
640F0000 00000000 0016E360
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000
[Monsey is Capped to Level]

[200,000 XP]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000D0000
640F0000 00000000 00030D40
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000

[500,000 XP]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000D0000
640F0000 00000000 0007A120
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000

[10,000,000 XP]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000D0000
640F0000 00000000 00989680
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000

[50,000,000 XP]
580E0000 029D5688
580E1000 00000168
580E1000 00000088
30550000 00000002
989FE030
580F1000 00000080
780F0000 00000024
30000000 00000010
9811F100 00000000 00000004
54011000 00000000
C0451400 000D0000
640F0000 00000000 02FAF080
94900100 00000001
20000000
780F0000 00000008
31000000
780E1000 00000050
31550000
[Credits To TomSwitch]
`;
}
