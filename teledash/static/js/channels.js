var intervalId;

const form = document.querySelector('form');
//form.addEventListener('submit', handleSubmit);


function showChannels(data, title='Collection Title'){
  if (!data.length){
    return 
  }
  // $('#results-table').html("");
  $('#results-table_wrapper').remove();
  $('#table-container').html(`<table id="results-table" class="display" cellspacing="0" width="100%">
  </table>`);
  // if (window.dtable){
  //   window.dtable.destroy();
  // }

    let columns = []
    $.each( data[0], function( key, value ) {
      var my_item = {};
      my_item.data = key;
      my_item.title = key;
      columns.push(my_item);
});
  try {
    window.dtable = $('#results-table').DataTable({
      "binfo": true,
      "sDom": '<"header"if>tp<"Footer">',
      "oLanguage": {
          "sInfo": `Showing channels from: ${title}`
      },
      destroy: true,
      data: data,
      "columns": columns
    });
  } catch(err){
    console.log(err)
  }
};



const fileSubmit = document.getElementById('file-table-submit');
fileSubmit.onclick = (ev) => {
    ev.preventDefault();
    let form = document.getElementById('file-table-form');
    let data = new FormData(form);

    fetch('/api/v1/collections/uploadfile', {
        method: 'POST',
        body: data
    }).then((response) => {
      if (response.ok) {
        return response.json()
      }
      return response.json().then((data) => {throw new Error(data.detail)})
      })
    .then((data) => {
      window.dataTable = data;
      console.log(window.dataTable)
      showChannels(window.dataTable.rows, 'Uploaded file');
      $('#collection').show();
      
    }
    )
    .catch((err) => {
        console.log('Error: ', err);
        window.alert(`File could not be parsed. Possible reasons:
          - not a valid csv, tsv, xlsx, xls
          - spreadsheet does not contain the columns: url, category, location, language
          - the required url field is missing for some rows 
        `)
    })

};


/* $('#collection-submit').click(function(ev){
  ev.preventDefault();  
  let form = document.getElementById('collection-form');
  let data = new FormData(form);
  let collectionTitle = data.get('collection-title');
  let channels = window.dataTable.rows.map(function(x) {
    return {"url": x.url};
  });


  const baseUrl = '/api/list_of_channels';
  const baseCollectionUrl = '/api/channel_collection'
  const queryParams = {"client_id": window.activeClient};
  const queryString = new URLSearchParams(queryParams).toString();


  fetch(`${baseUrl}?${queryString}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json' 
    },
    body: JSON.stringify(channels)
    }).then((response) => response.json())
    .then((data) => {
      console.log(data)
    }
    )
    .catch((err) => {
        console.log('Error: ', err);
    })

    let collPayload = {
      "collection_title": collectionTitle,
      "channel_urls": channels
    };

    window.pay = collPayload;
    window.form = data;
    window.colltitle = collectionTitle;
    fetch(`${baseCollectionUrl}?${queryString}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json' 
      },
      body: JSON.stringify(collPayload)
      }).then((response) => response.json())
      .then((data) => {
        console.log(data)
      }
      )
      .catch((err) => {
          console.log('Error: ', err);
      })
  
}); */


// implementation of websocket: the problem is that if the user changes page the 
// connection will close, so it's better a polling approach

/* $('#collection-submit').click(function(ev){
  try {
    ev.preventDefault();
    let form = document.getElementById('collection-form');
    let data = new FormData(form);
    let collectionTitle = data.get('collection-title');
    
    let channels = window.dataTable.rows.map(function(x) {
      return x.url;
    });
    let queryString = jQuery.param(
      {
        client_id: window.activeClient,
        channels: channels
      }, traditional=true
    )
    var ws = new WebSocket(`ws://${window.location.host}/api/list_of_channels_ws?${queryString}`);
    ws.onmessage = function(event) {
      console.log(event.data);
      let channelResult = JSON.parse(event.data);
      $('#collection-status').append(channelResult.url);
      console.log(channelResult.index, channelResult.n_channels)
      if (channelResult.index == channelResult.n_channels){
        console.log("saving")
        let baseCollectionUrl = '/api/channel_collection';
        let queryParams = {"client_id": window.activeClient};
        let queryString = new URLSearchParams(queryParams).toString();
        let channels = window.dataTable.rows.map(function(x) {
          return {'url': x.url};
        });
        let collPayload = {
          "collection_title": collectionTitle,
          "channel_urls": channels
        };
        fetch(`${baseCollectionUrl}?${queryString}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json' 
          },
          body: JSON.stringify(collPayload)
          })
          .then((response) => response.json())
          .then((data) => {
            console.log(data)
          }
          )
          .catch((err) => {
              console.log('Error: ', err);
          })
      }

    };
  } catch(error) {
    console.log(error)
  };
});
 */






