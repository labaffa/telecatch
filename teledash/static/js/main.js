$("#inpt_search").on('focus', function () {
	$(this).parent('label').addClass('active');
});

$("#inpt_search").on('blur', function () {
	if($(this).val().length == 0)
		$(this).parent('label').removeClass('active');
});
$("#inpt_search").on("keydown", function(event) {
    if (event.key === "Enter") {
      event.preventDefault(); // Impedisce l'invio del modulo
      let limit = parseInt($('#inpt_limit').val(), 10) || 100;
      if (limit > 1000){
        limit = 1000;
      }
      let search = this.value;
      // Chiamata all'API con il valore dell'input
      callAPI(search, limit);
    }
  });

$('#submitButton').on("click", function() {
    let search = $('#inpt_search').val();
    let limit = parseInt($('#inpt_limit').val(), 10) || 100;
    if (limit > 1000){
      limit = 1000;
    }
    // Chiamata all'API con il valore dell'input
    callAPI(search, limit);
  });
const input = document.getElementById("inpt_search");
const resultTableBody = document.querySelector("#results-table tbody");

/* const submitButton = document.getElementById("submitButton");
submitButton.addEventListener("click", function() {
  const value = input.value;
  callAPI(value);
});
 */


function callAPI(value, limit) {
  fetch(`/api/search_channels?search=${value}&limit=${limit}`)
    .then(response => response.json())
    .then(data => {
      // Pulisci la tabella
      resultTableBody.innerHTML = "";

      // Popola la tabella con i risultati
      data.forEach(item => {
        const row = document.createElement("tr");
        const channelCell = document.createElement("td");
        const messageCell = document.createElement("td");
        const timestampCell = document.createElement("td");

        channelCell.textContent = item.peer_id.channel_id;
        messageCell.textContent = item.message;
        timestampCell.textContent = item.date;

        row.appendChild(channelCell);
        row.appendChild(messageCell);
        row.appendChild(timestampCell);

        resultTableBody.appendChild(row);
      });
    })
    .catch(error => {
      console.error("Errore nella chiamata API:", error);
    });
}
