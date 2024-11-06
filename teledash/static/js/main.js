var tableMessages = [];
// Numero di righe da visualizzare per pagina
var rowsPerPage = 10;
  
// Selettore della tabella e del contenitore di paginazione
var tableSelector = '#results-table';
var paginationSelector = '#pagination';
var input = document.getElementById("inpt_search");
var resultTableBody = document.querySelector("#results-table tbody");

// let collection = window.activeCollection;
// let collection_response = await fetch(`/api/channel_collection_by_title?collection_title=${collection}`).then((response) => response.json())
// var channelUrls = collection_response.data.map(x => x.url);
    


$("#inpt_search").on('focus', function () {
	$(this).parent('label').addClass('active');
});

$("#inpt_search").on('blur', function () {
	if($(this).val().length == 0)
		$(this).parent('label').removeClass('active');
});


$('#submitButton').on("click", async function() {
  try {
    if (!window.activeClient.client_id){
      throw new Error(`There is no active client set. Possibile reasons:
      - you still need to register an account
      - a registered and active client has been inactive for a long time 
      - unknown authentication errors related to the active client occurred

      Go to "Clients" page to register a new account o register an old account again.`)
    }
    if (!window.activeCollection){
      throw new Error(`No channel collection set. Possible reasons:
        - you still need to upload and save the first collection
        - you deleted the active collection
        - something went wrong when selecting the active collection (empty title, other unknown reasons)
        
        Go to the "Collections" page to set a valid active collection`)
    }
    $('#results-table').attr('data-page', 1);
    let search = $('#inpt_search').val();
    let start_date = $('#start-date').val();
    let end_date = $('#end-date').val();
    let chat_type = $('#chat-type').val();
    let country = null;
    let data_range = $('#data-range').val();
    let export_format = $('#export-format').val();
   
    
    window.search = search;
    window.start_date = start_date || null;
    window.end_date = end_date || null;
    window.chat_type = chat_type;
    window.country = country;
    window.data_range = parseInt(data_range);
    window.limit = window.data_range ? -1 : 40;
    window.export_format = export_format;
    window.media = export_format == 'zip' ? true : false;
    
    /* let limit = parseInt($('#inpt_limit').val(), 10) || 100;
    if (limit > 1000){
      limit = 1000;
    } */
    // Chiamata all'API con il valore dell'input
    window.tableMessages = [];
    
    let selectedUrls = $('#channels').val();
    window.urlsToSearch = selectedUrls.length == 0 ? window.channelUrls : selectedUrls
    if (!window.data_range){
      let endPoint = Object.is(window.data_range, -0) ? '/api/v1/sample' : '/api/v1/search';
      callAPI(search, window.limit, 0, 0, 
        window.start_date, window.end_date, 
        window.chat_type, window.country, window.activeClient.client_id, 
        window.urlsToSearch, endPoint
        );
    } else {
      await export_search();
    }
  } catch (error) {
    window.alert(error)
  }
  });



