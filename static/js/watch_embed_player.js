/**
 * YouTube embed via IFrame API — detects error 101/150 (embedding disabled)
 * and shows a fallback with direct watch link. Exposes global playYt(id).
 */
(function () {
  var root = document.getElementById('watch-player-root');
  if (!root) return;

  var containerId = 'watch-yt-player';
  var ytPlayer = null;
  var currentVid = root.getAttribute('data-first-video') || '';

  function showFallback(vid) {
    var fb = document.getElementById('yt-embed-fallback');
    var link = document.getElementById('yt-watch-direct');
    if (link && vid) link.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(vid);
    if (fb) fb.classList.remove('hidden');
  }

  function hideFallback() {
    var fb = document.getElementById('yt-embed-fallback');
    if (fb) fb.classList.add('hidden');
  }

  window.playYt = function (id) {
    if (!id) return;
    currentVid = id;
    hideFallback();
    var link = document.getElementById('yt-watch-direct');
    if (link) link.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(id);
    if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
      ytPlayer.loadVideoById(id);
    }
  };

  window.onYouTubeIframeAPIReady = function () {
    if (!currentVid) return;
    ytPlayer = new YT.Player(containerId, {
      videoId: currentVid,
      width: '100%',
      height: '100%',
      playerVars: {
        modestbranding: 1,
        rel: 0,
        playsinline: 1,
      },
      events: {
        onError: function () {
          showFallback(currentVid);
        },
      },
    });
  };

  var tag = document.createElement('script');
  tag.src = 'https://www.youtube.com/iframe_api';
  var first = document.getElementsByTagName('script')[0];
  first.parentNode.insertBefore(tag, first);
})();
