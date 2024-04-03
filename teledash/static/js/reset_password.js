const clientForm = document.getElementById('signupForm');
var password = document.getElementById("password")
  , confirm_password = document.getElementById("confirmPassword");

// document.getElementById('signupLogo').src = "https://s3-us-west-2.amazonaws.com/shipsy-public-assets/shipsy/SHIPSY_LOGO_BIRD_BLUE.png";
enableSubmitButton();

function validatePassword() {
  if(password.value != confirm_password.value) {
    confirm_password.setCustomValidity("Passwords Don't Match");
    return false;
  } else {
    confirm_password.setCustomValidity('');
    return true;
  }
}

password.onchange = validatePassword;
confirm_password.onkeyup = validatePassword;

function enableSubmitButton() {
  document.getElementById('submitButton').disabled = false;
  document.getElementById('loader').style.display = 'none';
}

function disableSubmitButton() {
  document.getElementById('submitButton').disabled = true;
  document.getElementById('loader').style.display = 'unset';
}

function validateSignupForm() {
  console.log("validating form")
  var form = document.getElementById('signupForm');
  
  for(var i=0; i < form.elements.length; i++){
      if(form.elements[i].value === '' && form.elements[i].hasAttribute('required')){
        console.log('There are some required fields!');
        return false;
      }
    }
  
  if (!validatePassword()) {
    return false;
  }
  resetPassword();
  // onSignup();
}

function onSignup() {
    let params = (new URL(window.location)).searchParams;
    let token = params.get('ac');
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    
    disableSubmitButton();
    
    if (this.readyState == 4 && this.status == 200) {
      enableSubmitButton();
    }
    else {
      console.log('AJAX call failed!');
      setTimeout(function(){
        enableSubmitButton();
      }, 1000);
    }
    
  };
  
  xhttp.open("GET", "/reset_password" + "?", true);
  xhttp.send();
}



function resetPassword(){
    disableSubmitButton();
    let params = (new URL(window.location)).searchParams;
    let token = params.get('ac');
    let data = new FormData(clientForm);
    let pwd = data.get('password');

    payFormData = new FormData()
    let payload = {
        'token': token,
        'password': pwd
    }
    // Object.keys(payload).forEach(key => payFormData.append(key, payload[key]));
    fetch("/v1/auth/reset-password",
        {
            method: "POST",
            headers: {
                'accept': 'application/json',
                'Content-Type': 'application/json'
              },
            body: JSON.stringify(payload)
        }).then((response) => {
            console.log(response.status)
            if (response.status != 200) {
                window.alert(`The password has not been reset.
                 The request link you used has probably expired. 
                 Try to ask TeleCatch to send another email with a new link`)
            } else {
                let mainDiv = document.getElementById('mainDiv');
                mainDiv.innerHTML = "<h3> Password reset with success </h3>";
                // window.alert("Password reset with success")
            }
        })
        .catch((err) => {
            enableSubmitButton();
            window.alert(err);
        })
    enableSubmitButton();
}