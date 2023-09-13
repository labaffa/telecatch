$('.form').find('input, textarea').on('keyup blur focus', function (e) {
  
    var $this = $(this),
        label = $this.prev('label');
  
        if (e.type === 'keyup') {
              if ($this.val() === '') {
            label.removeClass('active highlight');
          } else {
            label.addClass('active highlight');
          }
      } else if (e.type === 'blur') {
          if( $this.val() === '' ) {
              label.removeClass('active highlight'); 
              } else {
              label.removeClass('highlight');   
              }   
      } else if (e.type === 'focus') {
        
        if( $this.val() === '' ) {
              label.removeClass('highlight'); 
              } 
        else if( $this.val() !== '' ) {
              label.addClass('highlight');
              }
      }
  
  });
  
  $('.tab a').on('click', function (e) {
    e.preventDefault();
    
    $(this).parent().addClass('active');
    $(this).parent().siblings().removeClass('active');
    
    target = $(this).attr('href');
  
    $('.tab-content > div').not(target).hide();
    
    $(target).fadeIn(600);
    
  });


  const registerSubmit = document.getElementById("registerSubmit");
  registerSubmit.onclick = (ev) => {
    ev.preventDefault();
    const registerForm = document.getElementById("registerForm");
    const data = new FormData(registerForm);
    // convert form data to json
    let object = {}
    data.forEach((value, key) => object[key] = value)

    // send data to the backend route
    fetch("/signup", {
      method: "POST",
      body: JSON.stringify(object),
      headers: {'Content-Type': 'application/json'}
    }).then((response) => response.json())
      .then((data) => {
        const status = document.getElementById("registerStatus");
        if (data.detail) {
            status.innerText = data.detail;
        } else {
            status.innerText = "Registered with username " + data.username;
        }
      })
      .catch((err) => {
        console.log("Error: ", err)
      })
  };

  
  const loginSubmit = document.getElementById("loginSubmit");
  loginSubmit.onclick = (ev) => {
    ev.preventDefault();
    const loginForm = document.getElementById("loginForm")
    const data = new FormData(loginForm)
    fetch("/login", {
        method: "POST",
        body: data
      }).then((response) => response.json())
        .then((data) => {
          const status = document.getElementById("loginStatus");
          if (data.detail) {
              status.innerText = "Error loggin in: " + data.detail;
          } else {
              status.innerText = "Successfully logged in";

              // now we should/could one of the followings:
              //    1. set token to localstorage
              //    2. save token to cookies
              // we are not doing it now because the backend 
              // is setting cookies inside /login endpoint
              // token = `${data.token_type} ${data.access_token}`;
            let params = new URLSearchParams(window.location.search);
            let redirectURL = params.get("next");
            window.location.replace(redirectURL);
            }
        })
        .catch((err) => {
          console.log("Error: ", err)
    })

  };