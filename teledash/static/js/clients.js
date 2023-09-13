const clientSubmit = document.getElementById('clientSubmit');
const clientForm = document.getElementById('clientForm');


function loginTelegram(){
    let data = new FormData(clientForm);
    fetch("/add_tg_phone",
        {
            method: "POST",
            body: data
        }).then((response) => response.json())
        .then((data) => {
            if (data.detail){
                console.log(data.detail.msg)
                
                throw new Error(String(data.detail[0].msg))
            }
            const status = document.getElementById("clientStatus");
            console.log(data)
            if (data.authenticated == true){
                status.innerText = "Successfully registered account"
                window.alert("Successfully registered account")
                window.location.reload();
            } else {
                const codeInput = `<div class="field-wrap">
                    <label>
                        Insert the received code from Telegram:
                    </label>
                    <input name='code' type='number' placeholder='01234'>
                </div>`
                clientForm.insertAdjacentHTML('beforeend', codeInput);
            }
            $('#clientSubmit').prop('disabled', false);
        })
        .catch((err) => {
            $('#clientSubmit').prop('disabled', false);
            window.alert(err);
        })
}

clientSubmit.onclick = (ev) => {
    $('#clientSubmit').prop('disabled', true);
    loginTelegram();
    ev.preventDefault();
}