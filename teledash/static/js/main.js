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


$('#submitButton').on("click", function() {
    $('#results-table').attr('data-page', 1);
    let search = $('#inpt_search').val();
    let start_date = $('#start-date').val();
    let end_date = $('#end-date').val();
    let chat_type = $('#chat-type').val();
    let country = null;
    let data_range = $('#data-range').val();

    window.search = search;
    window.start_date = start_date || null;
    window.end_date = end_date || null;
    window.chat_type = chat_type;
    window.country = country;
    window.data_range = data_range;
    window.limit = parseInt(window.data_range) ? -1 : 40;

    /* let limit = parseInt($('#inpt_limit').val(), 10) || 100;
    if (limit > 1000){
      limit = 1000;
    } */
    // Chiamata all'API con il valore dell'input
    window.tableMessages = [];
    callAPI(search, window.limit, 0, 0, 
      window.start_date, window.end_date, 
      window.chat_type, window.country);
  });

/* const submitButton = document.getElementById("submitButton");
submitButton.addEventListener("click", function() {
  const value = input.value;
  callAPI(value);
});
 */


function callAPI(
  value, limit=40, 
  offset_channel=0, offset_id=0,
  start_date, end_date, chat_type,
  country
  ) {
  emptyTableHeight = 30*rowsPerPage;
  resultTableBody.innerHTML = `<div class="container" style="height: ${emptyTableHeight}px;>
    <span class="loader centered">Loading...</span>
    </div>
    `;
  fetch(
    `/api/search_channels?search=${value}&limit=${limit}&offset_channel=${offset_channel}&offset_id=${offset_id}&start_date=${start_date}&end_date=${end_date}&chat_type=${chat_type}&country=${country}`,
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
        const typeCell = document.createElement("td");
        const countryCell = document.createElement("td");
        const viewsCell = document.createElement("td");


        channelCell.textContent = item.peer_id.channel_url;
        messageCell.textContent = item.message;
        timestampCell.textContent = item.date;
        typeCell.textContent = item.chat_type;
        countryCell.textContent = item.country;
        viewsCell.textContent = item.views;

        row.appendChild(channelCell);
        row.appendChild(messageCell);
        row.appendChild(timestampCell);
        row.appendChild(typeCell);
        row.appendChild(countryCell);
        row.appendChild(viewsCell);

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
        let offset_channel = window.allChannels.indexOf(
            window.tableMessages.slice(-1)[0].peer_id.channel_url
        );
        let offset_id = window.tableMessages.slice(-1)[0].id;
        callAPI(
          window.search, window.limit, 
          offset_channel, offset_id, 
          window.start_date, window.end_date,
          window.chat_type, window.country
          );
    }


}
// Funzione per mostrare solo le righe desiderate
function showRows(pageNumber, tableSelector, rowsPerPage=10) {
    let startIndex = (pageNumber - 1) * rowsPerPage;
    let endIndex = startIndex + rowsPerPage;
    $(tableSelector + ' tbody tr').hide(); // Nasconde tutte le righe
    $(tableSelector + ' tbody tr').slice(startIndex, endIndex).show(); // Mostra solo le righe della pagina corrente
  }




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


$('#export-messages').click(function(e){
  var myTableArray = [];
  var keys = [
    "username", "message", "timestamp", 
    "type", "country", "views"
  ]
  $("table#results-table tr").each(function() {
    let arrayOfThisRow = [];
    let tableData = $(this).find('td');
    if (tableData.length > 0) {
        tableData.each(function() {arrayOfThisRow.push($
          (this).text()); });
        let objectOfThisRow = Object.fromEntries(
          keys.map((k, i) => [k, arrayOfThisRow[i]]));
          
        myTableArray.push(objectOfThisRow);
    }});
  console.log(myTableArray);
  fetch('/api/export_to_csv', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    //body: JSON.stringify(window.tableMessages)
    body: JSON.stringify(myTableArray)
  }).then(res => {
    const disposition = res.headers.get('Content-Disposition');
    filename = disposition.split(/;(.+)/)[1].split(/=(.+)/)[1];
    if (filename.toLowerCase().startsWith("utf-8''"))
        filename = decodeURIComponent(filename.replace("utf-8''", ''));
    else
        filename = filename.replace(/['"]/g, '');
    return res.blob();
  }).then(blob => {
    var url = window.URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a); // append the element to the dom
    a.click();
    a.remove(); // afterwards, remove the element  
  });

});



async function fillChatInfo(eleId, chatType){
  
  let select = $(eleId);
  
    let count = window.channelsInfo.meta[`${chatType}_count`]
    let header = (chatType == "channel") ? 'Channels' : "Groups"
    select.append(
      $('<option>', {
        text: '-- ' + header + ` [${count}]` + ' --',
        value: ""
      })
    )
    window.channelsInfo.data.forEach((channel) => {
      // Crea un'opzione con il valore e il testo dell'oggetto
      if (channel.type == chatType) {
        select.append(
          $('<option>', {
            text: `${channel.title} [${channel.identifier}]`,
            value: channel.identifier,
          })
        );
      }});
  
};

async function fillMsgCounts(eleId){
  let select = $(eleId);
  let totalCount = window.channelsInfo.meta.msg_count;
  select.append(
    $('<option>', {
      text: '-- Message count' + ` [${totalCount}]` + ' --',
      value: ""
    })
  )
  window.channelsInfo.data.forEach((channel) => {
      select.append(
        $('<option>', {
          text: `${channel.title}:  ${channel.count}`,
          value: channel.identifier,
        })
      );
    });


};

async function fillPtsCounts(eleId){
  let select = $(eleId);
  let totalCount = window.channelsInfo.meta.participant_count;
  select.append(
    $('<option>', {
      text: '-- Participants' + ` [${totalCount}]` + ' --',
      value: ""
    })
  )
  window.channelsInfo.data.forEach((channel) => {
      select.append(
        $('<option>', {
          text: `${channel.title}:  ${channel.participants_counts}`,
          value: channel.identifier,
        })
      );
    });
};


$(document).ready(function() {
  // Inizializza la paginazione
  // generatePagination(tableSelector, paginationSelector, 1, rowsPerPage);
  // showRows(1, tableSelector, rowsPerPage);
  createEmptyTable(rowsPerPage);
  fetch(`/api/channels_info`, 
            {
                headers: {'Cache-Control': 'no-cache'}
            }
      ).then(response => response.json()
      ).then(data => {
                window.channelsInfo = data;
                fillChatInfo('#channels', 'channel');
                fillChatInfo('#groups', 'group');
                fillMsgCounts('#counts');
                fillPtsCounts('#participants');
        })
  
  
});
