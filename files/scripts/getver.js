 var xhr = new XMLHttpRequest(); 
  xhr.onreadystatechange = function() { 
    if (xhr.readyState == 4 && xhr.status == 200) { 
      document.getElementById("data").innerHTML = "("+ xhr.responseText+")"; 
    } 
  }; 
  xhr.open("GET", "https://enderminecraft.github.io/ver.txt", true); 
  xhr.send(); 