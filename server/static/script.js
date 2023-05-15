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
        // if now - last_req_time < 10s, then return
        if (Date.now() - last_req_time < 10000) {
            return;
        }
        last_req_time = Date.now();
        const pastedText = event.clipboardData.getData('text');
        leftTextarea.value = pastedText;
        dmnt_dism(pastedText);
    });

    var last_req_time = 0;
    leftTextarea.addEventListener('input', (event) => {
        // if now - last_req_time < 10s, then return
        if (Date.now() - last_req_time < 10000) {
            return;
        }
        last_req_time = Date.now();
        dmnt_dism(event.target.value);
    });

    function dmnt_dism(text) {
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
});
