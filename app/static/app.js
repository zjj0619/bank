(function () {
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.submitted === "1") {
        event.preventDefault();
        return;
      }
      form.dataset.submitted = "1";
      var button = form.querySelector("[type=submit]");
      if (!button) {
        return;
      }
      window.setTimeout(function () {
        button.disabled = true;
      }, 0);
    });
  });
})();
