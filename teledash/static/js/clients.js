const clientSubmit = document.getElementById('clientSubmit');

clientSubmit.onclick = (ev) => {
    ev.preventDefault();

    let clientForm = document.getElementById('clientForm');
    let data = new FormData(clientForm);
    fetch("/add_tg_phone",
        {
            method: "POST",
            body: data    
        }).then((response) => response.json())
        .then((data) => {
            const status = document.getElementById("clientStatus");
            status.innerText = "Successfully registered account"
            console.log(data)

        })
          
}