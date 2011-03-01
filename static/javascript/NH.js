function upVote(post_key){
  $.get('/upvote/' + post_key, function(data) {
    console.log(data);
  });
}

function downVote(post_key){
  $.get('/downvote/' + post_key, function(data) {
    console.log(data);
  });
}

