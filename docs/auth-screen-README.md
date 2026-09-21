# 🔐 دليل واجهة تسجيل الدخول والإنشاء EL GoLearn (Image 2 UI - Swapped Layout)

تم تحديث وتنسيق هذه الواجهة وفقاً لأفضل ممارسات تجربة المستخدم (UX Best Practices) للواجهات العربية الموجهة من اليمين إلى اليسار (RTL):

---

## 🎨 الترتيب والمكونات البصرية الجديدة (Updated Layout)

1. **الجانب الأيمن (Visual Side - Right)**:
   - **المنحنيات المائية المتحركة (Moving Wave Curves)**: خطوط انسيابية مضيئة باللون السماوي والنيوني تسبح بسلاسة في الخلفية.
   - **عقد الشبكة الجيومترية (Constellation Mesh)**: نقاط وروابط تفاعلية تتأثر وتتحرك مع حركة مؤشر الماوس.
   - **شعار GoLearn البارز والتنفيذي (Centerpiece Logo)**: تم نقل الشعار الأيقوني (الدماغ وسهم التفوق) إلى منتصف الجانب البصري ليعطي توازناً وتباينًا متناسقاً وراقياً.

2. **الجانب الأيسر (Auth Side - Left)**:
   - **كارت نموذج الإدخال (Clean Auth Card)**: كارت زجاجي نظيف ومتكامل، يتيح إدخال `اميل المستخدم`، `كلمه السر`، `كلمه السر مجددا` مع خيار التسجيل عبر **Google** والتبديل المباشر بين التسجيل والدخول.

---

## 📁 هيكل الملفات (File Structure)

```
d:\New_Front\image2\
├── index.html       # الهيكل المعدل بالترتيب البصري الجديد
├── style.css        # التنسيقات البصرية والنيونية والتجاوب
├── script.js        # كانفاس المنحنيات المائية والعقد وسكريبت التبديل
└── README.md        # دليل الاستخدام والدمج مع Django
```

---

## 🛠️ دليل الدمج مع مشروع Django (Django Integration Guide)

### 1️⃣ نقل الملفات الثابتة
- انقل `style.css` ⬅️ إلى `static/css/golearn-auth.css`
- انقل `script.js` ⬅️ إلى `static/js/golearn-auth.js`

### 2️⃣ القالب بالجانجو (`templates/registration/signup.html`)

```html
{% load static %}
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <title>EL GoLearn - الحساب والتحقق</title>
  <link rel="stylesheet" href="{% static 'css/golearn-auth.css' %}" />
</head>
<body>

  <div class="auth-container">
    
    <!-- الجانب الأيمن: البصريات والشعار -->
    <div class="visual-side">
      <div class="mesh-glow-bg"></div>
      <canvas id="mesh-canvas"></canvas>
      <div class="hero-brand-centerpiece">
        <!-- SVG Logo -->
        <h2 class="hero-brand-name">EL GoLearn</h2>
      </div>
    </div>

    <!-- الجانب الأيسر: النموذج -->
    <div class="auth-side">
      <div class="circuit-bg-glow"></div>
      <div class="auth-card">
        <h1 class="auth-title" id="auth-title">Welcome in EL GoLearn</h1>

        <form method="POST" action="{% url 'signup' %}" id="auth-form">
          {% csrf_token %}

          <div class="form-group">
            <label for="email" class="form-label">ادخال اميل المستخدم</label>
            <div class="input-wrapper">
              <input type="email" name="email" id="email" required placeholder="ادخل بريدك الإلكتروني" />
            </div>
          </div>

          <div class="form-group">
            <label for="password" class="form-label">كلمه السر</label>
            <div class="input-wrapper">
              <input type="password" name="password" id="password" required placeholder="كلمه السر" />
              <button type="button" class="toggle-password" onclick="togglePasswordVisibility('password', this)">👁️</button>
            </div>
          </div>

          <div class="form-group" id="confirm-password-group">
            <label for="confirm-password" class="form-label">كلمه السر مجددا</label>
            <div class="input-wrapper">
              <input type="password" name="confirm_password" id="confirm-password" placeholder="كلمه السر" />
              <button type="button" class="toggle-password" onclick="togglePasswordVisibility('confirm-password', this)">👁️</button>
            </div>
          </div>

          <div class="divider"><span>أو قم بالتسجيل عبر:</span></div>

          <div class="social-login">
            <button type="button" class="google-btn">
              <svg class="google-icon" viewBox="0 0 24 24">...</svg>
            </button>
          </div>

          <button type="submit" class="submit-btn" id="submit-btn">
            <span>إنشاء حساب</span>
          </button>
        </form>

        <div class="auth-switch">
          <span id="switch-prompt">لديك حساب بالفعل؟</span>
          <a href="#" id="switch-link" onclick="toggleAuthMode(event)">تسجيل الدخول</a>
        </div>
      </div>
    </div>

  </div>

  <script src="{% static 'js/golearn-auth.js' %}"></script>
</body>
</html>
```
