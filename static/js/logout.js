(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    initRipple();
    initLogoutState();
  });

  function initRipple() {
    document.querySelectorAll(".btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        var rect = btn.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        var ripple = document.createElement("span");
        ripple.className = "ripple";
        ripple.style.width = ripple.style.height = size + "px";
        ripple.style.left = e.clientX - rect.left - size / 2 + "px";
        ripple.style.top = e.clientY - rect.top - size / 2 + "px";
        btn.appendChild(ripple);
        setTimeout(function () { ripple.remove(); }, 600);
      });
    });
  }

  function initLogoutState() {
    var form = document.querySelector(".auth-form");
    if (!form) return;
    var btn = form.querySelector(".btn-danger");

    form.addEventListener("submit", function () {
      if (btn) {
        btn.classList.add("loading");
        btn.disabled = true;
      }
    });
  }
})();
