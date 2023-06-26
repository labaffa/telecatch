var tableMessages = [];
// Numero di righe da visualizzare per pagina
var rowsPerPage = 10;
  
// Selettore della tabella e del contenitore di paginazione
var tableSelector = '#results-table';
var paginationSelector = '#pagination';
var input = document.getElementById("inpt_search");
var resultTableBody = document.querySelector("#results-table tbody");


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
    $('#results-table').attr('data-page', 1);
    let search = $('#inpt_search').val();
    /* let limit = parseInt($('#inpt_limit').val(), 10) || 100;
    if (limit > 1000){
      limit = 1000;
    } */
    // Chiamata all'API con il valore dell'input
    callAPI(search, 40, 0, 0);
  });

/* const submitButton = document.getElementById("submitButton");
submitButton.addEventListener("click", function() {
  const value = input.value;
  callAPI(value);
});
 */


function callAPI(value, limit=40, offset_channel=0, offset_id=0) {
  emptyTableHeight = 30*rowsPerPage;
  resultTableBody.innerHTML = `<div class="container" style="height: ${emptyTableHeight}px;>
    <span class="loader centered">Loading...</span>
    </div>
    `;
  fetch(
    `/api/search_channels?search=${value}&limit=${limit}&offset_channel=${offset_channel}&offset_id=${offset_id}`,
    {
        headers: {
          'Cache-Control': 'no-cache'
        }}
    )
    .then(response => response.json())
    .then(data => {
      if (data.length == 0){
        window.messagesDone = true;
      }
      else {
        window.messagesDone = false;
      }
      window.tableMessages.push(...data);
      // Pulisci la tabella
      resultTableBody.innerHTML = "";

      // Popola la tabella con i risultati
      window.tableMessages.forEach(item => {
        const row = document.createElement("tr");
        const channelCell = document.createElement("td");
        const messageCell = document.createElement("td");
        const timestampCell = document.createElement("td");

        channelCell.textContent = item.peer_id.channel_url;
        messageCell.textContent = item.message;
        timestampCell.textContent = item.date;

        row.appendChild(channelCell);
        row.appendChild(messageCell);
        row.appendChild(timestampCell);

        resultTableBody.appendChild(row);
      });
      generatePagination(
        '#results-table', '#pagination', $('#results-table').attr('data-page'));
      showRows($('#results-table').attr('data-page'), '#results-table');
    })
    .catch(error => {
      console.error("Errore nella chiamata API:", error);
    });
}
 

/*  TABLE PAGINATION */


 // Calcola il numero di pagine e genera i link di paginazione
 function generatePagination(tableSelector, paginationSelector, pageNumber, rowsPerPage=10) {
    //let totalRows = $(tableSelector + ' tbody tr').length;
    let totalRows = window.tableMessages.length;
    let totalPages = Math.ceil(totalRows / rowsPerPage);

    console.log(totalRows, totalPages, pageNumber, window.messagesDone)
    $('#page-dw').hide();
    $('#page-up').hide();
    $('#page-number').html(pageNumber);
    // Aggiungi il pulsante "Pagina precedente" se non è la prima pagina
    if (pageNumber > 1) {
      $('#page-dw').show();
    } 

    // Aggiungi il pulsante "Pagina successiva" se non è l'ultima pagina
    if (pageNumber < totalPages) {
      $('#page-up').show();
    }

    if (pageNumber == totalPages && window.messagesDone == false){
        let search = $('#inpt_search').val();  // dobbiamo usare delle variabili globali
        let limit = parseInt($('#inpt_limit').val(), 10) || 100;
        let offset_channel = window.allChannels.indexOf(
            window.tableMessages.slice(-1)[0].peer_id.channel_url
        );
        let offset_id = window.tableMessages.slice(-1)[0].id;
        callAPI(search, limit, offset_channel, offset_id);
    }


}
// Funzione per mostrare solo le righe desiderate
function showRows(pageNumber, tableSelector, rowsPerPage=10) {
    let startIndex = (pageNumber - 1) * rowsPerPage;
    let endIndex = startIndex + rowsPerPage;
    $(tableSelector + ' tbody tr').hide(); // Nasconde tutte le righe
    $(tableSelector + ' tbody tr').slice(startIndex, endIndex).show(); // Mostra solo le righe della pagina corrente
  }



$(document).ready(function() {
    // Inizializza la paginazione
    // generatePagination(tableSelector, paginationSelector, 1, rowsPerPage);
    // showRows(1, tableSelector, rowsPerPage);
    createEmptyTable(rowsPerPage);
    
});

// Gestisci il click sui link di paginazione
$('#page-up').click(function(e) {
    e.preventDefault();
    let page = parseInt($('#results-table').attr('data-page'));
    $('#results-table').attr('data-page', page + 1);
    generatePagination(tableSelector, paginationSelector, page + 1, rowsPerPage);
    showRows(page + 1, tableSelector, rowsPerPage);
  });


// Gestisci il click sui link di paginazione
$('#page-dw').click(function(e) {
    e.preventDefault();
    let page = parseInt($('#results-table').attr('data-page'));
    $('#results-table').attr('data-page', page - 1);
    showRows(page - 1, tableSelector, rowsPerPage);
    generatePagination(tableSelector, paginationSelector, page - 1, rowsPerPage);
  });


  function createEmptyTable(rows) {
  
    // Crea le righe vuote
    for (let i = 0; i < rows; i++) {
      let row = resultTableBody.insertRow();
      // Puoi aggiungere eventuali celle o contenuto alle righe se necessario
    }
  }