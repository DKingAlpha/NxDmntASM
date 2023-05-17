window.addEventListener('DOMContentLoaded', () => {
    const leftTextarea = document.getElementById('leftTextarea');
    const rightTextarea = document.getElementById('rightTextarea');
    var last_active_time = 0;
    var last_req_left_text = '';
    var last_req_right_text = '';
    var last_input_area = 'left';

    leftTextarea.addEventListener('drop', (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        const reader = new FileReader();

        reader.onload = function (event) {
            leftTextarea.value = event.target.result;
            dmnt_dism(event.target.result);
        };

        reader.readAsText(file);
    });

    rightTextarea.addEventListener('paste', (event) => {
        const pastedText = event.clipboardData.getData('text');
        rightTextarea.value = pastedText;
        dmnt_asm(pastedText);
    });

    rightTextarea.addEventListener('drop', (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        const reader = new FileReader();

        reader.onload = function (event) {
            rightTextarea.value = event.target.result;
            dmnt_asm(event.target.result);
        };

        reader.readAsText(file);
    });

    leftTextarea.addEventListener('paste', (event) => {
        const pastedText = event.clipboardData.getData('text');
        leftTextarea.value = pastedText;
        dmnt_dism(pastedText);
    });

    leftTextarea.addEventListener('input', (event) => {
        last_active_time = Date.now();
        last_input_area = 'left';
    });

    rightTextarea.addEventListener('input', (event) => {
        last_active_time = Date.now();
        last_input_area = 'right';
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
                rightTextarea.value = data.dism;
                if (data.errors.length > 0) {
                    var errmsg = '';
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                    alert(errmsg);
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
                leftTextarea.value = data.asm;
                if (data.errors.length > 0) {
                    var errmsg = '';
                    for (var i = 0; i < data.errors.length; i++) {
                        errmsg += data.errors[i] + '\n';
                    }
                    alert(errmsg);
                }
            })
            .catch((error) => console.error(error));
    }

    const autoDism = setInterval(() => {
        if (Date.now() - last_active_time < 5000) {
            return;
        }
        if (last_input_area == 'left') {
            if (leftTextarea.value.length == 0) {
                return;
            }
            if (leftTextarea.value == last_req_left_text) {
                return;
            }
            dmnt_dism(leftTextarea.value);
        } else if (last_input_area == 'right') {
            if (rightTextarea.value.length == 0) {
                return;
            }
            if (rightTextarea.value == last_req_right_text) {
                return;
            }
            dmnt_asm(rightTextarea.value);
        } else {
            alert('error');
        }
    }, 1000);
});
