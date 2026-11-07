// Book Selector: a button that shows and hides the list of books right after it.
// Without JavaScript the list just stays visible.
(function () {
  var wraps = document.querySelectorAll(".selector");
  Array.prototype.forEach.call(wraps, function (wrap) {
    var button = wrap.querySelector(".selector-button");
    var list = wrap.querySelector(".selector-list");
    if (!button || !list) return;
    document.documentElement.classList.add("js");
    function setOpen(open) {
      button.setAttribute("aria-expanded", open ? "true" : "false");
      list.hidden = !open;
    }
    setOpen(false);
    button.addEventListener("click", function () {
      setOpen(button.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Escape" || e.key === "Esc") && button.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        button.focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (button.getAttribute("aria-expanded") === "true" && !wrap.contains(e.target)) setOpen(false);
    });
  });
})();
