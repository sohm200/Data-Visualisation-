/*
 * Upload, loading indicator, sheet switching and chart drawing.
 *
 * The page is replaced in place with the server's HTML response, so the chosen File stays in
 * memory here. Switching sheets re-submits that same file with the sheet name; the server keeps
 * nothing between requests (docs/decisions.md, FR-34).
 */
(function () {
  "use strict";

  const body = document.body;
  const settings = {
    processUrl: body.dataset.processUrl,
    maxBytes: Number(body.dataset.maxBytes),
    noFile: body.dataset.msgNoFile,
    tooLarge: body.dataset.msgTooLarge,
    unexpected: body.dataset.msgUnexpected,
  };
  let currentFile = null;

  function init() {
    const form = document.getElementById("upload-form");
    if (form) initUpload(form);

    const sheetSelect = document.getElementById("sheet-select");
    if (sheetSelect) {
      sheetSelect.addEventListener("change", function () {
        if (!currentFile) {
          showError("Please choose the file again to switch sheets.");
          return;
        }
        submit(currentFile, sheetSelect.value, false);
      });
    }
    drawCharts();
  }

  function initUpload(form) {
    const input = document.getElementById("file");
    const button = document.getElementById("process");
    const sync = function () { button.disabled = input.files.length === 0; };   // SRS 3.1
    input.addEventListener("change", function () { hideError(); sync(); });
    sync();

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const file = input.files[0];
      if (!file) { showError(settings.noFile); return; }                        // E-07
      if (file.size > settings.maxBytes) { showError(settings.tooLarge); return; } // E-02 (server checks too)
      currentFile = file;
      submit(file, null, true);
    });
  }

  function submit(file, sheet, fromUploadPage) {
    showLoading(true);                                                          // NFR-04
    const data = new FormData();
    data.append("file", file, file.name);
    if (sheet) data.append("sheet", sheet);

    fetch(settings.processUrl, { method: "POST", body: data })
      .then(function (response) { return response.text(); })
      .then(function (html) {
        const isDashboard = swapPage(html);
        if (isDashboard && fromUploadPage) history.pushState({ dashboard: true }, "");
      })
      .catch(function () { showError(settings.unexpected); })
      .finally(function () { showLoading(false); });
  }

  /* Replace the page content with the server's response. Returns true when it is a dashboard. */
  function swapPage(html) {
    const next = new DOMParser().parseFromString(html, "text/html");
    const content = next.getElementById("app");
    if (!content) throw new Error("Unexpected response");
    purgeCharts();
    document.getElementById("app").innerHTML = content.innerHTML;
    document.title = next.title;
    window.scrollTo(0, 0);
    init();
    return Boolean(document.querySelector(".dashboard"));
  }

  function drawCharts() {
    if (!window.Plotly) return;
    document.querySelectorAll(".chart[id]").forEach(function (element) {
      const source = document.getElementById(element.id + "-data");
      if (!source) return;
      try {
        const figure = JSON.parse(source.textContent);
        window.Plotly.newPlot(element, figure.data, figure.layout, {
          responsive: true,
          displaylogo: false,
          displayModeBar: true,
          modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"],
          toImageButtonOptions: { format: "png", filename: element.dataset.downloadName, scale: 2 },  // FR-24
        });
      } catch (error) {
        element.textContent = "This chart could not be shown.";                // FR-53
        console.error(error);
      }
    });
  }

  function purgeCharts() {
    if (!window.Plotly) return;
    document.querySelectorAll(".chart[id]").forEach(function (element) { window.Plotly.purge(element); });
  }

  function showLoading(on) {
    document.getElementById("loading").hidden = !on;
    document.querySelectorAll("button, select").forEach(function (control) {
      if (on) {
        control.setAttribute("data-was-disabled", control.disabled);
        control.disabled = true;
      } else if (control.hasAttribute("data-was-disabled")) {   // controls swapped in meanwhile keep their own state
        control.disabled = control.getAttribute("data-was-disabled") === "true";
        control.removeAttribute("data-was-disabled");
      }
    });
  }

  function showError(message) {
    const box = document.getElementById("error");
    if (!box) return;
    box.textContent = message;
    box.hidden = false;
  }

  function hideError() {
    const box = document.getElementById("error");
    if (box) box.hidden = true;
  }

  // Browser Back from a dashboard returns to the upload screen.
  window.addEventListener("popstate", function () { window.location.reload(); });

  init();
})();
