const clientSubmit = document.getElementById('clientSubmit');
const clientForm = document.getElementById('clientForm');
const phoneNumbers = document.querySelectorAll('.phone-number');


async function setActiveClient(client_id){
    fetch(`/api/v1/clients/set_active?client_id=${client_id}`,
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
    fetch("/api/v1/clients/register",
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


phoneNumbers.forEach(phone => {
  phone.addEventListener('click', function() {
    // Remove "active" from all numbers
    let clicked = event.target;

    let oldActive = document.querySelector('.phone-number.active');
    phoneNumbers.forEach(p => p.classList.remove('active'));
    
    // console.log(event.target.getAttribute('data-client-id'));
    setActiveClient(event.target.getAttribute('data-client-id'));
    $('#nav-active-client').text(event.target.getAttribute('data-client-phone'));
    if (oldActive) {
        oldActive.classList.remove('active');
        oldActive.style.pointerEvents = 'auto';
        oldActive.style.cursor = 'pointer';

        // Rimuovi la spunta se c'era
        const checkmark = oldActive.querySelector('.checkmark');
        if (checkmark) {
            checkmark.remove();
        }
    }

    // 2. Imposta il nuovo attivo
    clicked.classList.add('active');
    clicked.style.pointerEvents = 'none';
    clicked.style.cursor = 'default';

    let check = document.createElement('span');
    check.classList.add('checkmark');
    check.textContent = '(active)';
    clicked.appendChild(check);
    // window.location.reload();
    // this.classList.add('active');

    const newClientId = clicked.getAttribute('data-client-id');
    console.log(`Active number changed to: ${newClientId}`);
  });
});