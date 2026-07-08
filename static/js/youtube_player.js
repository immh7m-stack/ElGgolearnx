let player;

function onYouTubeIframeAPIReady() {
  const el = document.getElementById('youtube-player');
  if (!el) return;
  const playlistId = el.dataset.playlistId;
  player = new YT.Player('youtube-player', {
    height: '100%',
    width: '100%',
    playerVars: {
      listType: 'playlist',
      list: playlistId,
      rel: 0,
      modestbranding: 1,
    },
  });
}

window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;
