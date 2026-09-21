/**
 * EL GoLearn - Interactive Canvas & Auth Script
 * ---------------------------------------------
 * يحتوي على:
 * 1. انيميشن المنحنيات التفاعلية الانسيابية (Moving Wave Curves) والشبكة الجيومترية.
 * 2. التبديل الديناميكي بين وضع التسجيل والدخول.
 * 3. وظائف إظهار وإخفاء كلمات السر.
 */

document.addEventListener('DOMContentLoaded', () => {
  initFluidMeshCanvas();
});

let currentAuthMode = 'signup';

/**
 * التبديل بين وضع إنشاء الحساب وتسجيل الدخول
 */
function toggleAuthMode(event) {
  if (event) event.preventDefault();

  const authTitle = document.getElementById('auth-title');
  const confirmGroup = document.getElementById('confirm-password-group');
  const submitBtnSpan = document.querySelector('#submit-btn span');
  const switchPrompt = document.getElementById('switch-prompt');
  const switchLink = document.getElementById('switch-link');
  const confirmInput = document.getElementById('confirm-password');

  if (currentAuthMode === 'signup') {
    currentAuthMode = 'login';
    authTitle.textContent = 'Welcome Back to EL GoLearn';
    submitBtnSpan.textContent = 'تسجيل الدخول';
    switchPrompt.textContent = 'ليس لديك حساب؟';
    switchLink.textContent = 'إنشاء حساب جديد';

    confirmGroup.style.display = 'none';
    confirmInput.removeAttribute('required');
  } else {
    currentAuthMode = 'signup';
    authTitle.textContent = 'Welcome in EL GoLearn';
    submitBtnSpan.textContent = 'إنشاء حساب';
    switchPrompt.textContent = 'لديك حساب بالفعل؟';
    switchLink.textContent = 'تسجيل الدخول';

    confirmGroup.style.display = 'flex';
    confirmInput.setAttribute('required', 'true');
  }
}

/**
 * إظهار / إخفاء كلمات السر
 */
function togglePasswordVisibility(inputId, buttonElement) {
  const input = document.getElementById(inputId);
  if (!input) return;

  if (input.type === 'password') {
    input.type = 'text';
    buttonElement.textContent = '🔒';
  } else {
    input.type = 'password';
    buttonElement.textContent = '👁️';
  }
}

/**
 * معالجة النموذج
 */
function handleFormSubmit(event) {
  event.preventDefault();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;

  if (currentAuthMode === 'signup' && password !== confirmPassword) {
    alert('⚠️ كلمة السر غير متطابقة!');
    return;
  }

  alert(currentAuthMode === 'signup' ? '✅ تم إنشاء الحساب بنجاح!' : '✅ تم تسجيل الدخول بنجاح!');
}

function handleGoogleLogin() {
  alert('🔗 جاري التوجيه لتسجيل الدخول عبر Google...');
}

/**
 * الكانفاس المتطور: رسم المنحنيات المائية المضيئة (Moving Wave Curves) + العقد
 */
function initFluidMeshCanvas() {
  const canvas = document.getElementById('mesh-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = canvas.parentElement.clientWidth);
  let height = (canvas.height = canvas.parentElement.clientHeight);

  window.addEventListener('resize', () => {
    if (!canvas.parentElement) return;
    width = canvas.width = canvas.parentElement.clientWidth;
    height = canvas.height = canvas.parentElement.clientHeight;
  });

  let mouse = { x: width / 2, y: height / 2 };
  window.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  // 1. إعداد العقد (Nodes)
  const nodeCount = 40;
  const nodes = [];

  for (let i = 0; i < nodeCount; i++) {
    nodes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.7,
      vy: (Math.random() - 0.5) * 0.7,
      radius: Math.random() * 2.2 + 1.2,
      pulse: Math.random() * Math.PI
    });
  }

  // 2. إعداد طبقات المنحنيات المتحركة (Fluid Curves Layers)
  let timeStep = 0;

  function renderWaveCurve(offsetY, amplitude, frequency, speed, alpha, color) {
    ctx.beginPath();
    ctx.moveTo(0, height / 2 + offsetY);

    for (let x = 0; x <= width; x += 15) {
      const y = Math.sin(x * frequency + timeStep * speed) * amplitude + 
                Math.cos(x * 0.005 + timeStep * 0.5) * (amplitude * 0.5) + (height / 2 + offsetY);
      ctx.lineTo(x, y);
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.6;
    ctx.shadowBlur = 12;
    ctx.shadowColor = 'rgba(56, 189, 248, 0.6)';
    ctx.stroke();
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    timeStep += 0.02;

    // A) رسم المنحنيات المتموجة بالخلفية
    renderWaveCurve(-100, 45, 0.006, 0.8, 0.25, 'rgba(56, 189, 248, 0.25)');
    renderWaveCurve(0, 60, 0.004, 1.2, 0.35, 'rgba(125, 211, 252, 0.3)');
    renderWaveCurve(90, 50, 0.005, 0.6, 0.2, 'rgba(2, 132, 199, 0.25)');

    // B) رسم وتحديث العقد والخطوط الموصلة
    for (let i = 0; i < nodeCount; i++) {
      let n1 = nodes[i];
      n1.x += n1.vx;
      n1.y += n1.vy;

      if (n1.x < 0 || n1.x > width) n1.vx *= -1;
      if (n1.y < 0 || n1.y > height) n1.vy *= -1;

      let dxMouse = mouse.x - n1.x;
      let dyMouse = mouse.y - n1.y;
      let distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);

      if (distMouse < 110) {
        n1.x -= (dxMouse / distMouse) * 0.4;
        n1.y -= (dyMouse / distMouse) * 0.4;
      }

      // رسم الخطوط الموصلة
      for (let j = i + 1; j < nodeCount; j++) {
        let n2 = nodes[j];
        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 120) {
          let lineAlpha = (1 - dist / 120) * 0.3;
          ctx.beginPath();
          ctx.moveTo(n1.x, n1.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.strokeStyle = `rgba(125, 211, 252, ${lineAlpha})`;
          ctx.lineWidth = 0.9;
          ctx.stroke();
        }
      }

      // رسم العقدة المضيئة
      n1.pulse += 0.035;
      let nodeAlpha = 0.5 + Math.sin(n1.pulse) * 0.35;

      ctx.beginPath();
      ctx.arc(n1.x, n1.y, n1.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(56, 189, 248, ${nodeAlpha})`;
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(56, 189, 248, 0.7)';
      ctx.fill();
    }

    requestAnimationFrame(animate);
  }

  animate();
}