function callAPI(
  value, 
  limit=40, 
  offset_channel=0, 
  offset_id=0,
  start_date, 
  end_date, 
  chat_type,
  country, 
  client_id,
  channel_urls,
  endpoint="/api/v1/search"
  ) {
  emptyTableHeight = 30*rowsPerPage;
  resultTableBody.innerHTML = `<div class="container" style="height: ${emptyTableHeight}px;>
    <span class="loader centered">Loading...</span>
    </div>
    `;

  let queryString = jQuery.param({
     q: value,
     limit: limit,
     offset_channel: offset_channel,
     offset_id: offset_id,
     start_date: start_date,
     end_date: end_date,
     chat_type: chat_type,
     country: country,
     client_id: client_id,
     source: channel_urls
    },
    traditional=true
  );
  fetch(
    `${endpoint}?${queryString}`,
    {
        headers: {
          'Cache-Control': 'no-cache'
        }}
    )
    .then((response) => {
      if (response.ok) {
        return response.json()
      }
      throw new Error('Something went wrong but I dont know what')
    }
    )
    .then(data => {
      if (data.length == 0){ // no more data to show
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
        // const countryCell = document.createElement("td");
        const viewsCell = document.createElement("td");


        channelCell.textContent = item.username;
        messageCell.textContent = item.message;
        timestampCell.textContent = item.timestamp;
        typeCell.textContent = item.type;
        // countryCell.textContent = item.country;
        viewsCell.textContent = item.views;

        row.appendChild(channelCell);
        row.appendChild(messageCell);
        row.appendChild(timestampCell);
        row.appendChild(typeCell);
        //row.appendChild(countryCell);
        row.appendChild(viewsCell);

        resultTableBody.appendChild(row);
      });
      createHistogramFromMessages(window.tableMessages);
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
    $('#page-first').hide();
    $('#page-dw').hide();
    $('#page-up').hide();
    $('#page-last').hide();
    $('#page-number').html(pageNumber);
    // Aggiungi il pulsante "Pagina precedente" se non è la prima pagina
    if (pageNumber > 1) {
      $('#page-first').show();
      $('#page-dw').show();
    } 

    // Aggiungi il pulsante "Pagina successiva" se non è l'ultima pagina
    if (pageNumber < totalPages) {
      $('#page-up').show();
      $('#page-last').show();
    }

    if (pageNumber == totalPages && window.messagesDone == false && (Object.is(window.data_range, 0))){
        let offset_channel = window.urlsToSearch.indexOf(
            window.tableMessages.slice(-1)[0].username
        );
        let offset_id = window.tableMessages.slice(-1)[0].id;
        callAPI(
          window.search, window.limit, 
          offset_channel, offset_id, 
          window.start_date, window.end_date,
          window.chat_type, window.country, window.activeClient.client_id, 
          window.urlsToSearch
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

$('#page-first').click(function(e) {
    e.preventDefault();
    let page = parseInt($('#results-table').attr('data-page'));
    $('#results-table').attr('data-page', 1);
    showRows(1, tableSelector, rowsPerPage);
    generatePagination(tableSelector, paginationSelector, 1, rowsPerPage);
});
$('#page-last').click(function(e) {
  e.preventDefault();
  let totalRows = window.tableMessages.length;
  let totalPages = Math.ceil(totalRows / rowsPerPage);
  let page = parseInt($('#results-table').attr('data-page'));
  $('#results-table').attr('data-page', totalPages);
  showRows(totalPages, tableSelector, rowsPerPage);
  generatePagination(tableSelector, paginationSelector, totalPages, rowsPerPage);
});

  function createEmptyTable(rows) {
  
    // Crea le righe vuote
    for (let i = 0; i < rows; i++) {
      let row = resultTableBody.insertRow();
      // Puoi aggiungere eventuali celle o contenuto alle righe se necessario
    }
  }


/* $('#export-messages').click(function(e){
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

}); */

async function export_search(){
  let queryString = jQuery.param({ 
    q: window.search, 
    start_date: window.start_date,
    end_date: window.end_date,
    chat_type: window.chat_type,
    country: window.country,
    limit: -1,
    offset_channel: 0,
    offset_id: 0,
    out_format: window.export_format,
    client_id: window.activeClient.client_id,
    source: window.urlsToSearch,
    with_media: window.media
  },
  traditional=true 
  );
  var url = new URL('/api/v1/export_search', window.location.origin);
  //url.search = new URLSearchParams(params).toString();
  url.search = queryString;
  window.open(url, "_blank");
  
  // fetch(`/api/stream_search?${queryString}`, {
  //   headers: {
  //     'Content-Type': 'application/json',
  //     'Cache-Control': 'no-cache',
  //   'Connection': 'keep-alive'
  //   }
  // })
};



$('#export-messages').click(function(e){

  var params = { 
    q: window.search, 
    start_date: window.start_date,
    end_date: window.end_date,
    chat_type: window.chat_type,
    country: window.country,
    limit: -1,
    offset_channel: 0,
    offset_id: 0,
    out_format: window.export_format
  };
  var url = new URL('/api/v1/export_search', window.location.origin);
  url.search = new URLSearchParams(params).toString();
  fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
    }
  })
  // .then(res => {
  //   const disposition = res.headers.get('Content-Disposition');
  //   filename = disposition.split(/;(.+)/)[1].split(/=(.+)/)[1];
  //   if (filename.toLowerCase().startsWith("utf-8''"))
  //       filename = decodeURIComponent(filename.replace("utf-8''", ''));
  //   else
  //       filename = filename.replace(/['"]/g, '');
  //   const fileStream = streamSaver.createWriteStream(filename)
  //   // more optimized
  //   /* if (window.WritableStream && readableStream.pipeTo) {
  //     return readableStream.pipeTo(fileStream)
  //       .then(() => console.log('done writing'))
  //   } */

  //   window.writer = fileStream.getWriter()

  //   const reader = res.body.getReader()
  //   const pump = () => reader.read()
  //     .then(res => res.done
  //       ? writer.close()
  //       : writer.write(res.value).then(pump))

  //   pump()
  // })
});

async function fillChatInfo(eleId, chatType){
  
  let select = $(eleId);
  select.empty();
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
  select.empty();
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
          text: `${channel.title}:  ${channel.messages_count}`,
          value: channel.identifier,
        })
      );
    });


};

