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

    fetch('/uploadfile', {
        method: 'POST',
        body: data
    }).then((response) => response.json())
    .then((data) => {
      window.dataTable = data;
      console.log(window.dataTable)
      showChannels(window.dataTable.rows, 'Uploaded file');
      $('#collection').show();
      
    }
    )
    .catch((err) => {
        console.log('Error: ', err);
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
  $('#collection-submit').prop('disabled', true);
  ev.preventDefault();

  let form = document.getElementById('collection-form');
  let data = new FormData(form);
  var collectionTitle = data.get('collection-title');
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

  fetch(`/api/init_many_channels_to_db`, {
    method: "POST",
    headers: {
      'Content-Type': 'application/json' 
    },
    body: initPayload
  }).then(
    (response) => {
      if (response.ok) {
        return response.json()
      }
      throw new Error('Error inserting channels in db. Collection not saved')
      }
  ).then((data) => {
    
    console.log("channels initiated if not already")
    console.log(data)
    fetch(`/api/channel_collection?client_id=${window.activeClient}`,{
      method: "POST",
      headers: {
        'Content-Type': 'application/json' 
      },
      body: payload
      }).then(
        (response) => {
          if (response.ok) {
            return response.json();
          }
          
          
          throw new Error('Collection title already present in user account. Set a different title');
         }
      ).then((data) => {

        let el = `<option value=${collectionTitle}>` + collectionTitle + '</option>';
        $('#collection-titles').append(el);
        
        console.log("saved collection in user account")
        console.log(data)
        $('#collection-submit').prop('disabled', false);
        $('#collection').hide();
        if (!window.activeCollection){
          setActiveCollection(collectionTitle);
          window.alert(`Channels from file saved in "${collectionTitle}" collection. The collection is now the current active collection`)
        }else{
         window.alert(`Channels from file saved in "${collectionTitle}" collection`)
        }
        let title = $('#collection-titles').val();
        let queryString = jQuery.param(
          {
            client_id: window.activeClient,
            collection: title,
            period: 60*60
          },
          traditional=true
        )
        fetch(`/api/set_chat_update_task?${queryString}`,
          {
            method: "PUT",
            headers: {
              'Content-Type': 'application/json' 
            }
          }).then((response) => response.json())
          .then((data) => {
            console.log("Set job to update all channels")
            console.log(data)
          })
      })
      .catch((err) => {

        $('#collection-submit').prop('disabled', false);
        window.alert(err)
        console.log('Error: ', err);
      });
  })
  .catch((err) => {
    $('#collection-submit').prop('disabled', false);
    console.log('Error: ', err);
  });

  

  
  // const baseUrl = '/api/channels_collection_background';
  // const queryString = jQuery.param(
  //   {
  //     client_id: window.activeClient,
  //     collection_title: collectionTitle
  //   },
  //   traditional=true
  //   );
  // fetch(`${baseUrl}?${queryString}`, {
  //   method: 'POST',
  //   headers: {
  //     'Content-Type': 'application/json' 
  //   },
  //   body: JSON.stringify(channels)
  //   }).then((response) => response.json())
  //   .then((data) => {
  //     if (data.detail){
  //       window.alert(data.detail)
  //     }
  //     console.log(data);
  //     let taskUid = data.uid;
  //     $('#collection-status').text(
  //       `Started process with uid: ${taskUid}`
  //     );
  //     intervalId = setInterval(fetchStatus, 2000, taskUid);
  //   }
  //   )
  //   .catch((err) => {
  //       console.log('Error: ', err);
  //   })


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
  fetch(`/api/active_collection_of_user`, {
    method: "GET",
    headers: {
      'Content-Type': 'application/json' 
    }
  })
  .then((response) => response.json())
  .then(data => {
    $('#active-collection').html(data);
    $('#nav-active-collection').html(data);
    }
)};

async function setActiveCollection(title){
  fetch(`/api/set_active_collection_of_user?collection_title=${title}`, 
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json' 
      }
    }
  ).then((response) =>{
    
    showActiveCollection();
    $('#submit-active-collection').prop('disabled', false);
    
  })
}


$('#submit-active-collection').click(function(){
  $('#submit-active-collection').prop('disabled', true);
  let  title = $('#collection-titles').val();
  setActiveCollection(title)
});

$('#collection-titles').change(function(){
  let title = $('#collection-titles').find(":selected").val();
  console.log(title)
  showCollectionInTable(title);
})


async function showCollectionInTable(collectionTitle){
  fetch(`/api/channel_collection_by_title?collection_title=${collectionTitle}`, {
    headers: {
    'Content-Type': 'application/json' 
    }}
  ).then((response) => response.json())
    .then((data) => {
      let cleanData = data.data.map((o) => {
        let { channel_url, ...clean } = o;
        return clean;
      })
      showChannels(cleanData, collectionTitle);
    })
    .catch((err) => {
        console.log('Error: ', err);
    });
}

$(window).on('load', function(){
  $('#collection').hide();
  //getJobs();

  fetch('/api/channel_collections_of_user', {
      headers: {
        'Content-Type': 'application/json' 
      }
    })
    .then((response) => response.json())
    .then((data) => {

      data.data.forEach((d) => {
        let sel = (d == window.activeCollection) ? 'selected' : '';      
        let el = `<option value=${d} ${sel}>` + d + '</option>';
        $('#collection-titles').append(el);
        
      });
    })
    .catch((err) => {
      console.log('Error: ', err);
    });
    try{
      showCollectionInTable(window.activeCollection);
    } catch(error) {
      console.log(error)
    }
    if (window.activeCollection){
      showActiveCollection();
    }

    
});



