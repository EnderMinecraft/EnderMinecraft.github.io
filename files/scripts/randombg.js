var images = ["bg1.jpg","bg2.jpg","bg3.jpg"];
$('body').css({'background-image' : 'url(https://enderminecraft.github.io/files/images/' + images[Math.floor(Math.random() * images.length)] + ')'});
