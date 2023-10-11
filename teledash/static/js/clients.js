const clientSubmit = document.getElementById('clientSubmit');
const clientForm = document.getElementById('clientForm');

async function setActiveClient(client_id){
    fetch(`/api/set_active_client_of_user?client_id=${client_id}`,
    {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json' 
        }
      }
    ).then((response) => {
        if (response.ok) {
            return response.json()
        }
        return response.json().then((data) => {throw new Error(data.detail)})
    })
    .then((data) => {
        console.log(data);
    })
    .catch((err) => {
        console.log('Error: ', err);
        window.alert(`Something went wrong when trying to set the client as the active one. 
        The error from the server is: ${err}
        
        Try to register the phone number again
        `)
    })
}

function loginTelegram(){
    let data = new FormData(clientForm);
    fetch("/add_tg_phone",
        {
            method: "POST",
            body: data
        }).then((response) => response.json())
        .then((data) => {
            console.log("add_tg_phone response: ", data)
            if (data.detail){
                console.log(data.detail.msg)
                
                throw new Error(String(data.detail[0].msg))
            }
            const status = document.getElementById("clientStatus");
            console.log(data)
            if (data.authenticated == true){
                status.innerText = "Successfully registered account"
                setActiveClient(data.id);
                window.alert(`Client of the phone ${data.phone} is logged in and will be used to search Telegram`);
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