/* function handleSubmit(event) {
    // taken from https://www.freecodecamp.org/news/upload-files-with-javascript/

    
    event.preventDefault();
    const form = event.currentTarget;
    const url = new URL(form.action);
    const formData = new FormData(form);
    const searchParams = new URLSearchParams(formData);
  
    
    const fetchOptions = {
      method: form.method,
    };
  
    if (form.method.toLowerCase() === 'post') {
      if (form.enctype === 'multipart/form-data') {
        fetchOptions.body = formData;
      } else {
        fetchOptions.body = searchParams;
      }
    } else {
      url.search = searchParams;
    }
  
    fetch(url, fetchOptions)
    .then(response => response.json())
    .then(data => {showChannels(data)})
  
  }; 
*/

async function fetchStatus(uid) {
  let baseURL = `/api/work/${uid}/status`;
  fetch(baseURL)
  .then((response) => response.json())
  .then((data) => {
    let channels = data.processed_channels;
    let latest = (channels.length > 0) ? channels[channels.length - 1] : null;
    console.log(channels, latest)
    if (latest != null) {
      $('#collection-status').text(
        `Last processed channel [${latest.index}/${latest.n_channels}]: ${latest.url}`
      );
      if (latest.index == latest.n_channels){
        $('#collection-status').append(
          `Process [${uid}] successfully completed`
        );
        clearInterval(intervalId);
      }
    };
  })
};  

