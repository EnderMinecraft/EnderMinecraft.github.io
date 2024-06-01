 var xhr = new XMLHttpRequest(); 
  xhr.onreadystatechange = function() { 
    if (xhr.readyState == 4 && xhr.status == 200) { 
      document.getElementById("data").innerHTML = "("+ xhr.responseText+")"; 
    } 
  }; 
  xhr.open("GET", "https://enderminecraft.github.io/ver.txt", true); 
  xhr.send(); 
 var xhr1 = new XMLHttpRequest(); 
  xhr1.onreadystatechange = function() { 
    if (xhr1.readyState == 4 && xhr1.status == 200) { 
      document.getElementById("data1").innerHTML = "("+ xhr1.responseText+")"; 
    } 
  }; 
  xhr1.open("GET", "https://enderminecraft.github.io/vercrckdnbr.txt", true); 
  xhr1.send(); 
