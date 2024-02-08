var images = ['bg1.jpg',
          'bg2.jpg', 
          'bg3.jpg'];
$('#bg').css({'background-image' : 'url(images/' + images[Math.floor(Math.random() * images.length)] + ')'});