async function fillPtsCounts(eleId){
  let select = $(eleId);
  select.empty();
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
          text: `${channel.title}:  ${channel.participants_count}`,
          value: channel.identifier,
        })
      );
    });
};


function initChatSelect(eleId, chatType, placeHolder){
  window.selectedChannelList = [];
  let channels = window.channelsInfo.data;
  let options = channels
    .filter(channel => channel.type === chatType)
    .map((channel) => {
    return {"label": channel.title, "value": channel.url}
  })
  placeHolder = `-- ${placeHolder} [${options.length}] --`
  VirtualSelect.init({
    ele: eleId,
    options: options,
    multiple: true,
    search: false,
    disableSelectAll: true,
    showSelectedOptionsFirst: true,
    placeholder: placeHolder
  }
  )
}


function initChatGroupsSelect(eleId){
  window.selectedChannelList = [];
  let channels = window.channelsInfo.data;
  let channelOptions = channels
    .filter(channel => channel.type === 'channel')
    .map((channel) => {
    return {"label": channel.title, "value": channel.url}
  })
  let groupOptions = channels
    .filter(channel => channel.type === 'group')
    .map((channel) => {
    return {"label": channel.title, "value": channel.url}
  })
  let undefinedOptions = channels
    .filter(channel => channel.type === 'undefined')
    .map((channel) => {
    return {"label": channel.url, "value": channel.url}
  })

  // placeHolder = `-- ${placeHolder} [${options.length}] --`
  VirtualSelect.init({
    ele: eleId,
    options: [
      {
        label: 'Channels',
        options: channelOptions
      },
      {
        label: 'Groups',
        options: groupOptions
      },
      {
        label: 'Chat type undefined',
        options: undefinedOptions
      }
    ],
    multiple: true,
    search: false,
    disableSelectAll: true,
    showSelectedOptionsFirst: true,
    placeholder: 'Chats in collection'
  }
  )
}


async function updateMonitor(){
  if (!window.activeCollection){
    return;
  }
  let queryString = jQuery.param(
    {collection_title: window.activeCollection},
    traditional=true
  )
  fetch(`/api/v1/channels/info_of_channels_in_collection?${queryString}`, 
      {
          headers: {'Cache-Control': 'no-cache'}
      }
      ).then(response => response.json()
      ).then(data => {
        window.channelsInfo = data;
        // fillChatInfo('#channels', 'channel');
        // fillChatInfo('#groups', 'group');
        // initChatSelect('#channels', 'channel', 'Channels');
        // initChatSelect('#groups', 'group', 'Groups')
        if (!$('#channels').prop('options')){
          initChatGroupsSelect('#channels')
        }
        fillMsgCounts('#counts');
        fillPtsCounts('#participants');
  })
  console.log("monitor updated")
};
  

// $('#add-chat-btn').click(function(e){
  
//   let identifier = $('#add-chat').val();
//   var resp_ok;
//     fetch('/api/channel', {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json'
//       },
//       //body: JSON.stringify(window.tableMessages)
//       body: JSON.stringify({
//         "identifier": identifier
//       })
//     })
//     .then( (response) => {
//       resp_ok = response.ok;
//       return response.json();
      
//     })
//     .then( (data) => {
//       if (resp_ok) {
//         fetch('/api/update_chat', {
//           method: 'PUT',
//           headers: {
//             'Content-Type': 'application/json'
//           },
//           body: JSON.stringify({
//             "identifier": identifier
//           })
//         })
//         .then( (count_resp) => {
//           updateMonitor();
//           return data;
//         });
      
//       }
//       else {
//         throw new Error(data.detail);
//       }
//     })
//     .catch( (error) => {
//       console.log(error)
//       alert(error)
//     })
//   }
// );


// $('#remove-chat-btn').click(function(e){
  
//   let identifier = $('#remove-chat').val();
//   var resp_ok;
//     fetch('/api/channel', {
//       method: 'DELETE',
//       headers: {
//         'Content-Type': 'application/json'
//       },
//       //body: JSON.stringify(window.tableMessages)
//       body: JSON.stringify({
//         "identifier": identifier
//       })
//     })
//     .then( (response) => {
//       resp_ok = response.ok;
//       return response.json();
      
