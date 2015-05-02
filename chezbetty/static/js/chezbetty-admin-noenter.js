$(document).ready(function() {
  $(window).keydown(function(event){
    if(event.which === 13) {
      event.preventDefault();
      return false;
    }
  });
});
