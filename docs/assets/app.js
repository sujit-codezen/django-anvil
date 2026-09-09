(function () {
  "use strict";

  // ---------- Mobile sidebar toggle ----------
  const menuToggle = document.querySelector(".menu-toggle");
  const sidebar = document.querySelector(".sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ---------- TOC scroll-spy ----------
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  if (tocLinks.length) {
    const headings = tocLinks
      .map((a) => document.getElementById(a.getAttribute("href").slice(1)))
      .filter(Boolean);

    const setActive = () => {
      let current = headings[0];
      for (const h of headings) {
        if (h.getBoundingClientRect().top - 96 <= 0) current = h;
      }
      tocLinks.forEach((a) => {
        a.classList.toggle("active", current && a.getAttribute("href") === "#" + current.id);
      });
    };
    document.addEventListener("scroll", setActive, { passive: true });
    setActive();
  }

  // ---------- Search modal ----------
  const backdrop = document.querySelector(".search-backdrop");
  const trigger = document.querySelector(".search-trigger");
  const input = document.querySelector(".search-modal input");
  const resultsEl = document.querySelector(".search-results");
  if (!backdrop || !trigger || !input || !resultsEl || typeof SEARCH_INDEX === "undefined") return;

  let selectedIndex = 0;
  let currentResults = [];

  function render(items) {
    currentResults = items;
    selectedIndex = 0;
    if (!items.length) {
      resultsEl.innerHTML = '<div class="search-empty">No results.</div>';
      return;
    }
    resultsEl.innerHTML = items
      .slice(0, 20)
      .map(
        (item, i) =>
          `<a href="${item.page}" data-i="${i}" class="${i === 0 ? "selected" : ""}">` +
          `<div>${item.title}</div><div class="sr-page">${item.section}${item.desc ? " · " + item.desc : ""}</div>` +
          `</a>`
      )
      .join("");
  }

  function search(query) {
    const q = query.trim().toLowerCase();
    if (!q) return render(SEARCH_INDEX.slice(0, 10));
    render(
      SEARCH_INDEX.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.section.toLowerCase().includes(q) ||
          (item.desc && item.desc.toLowerCase().includes(q))
      )
    );
  }

  function open() {
    backdrop.classList.add("open");
    input.value = "";
    search("");
    setTimeout(() => input.focus(), 0);
  }
  function close() {
    backdrop.classList.remove("open");
  }

  trigger.addEventListener("click", open);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });
  input.addEventListener("input", () => search(input.value));

  document.addEventListener("keydown", (e) => {
    const isCmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
    if (isCmdK) {
      e.preventDefault();
      backdrop.classList.contains("open") ? close() : open();
      return;
    }
    if (!backdrop.classList.contains("open")) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const links = Array.from(resultsEl.querySelectorAll("a"));
      if (!links.length) return;
      links[selectedIndex]?.classList.remove("selected");
      selectedIndex =
        e.key === "ArrowDown"
          ? Math.min(selectedIndex + 1, links.length - 1)
          : Math.max(selectedIndex - 1, 0);
      links[selectedIndex].classList.add("selected");
      links[selectedIndex].scrollIntoView({ block: "nearest" });
    }
    if (e.key === "Enter") {
      const links = Array.from(resultsEl.querySelectorAll("a"));
      if (links[selectedIndex]) window.location.href = links[selectedIndex].getAttribute("href");
    }
  });
})();
