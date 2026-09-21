/**
 * EL GoLearn - Animated Background Engine
 */
class GoLearnBackgroundEngine {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.spotlight = null;
    this.particles = [];
    this.particleCount = 55;
    this.mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    this.targetMouse = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    this.init();
  }

  init() {
    document.addEventListener('DOMContentLoaded', () => {
      this.canvas = document.getElementById('golearn-bg-canvas');
      this.spotlight = document.querySelector('.golearn-bg-spotlight');

      if (!this.canvas) return;

      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
      this.createParticles();
      this.bindEvents();
      this.animate();
    });
  }

  resizeCanvas() {
    if (!this.canvas) return;
    this.width = this.canvas.width = window.innerWidth;
    this.height = this.canvas.height = window.innerHeight;
  }

  createParticles() {
    this.particles = [];
    for (let i = 0; i < this.particleCount; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        radius: Math.random() * 1.8 + 0.5,
        alpha: Math.random() * 0.7 + 0.2,
        speedX: (Math.random() - 0.5) * 0.25,
        speedY: (Math.random() - 0.5) * 0.25 - 0.1,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.015 + Math.random() * 0.02,
        color: Math.random() > 0.4 ? 'rgba(56, 189, 248, ' : 'rgba(125, 211, 252, '
      });
    }
  }

  bindEvents() {
    window.addEventListener('resize', () => {
      this.resizeCanvas();
      this.createParticles();
    });

    window.addEventListener('mousemove', (e) => {
      this.targetMouse.x = e.clientX;
      this.targetMouse.y = e.clientY;
    });

    window.addEventListener('touchmove', (e) => {
      if (e.touches.length > 0) {
        this.targetMouse.x = e.touches[0].clientX;
        this.targetMouse.y = e.touches[0].clientY;
      }
    });
  }

  animate() {
    this.mouse.x += (this.targetMouse.x - this.mouse.x) * 0.08;
    this.mouse.y += (this.targetMouse.y - this.mouse.y) * 0.08;

    if (this.spotlight) {
      this.spotlight.style.transform = `translate3d(${this.mouse.x}px, ${this.mouse.y}px, 0)`;
    }

    if (this.ctx) {
      this.ctx.clearRect(0, 0, this.width, this.height);

      for (let i = 0; i < this.particles.length; i++) {
        const p = this.particles[i];
        p.x += p.speedX;
        p.y += p.speedY;
        p.pulse += p.pulseSpeed;

        if (p.x < 0) p.x = this.width;
        if (p.x > this.width) p.x = 0;
        if (p.y < 0) p.y = this.height;
        if (p.y > this.height) p.y = 0;

        const currentAlpha = Math.max(0.1, p.alpha + Math.sin(p.pulse) * 0.25);
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        this.ctx.fillStyle = `${p.color}${currentAlpha})`;
        this.ctx.shadowBlur = 10;
        this.ctx.shadowColor = 'rgba(56, 189, 248, 0.8)';
        this.ctx.fill();
      }
    }

    requestAnimationFrame(() => this.animate());
  }
}

window.GoLearnBackground = new GoLearnBackgroundEngine();