$('#collection-submit').click(function(ev){
  // $('#collection-submit').prop('disabled', true);
  try {
    if (!window.activeClient.client_id){
      throw new Error('No Telegram accounts registered on your account. Go to "Clients" page')
    }
    $(':button').prop('disabled', true);
    ev.preventDefault();
    
    let form = document.getElementById('collection-form');
    let data = new FormData(form);
    var collectionTitle = data.get('collection-title');
    if (collectionTitle === ""){
      throw new Error('Set a Collection title before submitting')
    }
    $('#collection-status').text(`Saving collection with title: ${collectionTitle}`);
    let channels = window.dataTable.rows.map(function(x) {
      return x.url.trim();
    });

    let channelcreate_items = window.dataTable.rows.map(function(x){
      return {"url": x.url.trim()}
    });
    let payload = JSON.stringify(
      {"collection_title": collectionTitle, "channel_urls": channelcreate_items}
    )
    
    
    let initPayload = JSON.stringify(
      window.dataTable.rows.map(function(x){
        return {
          channel_url: x.url.trim(), 
          category: x.category, 
          language: x.language, 
          location: x.location
        }
      })
    );
    let postCollectionPayload = JSON.stringify({
      "title": collectionTitle,
      "channels": window.dataTable.rows.map(function(x){
        return {
          channel_url: x.url.trim(), 
          category: x.category, 
          language: x.language, 
          location: x.location
        }
      })}
    );
    fetch(`/api/v1/collections/item/${collectionTitle}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: postCollectionPayload
    }).then(
      (response) => {
        if (response.ok) {
          return response.json()
        }
        throw new Error(`Error inserting channels in db. Collection not saved`)
      }
    ).then((data) => {
      let el = `<option value=${collectionTitle}>` + collectionTitle + '</option>';
      $('#collection-titles').append(el);
      
      console.log("saved collection in user account")
      console.log(data)
      $('#collection-submit').prop('disabled', false);
      $(':button').prop('disabled', false);
      $('#collection').hide();
      if (!window.activeCollection){
        setActiveCollection(collectionTitle);
        window.alert(`Channels from file saved in "${collectionTitle}" collection. The collection is now the current active collection`)
      }else{
      window.alert(`Channels from file saved in "${collectionTitle}" collection`)
      }
      
      }).catch((err) => {

        $('#collection-submit').prop('disabled', false);
        $(':button').prop('disabled', false);
        if ($('#collection-titles').find('option').length === 0){
          $('#submit-active-collection').prop('disabled', true);
        };
        window.alert(err)
        console.log('Error: ', err);
      });

    // fetch(`/api/init_many_channels_to_db`, {
    //   method: "POST",
    //   headers: {
    //     'Content-Type': 'application/json' 
    //   },
    //   body: initPayload
    // }).then(
    //   (response) => {
    //     if (response.ok) {
    //       return response.json()
    //     }
    //     throw new Error('Error inserting channels in db. Collection not saved')
    //     }
    // ).then((data) => {
    //   let el = `<option value=${collectionTitle}>` + collectionTitle + '</option>';
    //   $('#collection-titles').append(el);
      
    //   console.log("saved collection in user account")
    //   console.log(data)
    //   $('#collection-submit').prop('disabled', false);
    //   $(':button').prop('disabled', false);
    //   $('#collection').hide();
    //   if (!window.activeCollection){
    //     setActiveCollection(collectionTitle);
    //     window.alert(`Channels from file saved in "${collectionTitle}" collection. The collection is now the current active collection`)
    //   }else{
    //   window.alert(`Channels from file saved in "${collectionTitle}" collection`)
    //   }
    // })
      
    //   console.log("channels initiated if not already")
    //   console.log(data)
    //   fetch(`/api/channel_collection?client_id=${window.activeClient.client_id}`,{
    //     method: "POST",
    //     headers: {
    //       'Content-Type': 'application/json' 
    //     },
    //     body: payload
    //     }).then(
    //       (response) => {
    //         if (response.ok) {
    //           return response.json();
    //         }
            
            
    //         throw new Error('Collection not added. Possible reasons: client not registered, title already present in your account');
    //       }
    //     ).then((data) => {

    //       let el = `<option value=${collectionTitle}>` + collectionTitle + '</option>';
    //       $('#collection-titles').append(el);
          
    //       console.log("saved collection in user account")
    //       console.log(data)
    //       $('#collection-submit').prop('disabled', false);
    //       $(':button').prop('disabled', false);
    //       $('#collection').hide();
    //       if (!window.activeCollection){
    //         setActiveCollection(collectionTitle);
    //         window.alert(`Channels from file saved in "${collectionTitle}" collection. The collection is now the current active collection`)
    //       }else{
    //       window.alert(`Channels from file saved in "${collectionTitle}" collection`)
    //       }
    //       let title = $('#collection-titles').val();
    //       let queryString = jQuery.param(
    //         {
    //           client_id: window.activeClient.client_id,
    //           collection: title,
    //           period: 60*60
    //         },
    //         traditional=true
    //       )
    //       fetch(`/api/set_chat_update_task?${queryString}`,
    //         {
    //           method: "PUT",
    //           headers: {
    //             'Content-Type': 'application/json' 
    //           }
    //         }).then((response) => response.json())
    //         .then((data) => {
    //           console.log("Set job to update all channels")
    //           console.log(data)
    //         })
    //     })
    //     .catch((err) => {

    //       $('#collection-submit').prop('disabled', false);
    //       $(':button').prop('disabled', false);
    //       if ($('#submit-active-collection').find('option').length === 0){
    //         $('#submit-active-collection').prop('disabled', true);
    //       };
    //       window.alert(err)
    //       console.log('Error: ', err);
    //     });
    
    // })
    // .catch((err) => {
    //   $('#collection-submit').prop('disabled', false);
    //   if ($('#submit-active-collection').find('option').length === 0){
    //     $('#submit-active-collection').prop('disabled', true);
    //   };
    //   console.log('Error: ', err);
    // });
  } catch (error) {
    window.alert(error);
    $('#collection-submit').prop('disabled', false);
    $(':button').prop('disabled', false);
    if ($('#collection-titles').find('option').length === 0){
      $('#submit-active-collection').prop('disabled', true);
    };
    console.log("Error: ", error)
  }
  });


async function getJobs(){
  fetch('/api/collection_jobs_of_user')
  .then((response) => response.json())
  .then((data) => {
    console.log(data);
    data.forEach((d) => {
      let el = `<option value=${d}>` + d.uid + '</option>';
      $('#jobs-queue').append(el);
    });
  })

};


async function showActiveCollection(){
  fetch(`/api/v1/collections/active`, {
    method: "GET",
    headers: {
      'Content-Type': 'application/json' 
    }
  })
  .then((response) => response.json())
  .then(data => {
    window.activeCollection = data;
    $('#active-collection').html(data);
    $('#nav-active-collection').html(data);
    }
)};

async function setActiveCollection(title){
  fetch(`/api/v1/collections/set_active?collection_title=${title}`, 
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json' 
      }
    }
  ).then((response) =>{
    showActiveCollection();
    // update metadata of the active collection
    fetch(`/api/v1/collections/item/${title}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json' 
        }
      }
    )
    
  })
}

async function deleteCollection(title){

  fetch(`/api/v1/collections/item/${title}`,
    {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    }
  ).then((response) =>{
    console.log("deleted", title)
  })
}

$('#submit-active-collection').click(function(){
  $('[collection-button]').prop('disabled', true);
  let  title = $('#collection-titles').val();
  setActiveCollection(title);
  $('[collection-button]').prop('disabled', false);    
});

