function upVote(self, post_key){
  $.get('/upvote/' + post_key, function(data) {
    if (data == 'Ok'){
      self.className += " voted";
    } else if (data == 'Bad'){
      window.location = "/login"
    }
  });
}
function upVoteComment(self, post_key){
  $.get('/upvote_comment/' + post_key, function(data) {
    if (data == 'Ok'){
      self.className += " voted";
    } else if (data == 'Bad'){
      window.location = "/login"
    }
  });
}

/**
 * Simple validacion de http://www.anieto2k.com/2008/06/25/validar-formularios-con-jquery/
 */
var filters = {
    requerido: function(el) {return ($(el).val() != '' && $(el).val() != -1);},
    email: function(el) {return /^[A-Za-z][A-Za-z0-9_]*@[A-Za-z0-9_]+\.[A-Za-z0-9_.]+[A-za-z]$/.test($(el).val());},
    telefono: function(el){return /^[0-9]*$/.test($(el).val());}};

// Extensiones
$.extend({
  stop: function(e){
    if (e.preventDefault) e.preventDefault();
    if (e.stopPropagation) e.stopPropagation();
  }
});

$(document).ready(function() {
  $("form.validable").bind("submit", function(e){
  	if (typeof filters == 'undefined') return;
    $(this).find("input, textarea, select").each(function(x,el){
      if ($(el).attr("className") != 'undefined') {
        $.each(new String($(el).attr("className")).split(" "), function(x, klass){
          if ($.isFunction(filters[klass]))
            if (!filters[klass](el))  $(el).addClass("fielderror");
        });
      }
    });
    if ($(this).find(".fielderror").size() > 0) {
      $.stop(e || window.event);
      return false;
    }
    return true;
  });

  $('.fielderror').live('blur', function() {
    if ($(this).val() != '') {
      $(this).removeClass('fielderror');
    }
  });
});
