function upVote(self, post_key){
  $.get('/upvote/' + post_key, function(data) {
    if (data == 'Ok'){
      self.className += " voted";
    } else if (data == 'Bad'){
      window.location = "/login"
    }
  });
}

function downVote(self, post_key){
  $.get('/downvote/' + post_key, function(data) {
    if (data == 'Ok'){
      self.className += " voted";
    } else if (data == 'Bad'){
      window.location = "/login"
    }
  });
}

