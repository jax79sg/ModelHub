// Progressive enhancement only: every page works without this file.
(function () {
  "use strict";

  // Theme toggle: explicit choice wins, otherwise the system setting applies.
  var toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
    });
  }

  // Forms that apply as soon as a control changes.
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    form.addEventListener("change", function () { form.submit(); });
  });
  document.querySelectorAll("form[data-autosubmit-debounce]").forEach(function (form) {
    var timer = null;
    var input = form.querySelector("input[name=search]");
    if (!input) return;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { form.submit(); }, 350);
    });
    // Keep the caret at the end after the page reloads with the filter applied.
    if (input.value && document.activeElement === document.body && location.search.indexOf("search=") !== -1) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  });

  // Two-thumb parameter slider: keep min <= max and paint the selected span.
  document.querySelectorAll("[data-range]").forEach(function (box) {
    var labels = (box.getAttribute("data-labels") || "").split("|");
    var lo = box.querySelector("input[name=pmin]");
    var hi = box.querySelector("input[name=pmax]");
    var fill = box.querySelector(".range-fill");
    var form = box.closest("form");
    var minLabel = form.querySelector("[data-range-min]");
    var maxLabel = form.querySelector("[data-range-max]");
    function paint(changed) {
      if (+lo.value > +hi.value) { (changed === lo ? hi : lo).value = changed.value; }
      var top = +lo.max;
      fill.style.left = (+lo.value / top * 100) + "%";
      fill.style.right = (100 - +hi.value / top * 100) + "%";
      if (minLabel) minLabel.textContent = labels[+lo.value];
      if (maxLabel) maxLabel.textContent = labels[+hi.value];
    }
    lo.addEventListener("input", function () { paint(lo); });
    hi.addEventListener("input", function () { paint(hi); });
    paint(lo);
  });

  // Copy buttons.
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      var done = function () {
        btn.classList.add("copied");
        setTimeout(function () { btn.classList.remove("copied"); }, 1200);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var ta = document.createElement("textarea");
        ta.value = text; ta.setAttribute("readonly", "");
        ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ }
        document.body.removeChild(ta);
      }
    });
  });

  // Close menus when clicking elsewhere.
  document.addEventListener("click", function (ev) {
    document.querySelectorAll("details.menu[open]").forEach(function (d) {
      if (!d.contains(ev.target)) d.removeAttribute("open");
    });
  });
})();
