(() => {
  const crawlForm = document.getElementById("crawl-form");
  const targetUrlInput = document.getElementById("target-url-input");
  const navCategoryInput = document.getElementById("nav-category-input");
  const discoverNavBtn = document.getElementById("discover-nav-btn");
  const crawlSubmitBtn = document.getElementById("crawl-submit-btn");
  const statusPill = document.getElementById("status-pill");
  const navDrawer = document.getElementById("nav-categories-drawer");
  const navDrawerTitle = document.getElementById("nav-drawer-title");
  const navCategoriesList = document.getElementById("nav-categories-list");
  const errorBanner = document.getElementById("error-banner");
  const crawlMeta = document.getElementById("crawl-meta");
  const searchQueryInput = document.getElementById("search-query-input");
  const searchCountBadge = document.getElementById("search-count-badge");
  const viewListBtn = document.getElementById("view-list-btn");
  const viewJsonBtn = document.getElementById("view-json-btn");
  const copyJsonBtn = document.getElementById("copy-json-btn");
  const exportCsvBtn = document.getElementById("export-csv-btn");
  const listingsView = document.getElementById("listings-view");
  const emptyState = document.getElementById("empty-state");
  const listingsGrid = document.getElementById("listings-grid");
  const jsonView = document.getElementById("json-view");
  const jsonOutputCode = document.getElementById("json-output-code");

  let allExtractedItems = [];
  let filteredItems = [];

  function setStatus(text, state = "idle") {
    statusPill.textContent = text;
    statusPill.className = `status-pill status-${state}`;
  }

  function showError(msg) {
    if (!msg) {
      errorBanner.classList.add("hidden");
      errorBanner.textContent = "";
      return;
    }
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function highlightMatch(text, query) {
    const safe = escapeHtml(text);
    const trimmed = (query || "").trim();
    if (!trimmed) return safe;
    const escapedQuery = trimmed.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escapedQuery})`, "gi");
    return safe.replace(regex, '<mark class="search-highlight">$1</mark>');
  }

  function renderCategoriesDrawer(categories, activeCategory = "") {
    navCategoriesList.innerHTML = "";
    if (!Array.isArray(categories) || categories.length === 0) {
      navDrawer.classList.add("hidden");
      return;
    }
    navDrawerTitle.textContent = `Discovered Navigation Categories (${categories.length})`;
    categories.forEach((cat) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "nav-pill";
      if (activeCategory && cat.label.toLowerCase() === activeCategory.toLowerCase()) {
        btn.classList.add("active");
      }
      btn.textContent = cat.label;
      btn.title = cat.url;
      btn.addEventListener("click", () => {
        navCategoryInput.value = cat.label;
        runCrawl();
      });
      navCategoriesList.appendChild(btn);
    });
    navDrawer.classList.remove("hidden");
  }

  function filterItemsClientSide(items, query) {
    const cleaned = (query || "").trim().toLowerCase();
    if (!cleaned) return [...items];
    const tokens = cleaned.split(/\s+/).filter(Boolean);
    return items.filter((item) => {
      const title = (item.title || "").toLowerCase();
      const url = (item.url || "").toLowerCase();
      const combined = `${title} ${url}`;
      if (title.includes(cleaned) || url.includes(cleaned)) return true;
      return tokens.length > 1 && tokens.every((t) => combined.includes(t));
    });
  }

  function renderResults() {
    const query = searchQueryInput.value;
    filteredItems = filterItemsClientSide(allExtractedItems, query);
    searchCountBadge.textContent = `${filteredItems.length} / ${allExtractedItems.length}`;

    const hasItems = filteredItems.length > 0;
    copyJsonBtn.disabled = allExtractedItems.length === 0;
    exportCsvBtn.disabled = allExtractedItems.length === 0;

    // Render OpenSpec JSON view
    const specPayload = {
      items: filteredItems.map((i) => ({ title: i.title, url: i.url })),
    };
    jsonOutputCode.textContent = JSON.stringify(specPayload, null, 2);

    // Render Listings Grid
    listingsGrid.innerHTML = "";
    if (!hasItems) {
      listingsGrid.classList.add("hidden");
      emptyState.classList.remove("hidden");
      emptyState.innerHTML =
        allExtractedItems.length > 0
          ? `<p>No listings match filter <strong>"${escapeHtml(query)}"</strong> (${allExtractedItems.length} total extracted).</p>`
          : `<p>No listings loaded yet. Enter a URL and navigation category above and click <strong>Crawl &amp; Extract Listings</strong>.</p>`;
      return;
    }

    emptyState.classList.add("hidden");
    listingsGrid.classList.remove("hidden");

    filteredItems.forEach((item, idx) => {
      const li = document.createElement("li");
      li.className = "listing-card";
      li.innerHTML = `
        <span class="listing-index">#${idx + 1}</span>
        <a class="listing-title" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
          ${highlightMatch(item.title, query)}
        </a>
        <a class="listing-url" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
          ${highlightMatch(item.url, query)}
        </a>
      `;
      listingsGrid.appendChild(li);
    });
  }

  function sanitizeTargetUrl(rawInput) {
    let cleaned = (rawInput || "").trim();
    if (!cleaned) return "";

    // Strip markdown link syntax [label](https://...) if pasted
    const mdMatch = cleaned.match(/^\[[^\]]*\]\((https?:\/\/[^)\s]+)\)$/i);
    if (mdMatch) {
      cleaned = mdMatch[1].trim();
    }

    // If multiple http(s):// schemes exist before any query string '?',
    // extract the trailing explicit absolute URL (e.g. when pasted after a previous URL)
    const preQuery = cleaned.split("?")[0];
    const schemeMatches = [...preQuery.matchAll(/https?:\/\//gi)];
    if (schemeMatches.length > 1) {
      const lastIndex = schemeMatches[schemeMatches.length - 1].index;
      cleaned = cleaned.slice(lastIndex).trim();
    }

    // Do not prepend any default host if it already starts with http:// or https://
    if (!/^https?:\/\//i.test(cleaned)) {
      cleaned = `https://${cleaned.replace(/^\/+/, "")}`;
    }

    return cleaned;
  }

  async function discoverCategories() {
    const targetUrl = sanitizeTargetUrl(targetUrlInput.value);
    if (!targetUrl) {
      showError("Please enter a Target Root URL first.");
      return;
    }
    targetUrlInput.value = targetUrl;
    showError("");
    setStatus("Discovering Nav...", "loading");
    discoverNavBtn.disabled = true;

    try {
      const res = await fetch("/api/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_url: targetUrl }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus("Discovery Failed", "error");
        showError(data.error || "Failed to discover navigation categories.");
        return;
      }
      renderCategoriesDrawer(data.categories || [], navCategoryInput.value.trim());
      setStatus(`Found ${(data.categories || []).length} Nav Links`, "success");
    } catch (err) {
      setStatus("Network Error", "error");
      showError(err.message || "Request failed.");
    } finally {
      discoverNavBtn.disabled = false;
    }
  }

  async function runCrawl(e) {
    if (e) e.preventDefault();
    const targetUrl = sanitizeTargetUrl(targetUrlInput.value);
    const navCategory = navCategoryInput.value.trim() || "all";
    if (!targetUrl) {
      showError("target_url is required.");
      return;
    }
    targetUrlInput.value = targetUrl;
    navCategoryInput.value = navCategory;

    showError("");
    setStatus("Crawling...", "loading");
    crawlSubmitBtn.disabled = true;

    try {
      const res = await fetch("/api/crawl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_url: targetUrl,
          nav_category: navCategory,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        setStatus("Category Not Found / Error", "error");
        showError(data.error || "Crawl failed.");
        if (Array.isArray(data.available_categories)) {
          renderCategoriesDrawer(data.available_categories, "");
        }
        return;
      }

      allExtractedItems = Array.isArray(data.items) ? data.items : [];
      renderCategoriesDrawer(data.available_categories || [], data.matched_category);
      crawlMeta.innerHTML = `Matched Category: <strong>${escapeHtml(data.matched_category)}</strong> (<a href="${escapeHtml(data.category_url)}" target="_blank" rel="noopener" style="color: var(--accent-cyan)">${escapeHtml(data.category_url)}</a>) — Extracted <strong>${allExtractedItems.length}</strong> records`;
      setStatus(`Extracted ${allExtractedItems.length} Items`, "success");
      renderResults();
    } catch (err) {
      setStatus("Error", "error");
      showError(err.message || "Unexpected error while crawling.");
    } finally {
      crawlSubmitBtn.disabled = false;
    }
  }

  crawlForm.addEventListener("submit", runCrawl);
  discoverNavBtn.addEventListener("click", discoverCategories);
  searchQueryInput.addEventListener("input", renderResults);

  viewListBtn.addEventListener("click", () => {
    viewListBtn.classList.add("active");
    viewJsonBtn.classList.remove("active");
    listingsView.classList.remove("hidden");
    jsonView.classList.add("hidden");
  });

  viewJsonBtn.addEventListener("click", () => {
    viewJsonBtn.classList.add("active");
    viewListBtn.classList.remove("active");
    jsonView.classList.remove("hidden");
    listingsView.classList.add("hidden");
  });

  copyJsonBtn.addEventListener("click", async () => {
    const payload = JSON.stringify({ items: filteredItems }, null, 2);
    await navigator.clipboard.writeText(payload);
    const original = copyJsonBtn.textContent;
    copyJsonBtn.textContent = "Copied!";
    setTimeout(() => {
      copyJsonBtn.textContent = original;
    }, 1500);
  });

  exportCsvBtn.addEventListener("click", () => {
    const rows = [["title", "url"], ...filteredItems.map((i) => [i.title, i.url])];
    const csvContent = rows
      .map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "extracted_listings.csv";
    a.click();
    URL.revokeObjectURL(url);
  });

  document.querySelectorAll(".chip-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      targetUrlInput.value = btn.dataset.url || "";
      navCategoryInput.value = btn.dataset.category || "all";
      searchQueryInput.value = "";
      runCrawl();
    });
  });
})();
