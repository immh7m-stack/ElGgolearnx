document.addEventListener('DOMContentLoaded', () => {
  initParticlesCanvas();

  const splashScreen = document.getElementById('splash-screen');
  const isHomePage = window.location.pathname === '/home/' || window.location.pathname === '/home';
  const navType = window.performance?.getEntriesByType?.('navigation')?.[0]?.type;

  if (splashScreen && isHomePage && navType === 'reload') {
    window.addEventListener('load', () => {
      setTimeout(hideGoLearnSplash, 600);
    });
    return;
  }

  if (splashScreen && window.location.pathname === '/') {
    window.addEventListener('load', () => {
      setTimeout(hideGoLearnSplash, 600);
    });
    return;
  }

  if (splashScreen) {
    splashScreen.style.display = 'none';
  }
});

function hideGoLearnSplash() {
  const splashScreen = document.getElementById('splash-screen');
  if (!splashScreen) return;

  splashScreen.classList.add('fade-out');
  setTimeout(() => {
    splashScreen.style.display = 'none';
    if (window.location.pathname === '/') {
      window.location.replace(window.location.origin + '/home/');
    }
  }, 700);
}

function initParticlesCanvas() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = canvas.width = window.innerWidth;
  let height = canvas.height = window.innerHeight;

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const particleCount = 50;
  const particles = Array.from({ length: particleCount }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    radius: Math.random() * 1.6 + 0.3,
    alpha: Math.random() * 0.6 + 0.2,
    speedX: (Math.random() - 0.5) * 0.25,
    speedY: (Math.random() - 0.5) * 0.25,
    pulseSpeed: Math.random() * 0.015 + 0.005
  }));

  function render() {
    ctx.clearRect(0, 0, width, height);
    particles.forEach((p) => {
      p.x += p.speedX;
      p.y += p.speedY;
      p.alpha += Math.sin(Date.now() * p.pulseSpeed) * 0.004;
      if (p.alpha < 0.1) p.alpha = 0.1;
      if (p.alpha > 0.7) p.alpha = 0.7;
      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height;
      if (p.y > height) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(125, 211, 252, ${p.alpha})`;
      ctx.shadowBlur = 6;
      ctx.shadowColor = 'rgba(56, 189, 248, 0.7)';
      ctx.fill();
    });
    requestAnimationFrame(render);
  }

  render();
}