$('#delete-collection').click(function(){
  let title = $('#collection-titles').val();
  if (!title){
    window.alert("There is no collection to delete");
    return;
  }
  let text = "Press Ok to confirm that you want to delete it";
  if (confirm(text) == true){
    $('[collection-button]').prop('disabled', true);
    deleteCollection(title);
    $('#collection-titles').find(`option[value=${title}]`).remove();
    if (window.activeCollection == title) {
      window.activeCollection = null;
      $('#active-collection').html("None");
      $('#nav-active-collection').html(null);
    };
    $('[collection-button]').prop('disabled', false);
  }
});

$('#collection-titles').on('click change', function(){
  let title = $('#collection-titles').find(":selected").val();

  showCollectionInTable(title);
})


async function showCollectionInTable(collectionTitle){
  console.log(collectionTitle)
  fetch(`/api/v1/collections/item/${collectionTitle}`, {
    method: 'GET',
    headers: {
    'Content-Type': 'application/json' 
    }}
  ).then((response) => response.json())
    .then((data) => {
      console.log(data)
      let cleanData = data.data.map((o) => {
        let { channel_url, ...clean } = o;
        return clean;
      })
      window.dataTable = cleanData;
      console.log(cleanData, collectionTitle)
      showChannels(cleanData, collectionTitle);
    })
    .catch((err) => {
        console.log('Error: ', err);
    });
}

$(window).on('load', function(){
  $('#collection').hide();
  //getJobs();

  fetch('/api/v1/collections/all', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json' 
      }
    })
    .then((response) => response.json())
    .then((data) => {
      window.select_coll = data;
      console.log("data", data)
      if (data.data.length == 0){
        $('#submit-active-collection').prop('disabled', true);
      }
      data.data.forEach((d) => {

        let sel = (d == window.activeCollection) ? 'selected' : '';      
        let el = `<option value="${d}" ${sel}>` + d + '</option>';
        $('#collection-titles').append(el);
        
      })
      try{
        let title = window.activeCollection ? window.activeCollection : $('#collection-titles').val();
        showCollectionInTable(title);
      } catch(error) {
        console.log(error)
      }
      if (window.activeCollection){
        showActiveCollection();
      }

      ;
    })
    .catch((err) => {
      console.log('Error: ', err);
    });

    
});

function exportDataTableToTSV(){

  if (!window.dataTable){
    return
  }
  let header = Object.keys(window.dataTable[0]);
  let tsv = "";
  tsv += header.join("\t") + "\n";
  window.dataTable.forEach(function(item){
    let row = header.map(function(col){
      return item[col];
    }).join("\t");
    tsv += row + "\n";
  })
  // Crea un oggetto Blob per il contenuto TSV
  var blob = new Blob([tsv], { type: "text/tab-separated-values" });

  // Crea un URL per il Blob
  var url = window.URL.createObjectURL(blob);

  // Crea un elemento <a> per il download del file
  var a = document.createElement("a");
  a.href = url;

  // create filename
  let title = $('#collection-titles').val();
  let fname = "collection_export.tsv"
  if (title) {
    fname = `${title}.tsv`  
  } 
  

  a.download = fname;

  // Simula un clic sull'elemento <a> per avviare il download
  a.click();

  // Rilascia l'URL dell'oggetto Blob
  window.URL.revokeObjectURL(url);
}



function exportTableToTSV() {
  // Ottieni il riferimento alla tabella
  var tabella = document.getElementById("results-table");

  // Inizializza una stringa per i dati TSV
  var tsvData = [];

  // Loop attraverso le righe della tabella
  var righe = tabella.rows;
  for (var i = 0; i < righe.length; i++) {
    var riga = righe[i];
    var datiRiga = [];

    // Loop attraverso le celle della riga
    var celle = riga.cells;
    for (var j = 0; j < celle.length; j++) {
      var cella = celle[j];
      datiRiga.push(cella.textContent);
    }

    // Unisci i dati della riga con un separatore di tabulazione
    tsvData.push(datiRiga.join("\t"));
  }

  // Unisci tutte le righe TSV in una stringa completa
  var tsvContent = tsvData.join("\n");

  // Crea un oggetto Blob per il contenuto TSV
  var blob = new Blob([tsvContent], { type: "text/tab-separated-values" });

  // Crea un URL per il Blob
  var url = window.URL.createObjectURL(blob);

  // Crea un elemento <a> per il download del file
  var a = document.createElement("a");
  a.href = url;

  // create filename
  let title = $('#collection-titles').val();
  let fname = "collection_export.tsv"
  if (title) {
    fname = `${title}.tsv`  
  } 
  

  a.download = fname;

  // Simula un clic sull'elemento <a> per avviare il download
  a.click();

  // Rilascia l'URL dell'oggetto Blob
  window.URL.revokeObjectURL(url);
}



