window.addEventListener('DOMContentLoaded', () => {
    const leftTextarea = document.getElementById('leftTextarea');
    const rightTextarea = document.getElementById('rightTextarea');

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

    leftTextarea.addEventListener('paste', (event) => {
        const pastedText = event.clipboardData.getData('text');
        leftTextarea.value = pastedText;
        dmnt_dism(pastedText);
    });

    var last_active_time = 0;
    var last_req_text = '';

    leftTextarea.addEventListener('input', (event) => {
        last_active_time = Date.now();
    });

    function dmnt_dism(text) {
        last_active_time = Date.now();
        last_req_text = text;

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

    const autoDism = setInterval(() => {
        if (leftTextarea.value.length == 0) {
            return;
        }
        if (leftTextarea.value == last_req_text) {
            return;
        }
        if (Date.now() - last_active_time < 5000) {
            return;
        }
        dmnt_dism(leftTextarea.value);
    }, 1000);
});