//     })
//     .then( (data) => {
//       if (resp_ok) {
//         updateMonitor();
//         return data;
//       }
//       else {
//         throw new Error(data.detail);
//       }
//     })
//     .catch( (error) => {
//       console.log(error)
//       alert(error)
//     })
//   }
// );

function monthDiff(d1, d2) {
  let months;
  months = (d2.getFullYear() - d1.getFullYear()) * 12;
  months -= d1.getMonth();
  months += d2.getMonth();
  return months <= 0 ? 0 : months;
}

function createHistogramFromMessages(data) {
  // Imposta le dimensioni del grafico
  const width = 400;
  const height = 300;
  const margin = { top: 20, right: 30, bottom: 30, left: 40 };
  let svg;
  // append the svg object to the body of the page
  //svg.selectAll("*").remove();
  svg = d3.select('#histo').selectAll("*").remove();
  svg = d3.select("#histo")
    .append("svg")
      //.attr("width", width + margin.left + margin.right)
      //.attr("height", height + margin.top + margin.bottom)
      .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
      .attr("preserveAspectRatio", "xMinYMin meet")
      //.classed("svg-content", true)
    .append("g")
      .attr("transform",
            "translate(" + margin.left + "," + margin.top + ")");
            

  let parseTime = d3.timeParse("%Y-%m-%dT%H:%M:%S%Z");
  let dates = [];
  for (let obj of data) {
    dates.push(parseTime(obj.timestamp));
  } 
  let domain = d3.extent(dates); 
  
  let formatDate = d3.timeFormat("%Y-%m-%d");
  
  let x = d3.scaleTime().domain(domain).range([0, width]);  
  let xAxis = d3.axisBottom(x)
      //.tickFormat(formatDate);
  
  svg.append("g")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis.ticks(d3.timeDay));
  
    
  // set the parameters for the histogram
  let histogram = d3.histogram()
      .value(function(d) { return parseTime(d.timestamp); })   // I need to give the vector of value
      .domain(x.domain())  // then the domain of the graphic
      .thresholds(x.ticks(monthDiff(domain[0], domain[1]))); // then the numbers of bins

  let bins = histogram(data);
  
  // Y axis: scale and draw:
  let y = d3.scaleLinear()
      .range([height, 0])
      .domain([0, d3.max(bins, function(d) { return d.length; })]);   // d3.hist has to be called before the Y axis obviously
  svg.append("g")
      .call(d3.axisLeft(y));


  // Aggiungi le barre all'istogramma

  
  svg.selectAll('rect')
    .data(bins)
    .enter()
    .append("rect")
        .attr("x", 1)
        .attr("transform", function(d) { return "translate(" + x(d.x0) + "," + y(d.length) + ")"; })
        .attr("width", function(d) { return x(d.x1) - x(d.x0) -1 ; })
        .attr("height", function(d) { return height - y(d.length); })
        .style("fill", "#69b3a2")


  $('#histo-caption').html(
    `
    Total messages: ${data.length} <br>
    Group messages: ${window.tableMessages.reduce((acc, x) => x['type'] === 'group' ? acc + 1 : acc, 0)} <br>
    Channel messages: ${window.tableMessages.reduce((acc, x) => x['type'] === 'channel' ? acc + 1 : acc, 0)}
    `
  )

  
  /* svg_caption = d3.select('#histo-caption').selectAll("*").remove();
  svg_caption = d3.select("#histo-caption")
    .append("svg")
        //.attr("width", (width + margin.left + margin.right)/4)
        .attr("height", height + margin.top + margin.bottom)
    .append("g")
        .attr("transform",
          "translate(" + margin.left + "," + margin.top + ")");
    
  svg_caption.append("text")
      .text(`Total messages: ${data.length}` + "\n" +

        + `Group messages: ${window.tableMessages.reduce((acc, x) => x['chat_type'] === 'group' ? acc + 1 : acc, 0)}`
        + "\n" + `Channel messages: ${window.tableMessages.reduce((acc, x) => x['chat_type'] === 'channel' ? acc + 1 : acc, 0)}`)
      .attr("x",  1)
      //.attr("text-anchor", "end")
      .attr("y",  1); */
  
};


$(document).ready(function() {
  // Inizializza la paginazione
  // generatePagination(tableSelector, paginationSelector, 1, rowsPerPage);
  // showRows(1, tableSelector, rowsPerPage);
  createEmptyTable(rowsPerPage);
  updateMonitor();
  
  window.setInterval(updateMonitor, 60*60*1000);
  
});
