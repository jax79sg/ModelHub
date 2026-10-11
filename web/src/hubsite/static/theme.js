// Runs in <head> before first paint so the page never flashes the wrong theme.
(function () {
  var theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* storage blocked: follow the system */ }
  if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
})();
