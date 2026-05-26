const state = {
  project: null,
  runs: [],
  tools: {},
  busy: new Set(),
  openRunId: null,
  pollTimer: null,
  source: null,
  structure: null,
  bibtexRefsReport: null,
  floatInventory: null,
  /** Persisted until page reload; only applied when viewing LaTeX source. */
  sourceLatexWordWrap: false,
};

const proofState = {
  tab: "main",
  treeItems: [],
  session: null,
  fileModalRelativePath: null,
  /** Which assist tab opened the shared file modal; drives Analyze API choice. */
  modalWorkflow: null,
};

const paragraphStyleState = {
  treeItems: [],
  session: null,
};

const synopsisState = {
  tree: [],
  nodeById: new Map(),
  sortableInstances: [],
  busy: false,
  exportMdBusy: false,
};

/** Session-only: node id → branch children visible (true = expanded). Survives local re-renders; reconciled when tree ids change. */
const synopsisFoldSession = {
  branchExpanded: new Map(),
};

let synopsisSaveUiTimer = null;

/** Omit live output blobs from digests; patch those in-place so selection survives polling. */
let cachedRunsPanelLayoutKey = null;
let cachedToolsPanelLayoutKey = null;

const els = {
  error: document.getElementById("errorBox"),
  projectRoot: document.getElementById("projectRoot"),
  buildPath: document.getElementById("buildPath"),
  toolsPanel: document.getElementById("toolsPanel"),
  runsPanel: document.getElementById("runsPanel"),
  pdfLink: document.getElementById("pdfLink"),
  pdfState: document.getElementById("pdfState"),
  latexSourceBtn: document.getElementById("latexSourceBtn"),
  bibtexSourceBtn: document.getElementById("bibtexSourceBtn"),
  structureBtn: document.getElementById("structureBtn"),
  bibtexErrorsBtn: document.getElementById("bibtexErrorsBtn"),
  pdfCompressionLevel: document.getElementById("pdfCompressionLevel"),
  compressPdfBtn: document.getElementById("compressPdfBtn"),
  compressPdfState: document.getElementById("compressPdfState"),
  sourceModal: document.getElementById("sourceModal"),
  sourceDialogBox: document.getElementById("sourceDialogBox"),
  sourceTitle: document.getElementById("sourceTitle"),
  sourcePath: document.getElementById("sourcePath"),
  sourceCloseBtn: document.getElementById("sourceCloseBtn"),
  sourceSearch: document.getElementById("sourceSearch"),
  sourceSearchState: document.getElementById("sourceSearchState"),
  sourceJumpLine: document.getElementById("sourceJumpLine"),
  sourceJumpBtn: document.getElementById("sourceJumpBtn"),
  sourceWordWrapBtn: document.getElementById("sourceWordWrapBtn"),
  sourceViewerScroll: document.getElementById("sourceViewerScroll"),
  sourceViewer: document.getElementById("sourceViewer"),
  sourceModalBusy: document.getElementById("sourceModalBusy"),
  sourceModalBusyHint: document.getElementById("sourceModalBusyHint"),
  sourceSplit: document.getElementById("sourceSplit"),
  bibtexRefsCol: document.getElementById("bibtexRefsCol"),
  refsSearch: document.getElementById("refsSearch"),
  refsSearchState: document.getElementById("refsSearchState"),
  bibtexRefsViewer: document.getElementById("bibtexRefsViewer"),
  structureModal: document.getElementById("structureModal"),
  structureTitle: document.getElementById("structureTitle"),
  structurePath: document.getElementById("structurePath"),
  structureCloseBtn: document.getElementById("structureCloseBtn"),
  structureSearch: document.getElementById("structureSearch"),
  structureSearchState: document.getElementById("structureSearchState"),
  structureViewer: document.getElementById("structureViewer"),
  floatInventoryModal: document.getElementById("floatInventoryModal"),
  floatInventoryTitle: document.getElementById("floatInventoryTitle"),
  floatInventoryRoot: document.getElementById("floatInventoryRoot"),
  floatInventoryCloseBtn: document.getElementById("floatInventoryCloseBtn"),
  floatInventorySearch: document.getElementById("floatInventorySearch"),
  floatInventorySearchState: document.getElementById("floatInventorySearchState"),
  floatInventoryViewer: document.getElementById("floatInventoryViewer"),
  listFiguresBtn: document.getElementById("listFiguresBtn"),
  listTablesBtn: document.getElementById("listTablesBtn"),
  clearBtn: document.getElementById("clearBtn"),
  reloadBtn: document.getElementById("reloadBtn"),
  tabMainBtn: document.getElementById("tabMainBtn"),
  tabProofBtn: document.getElementById("tabProofBtn"),
  tabParagraphStyleBtn: document.getElementById("tabParagraphStyleBtn"),
  tabSynopsisBtn: document.getElementById("tabSynopsisBtn"),
  tabPanelMain: document.getElementById("tabPanelMain"),
  tabPanelProof: document.getElementById("tabPanelProof"),
  tabPanelParagraphStyle: document.getElementById("tabPanelParagraphStyle"),
  tabPanelSynopsis: document.getElementById("tabPanelSynopsis"),
  proofTree: document.getElementById("proofTree"),
  proofCardsWrap: document.getElementById("proofCardsWrap"),
  proofSessionPath: document.getElementById("proofSessionPath"),
  proofStatsSummary: document.getElementById("proofStatsSummary"),
  proofSuggestedBusy: document.getElementById("proofSuggestedBusy"),
  proofSuggestedBusyHint: document.getElementById("proofSuggestedBusyHint"),
  styleTree: document.getElementById("styleTree"),
  styleCardsWrap: document.getElementById("styleCardsWrap"),
  styleSessionPath: document.getElementById("styleSessionPath"),
  styleStatsSummary: document.getElementById("styleStatsSummary"),
  styleSuggestedBusy: document.getElementById("styleSuggestedBusy"),
  styleSuggestedBusyHint: document.getElementById("styleSuggestedBusyHint"),
  proofFileModal: document.getElementById("proofFileModal"),
  proofFileCloseBtn: document.getElementById("proofFileCloseBtn"),
  proofFileReloadBtn: document.getElementById("proofFileReloadBtn"),
  proofFileAnalyzeBtn: document.getElementById("proofFileAnalyzeBtn"),
  proofFileModel: document.getElementById("proofFileModel"),
  proofFilePath: document.getElementById("proofFilePath"),
  proofFileViewer: document.getElementById("proofFileViewer"),
  proofApiErrorModal: document.getElementById("proofApiErrorModal"),
  proofApiErrorCloseBtn: document.getElementById("proofApiErrorCloseBtn"),
  proofApiErrorTitle: document.getElementById("proofApiErrorTitle"),
  proofApiErrorSubtitle: document.getElementById("proofApiErrorSubtitle"),
  proofApiErrorBody: document.getElementById("proofApiErrorBody"),
  synopsisTree: document.getElementById("synopsisTree"),
  synopsisPathHint: document.getElementById("synopsisPathHint"),
  synopsisSaveState: document.getElementById("synopsisSaveState"),
  synopsisReloadBtn: document.getElementById("synopsisReloadBtn"),
  synopsisMarkdownBtn: document.getElementById("synopsisMarkdownBtn"),
  synopsisBusy: document.getElementById("synopsisBusy"),
  synopsisBusyHint: document.getElementById("synopsisBusyHint"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showError(message) {
  if (!message) {
    els.error.classList.add("hidden");
    els.error.textContent = "";
    return;
  }
  els.error.textContent = message;
  els.error.classList.remove("hidden");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const label =
      data.error || `${response.status} ${response.statusText || "Error"}`.trim();
    const err = new Error(label);
    err.status = response.status;
    if (data.detail) err.detail = data.detail;
    if (data.error_type) err.errorType = data.error_type;
    throw err;
  }
  return data;
}

function closeProofApiErrorModal() {
  if (!els.proofApiErrorModal) return;
  els.proofApiErrorModal.classList.add("hidden");
  els.proofApiErrorModal.setAttribute("aria-hidden", "true");
}

function showProofApiErrorModal(fromError, options = {}) {
  const title = options.title || "Proofreading analyze failed";
  if (!els.proofApiErrorModal || !els.proofApiErrorBody) {
    showError(fromError?.message || String(fromError));
    return;
  }
  const status = fromError?.status;
  const et = fromError?.errorType;
  if (els.proofApiErrorTitle) {
    els.proofApiErrorTitle.textContent = title;
  }
  if (els.proofApiErrorSubtitle) {
    const parts = [];
    if (status) parts.push(`HTTP ${status}`);
    if (et) parts.push(et);
    els.proofApiErrorSubtitle.textContent = parts.join(" · ");
  }
  els.proofApiErrorBody.textContent =
    fromError?.detail || fromError?.message || String(fromError || "Unknown error");
  els.proofApiErrorModal.classList.remove("hidden");
  els.proofApiErrorModal.setAttribute("aria-hidden", "false");
}

function proofModelSelectInnerHtml(selected) {
  return `<option value="gpt-5.4-mini" ${selected === "gpt-5.4-mini" ? "selected" : ""}>gpt-5.4-mini</option>
<option value="gpt-5.5" ${selected === "gpt-5.5" ? "selected" : ""}>gpt-5.5</option>`;
}

function proofUtf32Chars(str) {
  return [...String(str ?? "")];
}

/**
 * LCS-based alignment: returns ops with merged runs.
 * 'eq' text appears on both sides; 'del' only left; 'ins' only right.
 */
function proofLcDiffOps(a, b) {
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i -= 1) {
    for (let j = n - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? 1 + dp[i + 1][j + 1] : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  let i = 0;
  let j = 0;
  const raw = [];
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      raw.push({ t: "eq", ch: a[i] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      raw.push({ t: "del", ch: a[i] });
      i += 1;
    } else {
      raw.push({ t: "ins", ch: b[j] });
      j += 1;
    }
  }
  while (i < m) {
    raw.push({ t: "del", ch: a[i] });
    i += 1;
  }
  while (j < n) {
    raw.push({ t: "ins", ch: b[j] });
    j += 1;
  }
  const merged = [];
  for (const row of raw) {
    const last = merged[merged.length - 1];
    if (last && last.type === row.t) {
      last.text += row.ch;
    } else {
      merged.push({ type: row.t, text: row.ch });
    }
  }
  return merged;
}

function proofSnippetsWithCharDiffHtml(original, proposed) {
  const a = proofUtf32Chars(original);
  const b = proofUtf32Chars(proposed);
  if (a.length === 0 && b.length === 0) {
    return { leftInner: "", rightInner: "" };
  }
  const ops = proofLcDiffOps(a, b);
  let leftInner = "";
  let rightInner = "";
  for (const op of ops) {
    const esc = escapeHtml(op.text);
    if (op.type === "eq") {
      leftInner += esc;
      rightInner += esc;
    } else if (op.type === "del") {
      leftInner += `<span class="proof-char-diff-mismatch">${esc}</span>`;
    } else {
      rightInner += `<span class="proof-char-diff-mismatch">${esc}</span>`;
    }
  }
  return { leftInner, rightInner };
}

function proofFormatStatsSummary(edits, cards) {
  let typoAccepted = 0;
  let typoDiscarded = 0;
  let reformAccepted = 0;
  let reformDiscarded = 0;
  edits.forEach((edit, idx) => {
    const c = cards[idx] || { discarded: false, accepted: false };
    if (!c.accepted && !c.discarded) return;
    if (edit.type === "typo") {
      if (c.accepted) typoAccepted += 1;
      else if (c.discarded) typoDiscarded += 1;
    } else if (edit.type === "reformulation") {
      if (c.accepted) reformAccepted += 1;
      else if (c.discarded) reformDiscarded += 1;
    }
  });
  const parts = [];
  if (typoAccepted) parts.push(`${typoAccepted} typo${typoAccepted === 1 ? "" : "s"} accepted`);
  if (typoDiscarded) parts.push(`${typoDiscarded} typo${typoDiscarded === 1 ? "" : "s"} discarded`);
  if (reformAccepted) {
    parts.push(`${reformAccepted} reformulation${reformAccepted === 1 ? "" : "s"} accepted`);
  }
  if (reformDiscarded) {
    parts.push(`${reformDiscarded} reformulation${reformDiscarded === 1 ? "" : "s"} discarded`);
  }
  if (!parts.length) return "No suggestions accepted or discarded yet.";
  return `${parts.join(", ")}.`;
}

function proofSetSuggestedBusy(isBusy, hint) {
  const wrap = els.proofSuggestedBusy;
  if (!wrap) return;
  const hintEl = els.proofSuggestedBusyHint;
  wrap.classList.toggle("hidden", !isBusy);
  wrap.setAttribute("aria-hidden", isBusy ? "false" : "true");
  if (hintEl) {
    hintEl.textContent = isBusy ? hint || "Working…" : "";
  }
}

function styleSetSuggestedBusy(isBusy, hint) {
  const wrap = els.styleSuggestedBusy;
  if (!wrap) return;
  const hintEl = els.styleSuggestedBusyHint;
  wrap.classList.toggle("hidden", !isBusy);
  wrap.setAttribute("aria-hidden", isBusy ? "false" : "true");
  if (hintEl) {
    hintEl.textContent = isBusy ? hint || "Working…" : "";
  }
}

function proofInitModelSelect() {
  if (els.proofFileModel) {
    els.proofFileModel.innerHTML = proofModelSelectInnerHtml("gpt-5.4-mini");
  }
}

function proofSetViewerText(preEl, text) {
  let code = preEl.querySelector("code");
  if (!code) {
    code = document.createElement("code");
    preEl.appendChild(code);
  }
  code.textContent = text ?? "";
}

function proofBuildTree(rows) {
  const root = { children: new Map(), ends: [] };
  for (const row of rows) {
    const parts = String(row.dir || "")
      .replace(/\\/g, "/")
      .split("/")
      .filter(Boolean);
    let cur = root;
    for (const part of parts) {
      if (!cur.children.has(part)) {
        cur.children.set(part, { children: new Map(), ends: [] });
      }
      cur = cur.children.get(part);
    }
    cur.ends.push(row);
  }
  return root;
}

function proofRowMarkup(row, depthPx) {
  const exists = row.exists ? "" : `<span class="text-red-700">missing</span>`;
  let flags = "";
  if (!row.exists) flags += " proof-row-missing";
  if (row.visited) flags += " proof-row-visited";
  const selectHtml = `<select class="compact-select proof-row-model" aria-label="Model">${proofModelSelectInnerHtml(
    "gpt-5.4-mini",
  )}</select>`;
  return `
    <div class="proof-row flex flex-wrap items-center gap-1 py-1 border-b border-neutral-100${flags}"
         style="padding-left:${depthPx}px">
      <span class="mono">${escapeHtml(row.relative_path)}</span>
      ${exists}
      <span class="ml-auto shrink-0 flex flex-wrap gap-1 items-center">
        ${selectHtml}
        <button type="button" class="btn-secondary shrink-0" data-proof-view="${escapeHtml(
          row.relative_path,
        )}">View</button>
        <button type="button" class="btn-primary shrink-0 text-xxs" data-proof-analyze="${escapeHtml(
          row.relative_path,
        )}" title="Analyze with ChatGPT" ${row.exists ? "" : "disabled"}>Analyze with ChatGPT</button>
      </span>
    </div>`;
}

function styleRowMarkup(row, depthPx) {
  const exists = row.exists ? "" : `<span class="text-red-700">missing</span>`;
  let flags = "";
  if (!row.exists) flags += " proof-row-missing";
  if (row.visited) flags += " proof-row-visited";
  const selectHtml = `<select class="compact-select proof-row-model style-row-model" aria-label="Model">${proofModelSelectInnerHtml(
    "gpt-5.4-mini",
  )}</select>`;
  return `
    <div class="proof-row flex flex-wrap items-center gap-1 py-1 border-b border-neutral-100${flags}"
         style="padding-left:${depthPx}px">
      <span class="mono">${escapeHtml(row.relative_path)}</span>
      ${exists}
      <span class="ml-auto shrink-0 flex flex-wrap gap-1 items-center">
        ${selectHtml}
        <button type="button" class="btn-secondary shrink-0" data-style-view="${escapeHtml(
          row.relative_path,
        )}">View</button>
        <button type="button" class="btn-primary shrink-0 text-xxs" data-style-analyze="${escapeHtml(
          row.relative_path,
        )}" title="Analyze paragraph style" ${row.exists ? "" : "disabled"}>Analyze with ChatGPT</button>
      </span>
    </div>`;
}

function proofRenderTreeNode(node, depth) {
  const pad = depth * 10;
  let html = "";

  const childKeys = [...node.children.keys()].sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" }),
  );
  for (const name of childKeys) {
    const childPad = pad + (depth === 0 ? 0 : 6);
    html += `
      <div class="proof-node" style="padding-left:${childPad}px">
        <div class="proof-folder-label py-1">${escapeHtml(name)}</div>
        ${proofRenderTreeNode(node.children.get(name), depth + 1)}
      </div>`;
  }

  const ends = [...node.ends].sort((a, b) =>
    String(a.relative_path || "").localeCompare(String(b.relative_path || ""), undefined, {
      sensitivity: "base",
    }),
  );
  for (const row of ends) {
    html += proofRowMarkup(row, pad + (depth === 0 ? 0 : 14));
  }
  return html;
}

function styleRenderTreeNode(node, depth) {
  const pad = depth * 10;
  let html = "";

  const childKeys = [...node.children.keys()].sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" }),
  );
  for (const name of childKeys) {
    const childPad = pad + (depth === 0 ? 0 : 6);
    html += `
      <div class="proof-node" style="padding-left:${childPad}px">
        <div class="proof-folder-label py-1">${escapeHtml(name)}</div>
        ${styleRenderTreeNode(node.children.get(name), depth + 1)}
      </div>`;
  }

  const ends = [...node.ends].sort((a, b) =>
    String(a.relative_path || "").localeCompare(String(b.relative_path || ""), undefined, {
      sensitivity: "base",
    }),
  );
  for (const row of ends) {
    html += styleRowMarkup(row, pad + (depth === 0 ? 0 : 14));
  }
  return html;
}

async function loadProofTree() {
  try {
    const data = await api("/api/proof/tree");
    proofState.treeItems = [...(data.items || [])];
    els.proofTree.innerHTML =
      proofState.treeItems.length === 0
        ? `<p class="text-neutral-500 px-1">No inspected folders in project JSON.</p>`
        : proofRenderTreeNode(proofBuildTree(proofState.treeItems), 0);
    bindProofTreeClicks();
  } catch (error) {
    showError(error.message);
  }
}

async function loadParagraphStyleTree() {
  try {
    const data = await api("/api/paragraph-style/tree");
    paragraphStyleState.treeItems = [...(data.items || [])];
    els.styleTree.innerHTML =
      paragraphStyleState.treeItems.length === 0
        ? `<p class="text-neutral-500 px-1">No inspected folders in project JSON.</p>`
        : styleRenderTreeNode(proofBuildTree(paragraphStyleState.treeItems), 0);
    bindParagraphStyleTreeClicks();
  } catch (error) {
    showError(error.message);
  }
}

function synopsisWalkTree(nodes, fn) {
  for (const n of nodes || []) {
    fn(n);
    synopsisWalkTree(n.children || [], fn);
  }
}

function synopsisFoldGet(id) {
  if (id == null || id === "") return true;
  const k = String(id);
  if (!synopsisFoldSession.branchExpanded.has(k)) return true;
  return synopsisFoldSession.branchExpanded.get(k);
}

function synopsisFoldSet(id, expanded) {
  if (id == null || id === "") return;
  synopsisFoldSession.branchExpanded.set(String(id), Boolean(expanded));
}

/** Drop stale ids; new branch nodes default to expanded unless already in session. */
function synopsisFoldReconcile(tree) {
  const seen = new Set();
  synopsisWalkTree(tree, (n) => {
    const id = String(n.id ?? "");
    if (id) seen.add(id);
  });
  for (const k of synopsisFoldSession.branchExpanded.keys()) {
    if (!seen.has(k)) synopsisFoldSession.branchExpanded.delete(k);
  }
  synopsisWalkTree(tree, (n) => {
    const id = String(n.id ?? "");
    const ch = n.children;
    if (!id || !Array.isArray(ch) || ch.length === 0) return;
    if (!synopsisFoldSession.branchExpanded.has(id)) {
      synopsisFoldSession.branchExpanded.set(id, true);
    }
  });
}

function synopsisFoldApplyToType(levelType, expanded) {
  const want = String(levelType || "").toLowerCase();
  synopsisWalkTree(synopsisState.tree, (n) => {
    const t = String(n.type || "").toLowerCase();
    const ch = n.children;
    if (t === want && Array.isArray(ch) && ch.length > 0) {
      const id = String(n.id ?? "");
      if (id) synopsisFoldSet(id, expanded);
    }
  });
}

function synopsisMountSynopsisDom() {
  if (!els.synopsisTree) return;
  synopsisDestroySortables();
  els.synopsisTree.innerHTML = synopsisRenderTreeHtml(synopsisState.tree || []);
  if (els.synopsisTree.querySelector("ul.synopsis-tree-root")) {
    synopsisBindSortables();
  }
}

async function synopsisExportMarkdown() {
  if (!synopsisState.tree?.length || synopsisState.exportMdBusy || synopsisState.busy) return;
  synopsisState.exportMdBusy = true;
  synopsisBindBusy(true);
  if (els.synopsisBusyHint) els.synopsisBusyHint.textContent = "Writing full_content.md…";
  synopsisSetSaveUi("Exporting…");
  try {
    const branch_expanded = Object.fromEntries(synopsisFoldSession.branchExpanded);
    await api("/api/course-synopsis/export-markdown", {
      method: "POST",
      body: JSON.stringify({
        tree: synopsisState.tree,
        branch_expanded,
      }),
    });
    synopsisSetSaveUi("Wrote Markdown");
    showError("");
  } catch (err) {
    showError(err.message);
    synopsisSetSaveUi("");
  } finally {
    synopsisState.exportMdBusy = false;
    synopsisBindBusy(false);
    if (els.synopsisBusyHint) els.synopsisBusyHint.textContent = "Saving…";
  }
}

function synopsisReRenderTreeDom() {
  synopsisMountSynopsisDom();
}

function synopsisRebuildNodeMap(tree) {
  synopsisState.nodeById = new Map();
  const walk = (nodes) => {
    for (const n of nodes || []) {
      const id = String(n.id ?? "");
      if (id) synopsisState.nodeById.set(id, JSON.parse(JSON.stringify(n)));
      walk(n.children || []);
    }
  };
  walk(tree || []);
}

function synopsisDestroySortables() {
  for (const s of synopsisState.sortableInstances) {
    try {
      s.destroy();
    } catch {
      /* Sortable DOM may already be detached */
    }
  }
  synopsisState.sortableInstances = [];
}

function synopsisLiMarkup(node) {
  const rawId = String(node.id ?? "");
  const idEsc = escapeHtml(rawId);
  const kids = Array.isArray(node.children) ? node.children : [];
  const inner = kids.map((c) => synopsisLiMarkup(c)).join("");
  const hasKids = kids.length > 0;
  const expanded = !hasKids || synopsisFoldGet(rawId);
  const typ = escapeHtml(String((node.type || "").toLowerCase()));
  const title = escapeHtml(String(node.title ?? "(untitled)"));
  const collapsedCls = hasKids && !expanded ? " synopsis-branch-collapsed" : "";
  const foldGlyph = expanded ? "▾" : "▸";
  const foldCtl = hasKids
    ? `<button type="button" class="synopsis-fold-toggle" aria-expanded="${expanded}" aria-label="${expanded ? "Collapse branch" : "Expand branch"}" tabindex="0">${foldGlyph}</button>`
    : `<span class="synopsis-fold-placeholder" aria-hidden="true"></span>`;
  return `
    <li class="synopsis-node-li${hasKids ? " synopsis-node-li-branch" : " synopsis-node-li-leaf"}${collapsedCls}" data-id="${idEsc}">
      <div class="synopsis-node-row flex flex-wrap items-center gap-1 py-0.5">
        ${foldCtl}
        <button type="button" class="synopsis-drag-handle mono select-none shrink-0" title="Drag to reorder">≡</button>
        <span class="structure-kind synopsis-node-type">${typ}</span>
        <span class="synopsis-node-title">${title}</span>
      </div>
      <ul class="synopsis-children">${inner}</ul>
    </li>
  `;
}

function synopsisOnFoldToggleClick(ev) {
  const btn = ev.target.closest(".synopsis-fold-toggle");
  if (!btn || !els.synopsisTree?.contains(btn)) return;
  ev.preventDefault();
  ev.stopPropagation();
  const li = btn.closest(".synopsis-node-li");
  const rawId = li?.dataset?.id;
  if (rawId == null || rawId === "") return;
  synopsisFoldSet(rawId, !synopsisFoldGet(rawId));
  synopsisReRenderTreeDom();
}

function synopsisOnBulkFoldClick(ev) {
  const btn = ev.target.closest(".synopsis-fold-bulk");
  if (!btn || !els.tabPanelSynopsis?.contains(btn)) return;
  if (!synopsisState.tree?.length) return;
  const level = btn.dataset.synopsisFoldLevel;
  const action = btn.dataset.synopsisFoldAction;
  if (!level || !action) return;
  synopsisFoldApplyToType(level, action === "expand");
  synopsisReRenderTreeDom();
}

function synopsisRenderTreeHtml(tree) {
  if (!tree || !tree.length) {
    return `<p class="text-xxs text-neutral-500 px-1">No outline nodes in synopsis.</p>`;
  }
  return `<ul class="synopsis-tree-root">${tree.map((n) => synopsisLiMarkup(n)).join("")}</ul>`;
}

function synopsisSerializeUl(ul) {
  const out = [];
  if (!ul) return out;
  for (const li of ul.children) {
    if (!li.classList.contains("synopsis-node-li")) continue;
    const id = String(li.dataset.id ?? "");
    const base = synopsisState.nodeById.get(id);
    if (!base) continue;
    const sub = li.querySelector(":scope > ul.synopsis-children");
    const copy = JSON.parse(JSON.stringify(base));
    copy.children = synopsisSerializeUl(sub);
    out.push(copy);
  }
  return out;
}

function synopsisSerializeDomTree() {
  const rootUl = els.synopsisTree?.querySelector("ul.synopsis-tree-root");
  return synopsisSerializeUl(rootUl);
}

function synopsisClearSaveUiSoon() {
  clearTimeout(synopsisSaveUiTimer);
  synopsisSaveUiTimer = setTimeout(() => {
    if (els.synopsisSaveState) els.synopsisSaveState.textContent = "";
  }, 2000);
}

function synopsisSetSaveUi(shortText) {
  if (!els.synopsisSaveState) return;
  clearTimeout(synopsisSaveUiTimer);
  els.synopsisSaveState.textContent = shortText || "";
  if (shortText === "Saved") synopsisClearSaveUiSoon();
}

function synopsisBindBusy(show) {
  if (!els.synopsisBusy) return;
  els.synopsisBusy.classList.toggle("hidden", !show);
  els.synopsisBusy.setAttribute("aria-hidden", show ? "false" : "true");
}

function synopsisApplyPayload(data) {
  synopsisState.tree = [...(data.tree || [])];
  synopsisRebuildNodeMap(synopsisState.tree);
  synopsisFoldReconcile(synopsisState.tree);
  if (els.synopsisPathHint) {
    els.synopsisPathHint.textContent = data.path_relative || "00_CONTENT/course_synopsis.json";
  }
  synopsisMountSynopsisDom();
  showError("");
}

async function synopsisOnSortEnd(evt) {
  if (synopsisState.busy || typeof Sortable === "undefined") return;
  if (evt.oldIndex === evt.newIndex && evt.from === evt.to) return;

  synopsisState.busy = true;
  synopsisSetSaveUi("Saving…");
  synopsisBindBusy(true);
  try {
    const treeOut = synopsisSerializeDomTree();
    const data = await api("/api/course-synopsis/reorder", {
      method: "POST",
      body: JSON.stringify({ tree: treeOut }),
    });
    synopsisApplyPayload(data);
    synopsisSetSaveUi("Saved");
  } catch (err) {
    showError(err.message);
    synopsisSetSaveUi("");
    try {
      await loadSynopsisTree();
    } catch {
      /* surfaced above */
    }
  } finally {
    synopsisState.busy = false;
    synopsisBindBusy(false);
  }
}

function synopsisBindSortables() {
  synopsisDestroySortables();
  if (!els.synopsisTree || typeof Sortable === "undefined") {
    return;
  }
  const lists = els.synopsisTree.querySelectorAll(
    "ul.synopsis-tree-root, ul.synopsis-children",
  );
  lists.forEach((ul) => {
    const sortable = new Sortable(ul, {
      group: "synopsis",
      animation: 150,
      draggable: "> .synopsis-node-li",
      handle: ".synopsis-drag-handle",
      fallbackOnBody: true,
      swapThreshold: 0.65,
      ghostClass: "synopsis-sortable-ghost",
      dragClass: "synopsis-sortable-drag",
      onEnd: synopsisOnSortEnd,
    });
    synopsisState.sortableInstances.push(sortable);
  });
}

async function loadSynopsisTree() {
  if (!els.synopsisTree) return;
  synopsisDestroySortables();
  synopsisSetSaveUi("");
  try {
    const data = await api("/api/course-synopsis");
    synopsisApplyPayload(data);
  } catch (err) {
    synopsisState.tree = [];
    synopsisState.nodeById = new Map();
    synopsisFoldSession.branchExpanded.clear();
    if (err.status === 404) {
      showError("");
      if (els.synopsisPathHint) {
        els.synopsisPathHint.textContent = "course_synopsis.json (missing)";
      }
      const detail = err.message ? escapeHtml(err.message) : "";
      els.synopsisTree.innerHTML =
        `<p class="text-xxs text-neutral-600 px-1 leading-relaxed">Course synopsis JSON not found at the resolved path (default is <span class="mono">{root_dir}/00_CONTENT/course_synopsis.json</span>). If the file lives elsewhere (for example in this teaching repo while <span class="mono">root_dir</span> points at another LaTeX project), set ` +
        `<span class="mono">initial_project_structure</span> (e.g. <span class="mono">relative_path</span> + <span class="mono">course_synopsis</span>) in <span class="mono">main_project.json</span>, resolved next to that config file. Or set a single ` +
        `<span class="mono">course_synopsis_path</span> string. Generate or refresh the file with ` +
        `<span class="mono">conda activate python312 &amp;&amp; python 03_Scripts/build_course_synopsis.py</span>.</p>` +
        (detail
          ? `<p class="text-xxs text-red-700 mono break-all px-1 mt-1">Server: ${detail}</p>`
          : "");
    } else {
      showError(err.message);
      els.synopsisTree.innerHTML = `<p class="text-xxs text-neutral-500 px-1">Could not load synopsis.</p>`;
    }
  }
}

function bindProofTreeClicks() {
  els.proofTree.querySelectorAll("[data-proof-view]").forEach((button) => {
    button.addEventListener("click", () => proofOpenFileViewer(button.dataset.proofView, "proof"));
  });
  els.proofTree.querySelectorAll("[data-proof-analyze]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      const rowSel = button.closest(".proof-row")?.querySelector(".proof-row-model");
      const model = rowSel?.value || "gpt-5.4-mini";
      proofRunAnalyze(button.dataset.proofAnalyze, model);
    });
  });
}

function bindParagraphStyleTreeClicks() {
  els.styleTree.querySelectorAll("[data-style-view]").forEach((button) => {
    button.addEventListener("click", () => proofOpenFileViewer(button.dataset.styleView, "paragraphStyle"));
  });
  els.styleTree.querySelectorAll("[data-style-analyze]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      const rowSel = button.closest(".proof-row")?.querySelector(".style-row-model");
      const model = rowSel?.value || "gpt-5.4-mini";
      styleRunAnalyze(button.dataset.styleAnalyze, model);
    });
  });
}

function proofEnsureSession(rel) {
  if (!proofState.session || proofState.session.relativePath !== rel) {
    proofState.session = {
      relativePath: rel,
      fileText: "",
      cachedEdits: [],
      cards: [],
      lastModel: "gpt-5.4-mini",
    };
  }
}

function styleEnsureSession(rel) {
  if (!paragraphStyleState.session || paragraphStyleState.session.relativePath !== rel) {
    paragraphStyleState.session = {
      relativePath: rel,
      fileText: "",
      cachedEdits: [],
      cards: [],
      lastModel: "gpt-5.4-mini",
    };
  }
}

function proofStaleForEdit(edit) {
  if (!proofState.session || !proofState.session.fileText) return true;
  return !proofState.session.fileText.includes(edit.original_text);
}

function styleStaleForEdit(edit) {
  if (!paragraphStyleState.session || !paragraphStyleState.session.fileText) return true;
  return !paragraphStyleState.session.fileText.includes(edit.original_text);
}

function renderProofSidebar() {
  const statEl = els.proofStatsSummary;
  if (!proofState.session || !proofState.session.relativePath) {
    els.proofSessionPath.textContent = "";
    if (statEl) {
      statEl.textContent = "";
      statEl.classList.add("hidden");
    }
    els.proofCardsWrap.innerHTML =
      '<p class="text-xxs text-neutral-500">Run Analyze from the tree or the file viewer.</p>';
    return;
  }
  els.proofSessionPath.textContent = proofState.session.relativePath || "";
  const edits = proofState.session.cachedEdits || [];
  if (!edits.length) {
    if (statEl) {
      statEl.textContent = "";
      statEl.classList.add("hidden");
    }
    els.proofCardsWrap.innerHTML =
      '<p class="text-xxs text-neutral-500">No edits from the last ChatGPT analysis.</p>';
    return;
  }

  if (statEl) {
    statEl.textContent = proofFormatStatsSummary(edits, proofState.session.cards);
    statEl.classList.remove("hidden");
  }

  els.proofCardsWrap.innerHTML = edits
    .map((edit, idx) => {
      const cs = proofState.session.cards[idx] || { discarded: false, accepted: false };
      if (cs.accepted) {
        return `<div class="proof-change-card proof-change-card-proof-accepted text-xxs">
          Accepted: <span class="mono">${escapeHtml(edit.original_text.slice(0, 80))}${edit.original_text.length > 80 ? "…" : ""}</span>
        </div>`;
      }
      if (cs.discarded) {
        return `<div class="proof-change-card proof-change-card-proof-discarded text-xxs space-y-1">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-neutral-600">Discarded (${escapeHtml(edit.type)})</span>
            <button type="button" class="btn-primary shrink-0" disabled>Accept change</button>
          </div>
          <div class="text-neutral-500 mono text-[10px] truncate">${escapeHtml(edit.original_text)}</div>
        </div>`;
      }
      const stale = proofStaleForEdit(edit);
      const staleBadge = stale
        ? `<span class="text-amber-800 bg-amber-100 px-1 rounded">original not found in file</span>`
        : "";
      const typeTag = `<span class="text-neutral-500">[${escapeHtml(edit.type)}]</span>`;
      const { leftInner, rightInner } = proofSnippetsWithCharDiffHtml(
        edit.original_text,
        edit.replacement_text,
      );
      return `
        <article class="proof-change-card" data-proof-card="${idx}">
          <div class="flex flex-wrap items-center gap-1">
            ${typeTag}
            ${staleBadge}
            <span class="text-xxs text-neutral-600 flex-1 min-w-[8rem]">${escapeHtml(edit.explanation || "")}</span>
            <button type="button" class="btn-primary shrink-0" data-proof-accept="${idx}" ${
              stale ? "disabled" : ""
            }>Accept change</button>
            <button type="button" class="btn-secondary shrink-0" data-proof-discard="${idx}">Discard</button>
          </div>
          <div class="proof-diff-grid">
            <div>
              <div class="proof-diff-head">Original</div>
              <div class="proof-snippet-box proof-snippet-original">${leftInner}</div>
            </div>
            <div>
              <div class="proof-diff-head">Proposed</div>
              <div class="proof-snippet-box proof-snippet-prop">${rightInner}</div>
            </div>
          </div>
        </article>`;
    })
    .join("");

  els.proofCardsWrap.querySelectorAll("[data-proof-accept]").forEach((button) => {
    button.addEventListener("click", () => proofAcceptEdit(Number(button.dataset.proofAccept)));
  });
  els.proofCardsWrap.querySelectorAll("[data-proof-discard]").forEach((button) => {
    button.addEventListener("click", () => proofDiscardEdit(Number(button.dataset.proofDiscard)));
  });
}

function renderStyleSidebar() {
  const statEl = els.styleStatsSummary;
  if (!paragraphStyleState.session || !paragraphStyleState.session.relativePath) {
    els.styleSessionPath.textContent = "";
    if (statEl) {
      statEl.textContent = "";
      statEl.classList.add("hidden");
    }
    els.styleCardsWrap.innerHTML =
      '<p class="text-xxs text-neutral-500">Run Analyze from the tree or the file viewer.</p>';
    return;
  }
  els.styleSessionPath.textContent = paragraphStyleState.session.relativePath || "";
  const edits = paragraphStyleState.session.cachedEdits || [];
  if (!edits.length) {
    if (statEl) {
      statEl.textContent = "";
      statEl.classList.add("hidden");
    }
    els.styleCardsWrap.innerHTML =
      '<p class="text-xxs text-neutral-500">No edits from the last ChatGPT analysis.</p>';
    return;
  }

  if (statEl) {
    statEl.textContent = proofFormatStatsSummary(edits, paragraphStyleState.session.cards);
    statEl.classList.remove("hidden");
  }

  els.styleCardsWrap.innerHTML = edits
    .map((edit, idx) => {
      const cs = paragraphStyleState.session.cards[idx] || { discarded: false, accepted: false };
      if (cs.accepted) {
        return `<div class="proof-change-card proof-change-card-proof-accepted text-xxs">
          Accepted: <span class="mono">${escapeHtml(edit.original_text.slice(0, 80))}${edit.original_text.length > 80 ? "…" : ""}</span>
        </div>`;
      }
      if (cs.discarded) {
        return `<div class="proof-change-card proof-change-card-proof-discarded text-xxs space-y-1">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-neutral-600">Discarded (${escapeHtml(edit.type)})</span>
            <button type="button" class="btn-primary shrink-0" disabled>Accept change</button>
          </div>
          <div class="text-neutral-500 mono text-[10px] truncate">${escapeHtml(edit.original_text)}</div>
        </div>`;
      }
      const stale = styleStaleForEdit(edit);
      const staleBadge = stale
        ? `<span class="text-amber-800 bg-amber-100 px-1 rounded">original not found in file</span>`
        : "";
      const typeTag = `<span class="text-neutral-500">[${escapeHtml(edit.type)}]</span>`;
      const { leftInner, rightInner } = proofSnippetsWithCharDiffHtml(
        edit.original_text,
        edit.replacement_text,
      );
      return `
        <article class="proof-change-card" data-style-card="${idx}">
          <div class="flex flex-wrap items-center gap-1">
            ${typeTag}
            ${staleBadge}
            <span class="text-xxs text-neutral-600 flex-1 min-w-[8rem]">${escapeHtml(edit.explanation || "")}</span>
            <button type="button" class="btn-primary shrink-0" data-style-accept="${idx}" ${
              stale ? "disabled" : ""
            }>Accept change</button>
            <button type="button" class="btn-secondary shrink-0" data-style-discard="${idx}">Discard</button>
          </div>
          <div class="proof-diff-grid">
            <div>
              <div class="proof-diff-head">Original</div>
              <div class="proof-snippet-box proof-snippet-original">${leftInner}</div>
            </div>
            <div>
              <div class="proof-diff-head">Proposed</div>
              <div class="proof-snippet-box proof-snippet-prop">${rightInner}</div>
            </div>
          </div>
        </article>`;
    })
    .join("");

  els.styleCardsWrap.querySelectorAll("[data-style-accept]").forEach((button) => {
    button.addEventListener("click", () => styleAcceptEdit(Number(button.dataset.styleAccept)));
  });
  els.styleCardsWrap.querySelectorAll("[data-style-discard]").forEach((button) => {
    button.addEventListener("click", () => styleDiscardEdit(Number(button.dataset.styleDiscard)));
  });
}

function proofDiscardEdit(idx) {
  if (!proofState.session) return;
  while (proofState.session.cards.length <= idx) {
    proofState.session.cards.push({ discarded: false, accepted: false });
  }
  proofState.session.cards[idx] = {
    ...(proofState.session.cards[idx] || {}),
    discarded: true,
    accepted: false,
  };
  renderProofSidebar();
}

function styleDiscardEdit(idx) {
  if (!paragraphStyleState.session) return;
  while (paragraphStyleState.session.cards.length <= idx) {
    paragraphStyleState.session.cards.push({ discarded: false, accepted: false });
  }
  paragraphStyleState.session.cards[idx] = {
    ...(paragraphStyleState.session.cards[idx] || {}),
    discarded: true,
    accepted: false,
  };
  renderStyleSidebar();
}

async function proofAcceptEdit(idx) {
  if (!proofState.session || !proofState.session.cachedEdits[idx]) return;
  const edit = proofState.session.cachedEdits[idx];
  if (proofStaleForEdit(edit)) return;
  const key = `proof:apply:${proofState.session.relativePath}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  if (proofState.tab === "proof") {
    proofSetSuggestedBusy(true, "Applying change…");
  }
  render(); // disables other busy UI consistency
  try {
    await api("/api/proof/apply-edit", {
      method: "POST",
      body: JSON.stringify({
        relative_path: proofState.session.relativePath,
        original_text: edit.original_text,
        replacement_text: edit.replacement_text,
      }),
    });
    const file = await api(`/api/proof/file?path=${encodeURIComponent(proofState.session.relativePath)}`);
    proofState.session.fileText = file.text || "";
    if (file.warning && proofState.tab === "proof") {
      showError(file.warning);
    }
    while (proofState.session.cards.length <= idx) {
      proofState.session.cards.push({ discarded: false, accepted: false });
    }
    proofState.session.cards[idx] = { discarded: false, accepted: true };
    if (
      proofState.fileModalRelativePath === proofState.session.relativePath &&
      proofState.modalWorkflow !== "paragraphStyle" &&
      els.proofFileViewer
    ) {
      proofSetViewerText(els.proofFileViewer, proofState.session.fileText);
    }
    renderProofSidebar();
  } catch (error) {
    showProofApiErrorModal(error, { title: "Proofreading apply failed" });
  } finally {
    proofSetSuggestedBusy(false);
    state.busy.delete(key);
    render();
  }
}

async function styleAcceptEdit(idx) {
  if (!paragraphStyleState.session || !paragraphStyleState.session.cachedEdits[idx]) return;
  const edit = paragraphStyleState.session.cachedEdits[idx];
  if (styleStaleForEdit(edit)) return;
  const key = `style:apply:${paragraphStyleState.session.relativePath}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  if (proofState.tab === "paragraphStyle") {
    styleSetSuggestedBusy(true, "Applying change…");
  }
  render();
  try {
    await api("/api/paragraph-style/apply-edit", {
      method: "POST",
      body: JSON.stringify({
        relative_path: paragraphStyleState.session.relativePath,
        original_text: edit.original_text,
        replacement_text: edit.replacement_text,
      }),
    });
    const file = await api(`/api/proof/file?path=${encodeURIComponent(paragraphStyleState.session.relativePath)}`);
    paragraphStyleState.session.fileText = file.text || "";
    if (file.warning && proofState.tab === "paragraphStyle") {
      showError(file.warning);
    }
    while (paragraphStyleState.session.cards.length <= idx) {
      paragraphStyleState.session.cards.push({ discarded: false, accepted: false });
    }
    paragraphStyleState.session.cards[idx] = { discarded: false, accepted: true };
    if (
      proofState.fileModalRelativePath === paragraphStyleState.session.relativePath &&
      proofState.modalWorkflow === "paragraphStyle" &&
      els.proofFileViewer
    ) {
      proofSetViewerText(els.proofFileViewer, paragraphStyleState.session.fileText);
    }
    renderStyleSidebar();
  } catch (error) {
    showProofApiErrorModal(error, { title: "Paragraph-style apply failed" });
  } finally {
    styleSetSuggestedBusy(false);
    state.busy.delete(key);
    render();
  }
}

async function proofRunAnalyze(relativePath, model) {
  const key = `proof:analyze:${relativePath}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  switchAssistTab("proof");
  proofSetSuggestedBusy(true, "Analyzing with ChatGPT…");
  render();
  try {
    proofEnsureSession(relativePath);
    proofState.session.lastModel = model || "gpt-5.4-mini";
    const data = await api("/api/proof/analyze", {
      method: "POST",
      body: JSON.stringify({ relative_path: relativePath, model: model || "gpt-5.4-mini" }),
    });
    const file = await api(`/api/proof/file?path=${encodeURIComponent(relativePath)}`);
    proofState.session.fileText = file.text || "";
    proofState.session.cachedEdits = [...(data.edits || [])];
    proofState.session.cards = proofState.session.cachedEdits.map(() => ({
      discarded: false,
      accepted: false,
    }));
    if (data.warning) showError(data.warning);
    renderProofSidebar();
    if (
      proofState.fileModalRelativePath === relativePath &&
      proofState.modalWorkflow === "proof" &&
      els.proofFileModal &&
      !els.proofFileModal.classList.contains("hidden")
    ) {
      proofSetViewerText(els.proofFileViewer, proofState.session.fileText);
      if (els.proofFileModel && model) els.proofFileModel.value = model;
    }
    await loadProofTree();
  } catch (error) {
    showError(error.message);
    showProofApiErrorModal(error, { title: "Proofreading analyze failed" });
  } finally {
    proofSetSuggestedBusy(false);
    state.busy.delete(key);
    render();
  }
}

async function styleRunAnalyze(relativePath, model) {
  const key = `paragraph-style:analyze:${relativePath}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  switchAssistTab("paragraphStyle");
  styleSetSuggestedBusy(true, "Analyzing with ChatGPT…");
  render();
  try {
    styleEnsureSession(relativePath);
    paragraphStyleState.session.lastModel = model || "gpt-5.4-mini";
    const data = await api("/api/paragraph-style/analyze", {
      method: "POST",
      body: JSON.stringify({ relative_path: relativePath, model: model || "gpt-5.4-mini" }),
    });
    const file = await api(`/api/proof/file?path=${encodeURIComponent(relativePath)}`);
    paragraphStyleState.session.fileText = file.text || "";
    paragraphStyleState.session.cachedEdits = [...(data.edits || [])];
    paragraphStyleState.session.cards = paragraphStyleState.session.cachedEdits.map(() => ({
      discarded: false,
      accepted: false,
    }));
    if (data.warning) showError(data.warning);
    renderStyleSidebar();
    if (
      proofState.fileModalRelativePath === relativePath &&
      proofState.modalWorkflow === "paragraphStyle" &&
      els.proofFileModal &&
      !els.proofFileModal.classList.contains("hidden")
    ) {
      proofSetViewerText(els.proofFileViewer, paragraphStyleState.session.fileText);
      if (els.proofFileModel && model) els.proofFileModel.value = model;
    }
    await loadParagraphStyleTree();
  } catch (error) {
    showError(error.message);
    showProofApiErrorModal(error, { title: "Paragraph-style analyze failed" });
  } finally {
    styleSetSuggestedBusy(false);
    state.busy.delete(key);
    render();
  }
}

async function proofOpenFileViewer(relativePath, workflow) {
  const wf =
    workflow === "paragraphStyle"
      ? "paragraphStyle"
      : workflow === "proof"
        ? "proof"
        : proofState.tab === "paragraphStyle"
          ? "paragraphStyle"
          : "proof";
  proofState.modalWorkflow = wf;
  proofState.fileModalRelativePath = relativePath;
  if (wf === "paragraphStyle") {
    styleEnsureSession(relativePath);
  } else {
    proofEnsureSession(relativePath);
  }
  const sess = wf === "paragraphStyle" ? paragraphStyleState.session : proofState.session;
  els.proofFilePath.textContent = relativePath;
  if (els.proofFileModel) {
    const m =
      sess?.lastModel && sess.relativePath === relativePath ? sess.lastModel : "gpt-5.4-mini";
    els.proofFileModel.innerHTML = proofModelSelectInnerHtml(m);
  }
  els.proofFileModal.classList.remove("hidden");
  els.proofFileModal.setAttribute("aria-hidden", "false");

  await proofReloadFileViewer(false);
}

function proofCloseFileViewer() {
  els.proofFileModal.classList.add("hidden");
  els.proofFileModal.setAttribute("aria-hidden", "true");
  proofState.fileModalRelativePath = null;
  proofState.modalWorkflow = null;
}

async function proofReloadFileViewer(syncCards) {
  const rel =
    proofState.fileModalRelativePath ||
    proofState.session?.relativePath ||
    paragraphStyleState.session?.relativePath ||
    "";
  if (!rel) return;
  const wf = proofState.modalWorkflow || (proofState.tab === "paragraphStyle" ? "paragraphStyle" : "proof");
  try {
    const file = await api(`/api/proof/file?path=${encodeURIComponent(rel)}`);
    proofSetViewerText(els.proofFileViewer, file.text || "");
    const onAssistTab =
      proofState.tab === "paragraphStyle"
        ? "paragraphStyle"
        : proofState.tab === "proof"
          ? "proof"
          : null;
    if (wf === "paragraphStyle") {
      styleEnsureSession(rel);
      paragraphStyleState.session.fileText = file.text || "";
      if (file.warning && onAssistTab === "paragraphStyle") showError(file.warning);
      if (
        syncCards !== false &&
        paragraphStyleState.session.cachedEdits?.length &&
        onAssistTab === "paragraphStyle"
      ) {
        renderStyleSidebar();
      }
    } else {
      proofEnsureSession(rel);
      proofState.session.fileText = file.text || "";
      if (file.warning && onAssistTab === "proof") showError(file.warning);
      if (
        syncCards !== false &&
        proofState.session.cachedEdits?.length &&
        onAssistTab === "proof"
      ) {
        renderProofSidebar();
      }
    }
  } catch (error) {
    showError(error.message);
  }
}

function switchAssistTab(which) {
  proofState.tab = which;
  els.tabPanelMain.classList.toggle("hidden", which !== "main");
  els.tabPanelProof.classList.toggle("hidden", which !== "proof");
  if (els.tabPanelParagraphStyle) {
    els.tabPanelParagraphStyle.classList.toggle("hidden", which !== "paragraphStyle");
  }
  if (els.tabPanelSynopsis) {
    els.tabPanelSynopsis.classList.toggle("hidden", which !== "synopsis");
  }

  function styleBtn(btn, active) {
    if (!btn) return;
    btn.classList.toggle("bg-neutral-800", active);
    btn.classList.toggle("text-white", active);
    btn.classList.toggle("border-neutral-400", active);
    btn.classList.toggle("bg-white", !active);
    btn.classList.toggle("border-neutral-300", !active);
  }

  styleBtn(els.tabMainBtn, which === "main");
  styleBtn(els.tabProofBtn, which === "proof");
  styleBtn(els.tabParagraphStyleBtn, which === "paragraphStyle");
  styleBtn(els.tabSynopsisBtn, which === "synopsis");
}

async function reloadApp() {
  await loadState();
  await loadProofTree();
  await loadParagraphStyleTree();
  await loadSynopsisTree();
}

async function loadState() {
  try {
    const data = await api("/api/state");
    state.project = data.project;
    state.runs = [...(data.runs || [])].sort((a, b) => a.started_at - b.started_at);
    if (state.openRunId && !state.runs.some((run) => run.id === state.openRunId)) {
      state.openRunId = null;
    }
    state.tools = data.tools || {};
    render();
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

function render() {
  renderProject();
  syncToolsPanel();
  syncRunsPanel();
}

function selectionSpansElement(el) {
  if (!el) return false;
  const sel = getSelection();
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return false;
  try {
    const range = sel.getRangeAt(0);
    return typeof range.intersectsNode === "function"
      ? range.intersectsNode(el)
      : el.contains(range.commonAncestorContainer);
  } catch {
    return false;
  }
}

function renderProject() {
  if (!state.project) return;
  els.projectRoot.textContent = state.project.root_dir || "";
  els.buildPath.textContent = `Build: ${state.project.build_dir || ""}`;
  els.latexSourceBtn.disabled = !state.project.processed_tex_exists;
  els.bibtexSourceBtn.disabled = !state.project.processed_bib_exists;
  els.structureBtn.disabled = !state.project.processed_tex_exists;
  els.bibtexErrorsBtn.disabled = !state.project.processed_blg_exists;
  els.listFiguresBtn.disabled = !state.project.content_dir_exists;
  els.listTablesBtn.disabled = !state.project.content_dir_exists;
  els.compressPdfBtn.disabled =
    !state.project.processed_pdf_exists || state.busy.has("pdf:compress");
  if (state.project.processed_pdf_exists) {
    els.pdfLink.classList.remove("disabled");
    const u = new URL(state.project.pdf_url, window.location.origin);
    u.searchParams.set("t", String(Date.now()));
    els.pdfLink.href = u.href;
    els.pdfState.textContent = "available";
  } else {
    els.pdfLink.classList.add("disabled");
    els.pdfLink.href = "#";
    els.pdfState.textContent = "not generated yet";
  }
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightLatexHtml(text) {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/(%[^\n]*)/g, '<span class="source-comment">$1</span>')
    .replace(/(\\[a-zA-Z@]+|\\.)/g, '<span class="source-command">$1</span>')
    .replace(/(\{[^{}\n]{0,120}\})/g, '<span class="source-arg">$1</span>');
}

function highlightBibtexHtml(text) {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/(@[a-zA-Z]+)(\s*\{)/g, '<span class="source-entry">$1</span>$2')
    .replace(/^(\s*[a-zA-Z][a-zA-Z0-9_-]*)(\s*=)/gm, '<span class="source-field">$1</span>$2')
    .replace(/(%[^\n]*)/g, '<span class="source-comment">$1</span>');
}

function markSearchMatches(root, query) {
  const needle = String(query || "");
  if (!needle) return 0;
  const pattern = new RegExp(escapeRegExp(needle), "gi");
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }

  let count = 0;
  textNodes.forEach((node) => {
    const value = node.nodeValue || "";
    pattern.lastIndex = 0;
    if (!pattern.test(value)) return;
    pattern.lastIndex = 0;

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let match;
    while ((match = pattern.exec(value)) !== null) {
      fragment.append(document.createTextNode(value.slice(lastIndex, match.index)));
      const mark = document.createElement("mark");
      mark.className = "source-search-hit";
      mark.textContent = match[0];
      fragment.append(mark);
      lastIndex = match.index + match[0].length;
      count += 1;
      if (match[0].length === 0) pattern.lastIndex += 1;
    }
    fragment.append(document.createTextNode(value.slice(lastIndex)));
    node.parentNode.replaceChild(fragment, node);
  });
  return count;
}

function latexHeadingLevel(line) {
  const match = String(line).match(/^\s*\\(chapter|section|subsection|subsubsection)\*?\s*\{/);
  if (!match) return null;
  return { chapter: 1, section: 2, subsection: 3, subsubsection: 4 }[match[1]];
}

function buildLatexFoldRegions(lines) {
  const regions = new Map();
  const beginDocument = lines.findIndex((line) => /^\s*\\begin\{document\}/.test(line));
  if (beginDocument > 0) {
    regions.set(0, {
      end: beginDocument - 1,
      label: "preamble",
      level: 0,
    });
  }

  const headings = [];
  lines.forEach((line, index) => {
    const level = latexHeadingLevel(line);
    if (level !== null) headings.push({ index, level });
  });

  headings.forEach((heading, idx) => {
    const next = headings.slice(idx + 1).find((candidate) => candidate.level <= heading.level);
    const end = (next ? next.index : lines.length) - 1;
    if (end > heading.index) {
      regions.set(heading.index, {
        end,
        label: `lines ${heading.index + 2}-${end + 1}`,
        level: heading.level,
      });
    }
  });
  return regions;
}

function renderLatexSource(code, text) {
  const lines = String(text).split("\n");
  const regions = buildLatexFoldRegions(lines);
  const folded = state.source?.folded || new Set();
  const hiddenLines = new Set();

  folded.forEach((start) => {
    const region = regions.get(start);
    if (!region) return;
    for (let lineNo = start + 1; lineNo <= region.end; lineNo += 1) {
      hiddenLines.add(lineNo);
    }
  });

  code.innerHTML = lines
    .map((line, index) => {
      const region = regions.get(index);
      const isFolded = folded.has(index);
      const hidden = hiddenLines.has(index);
      const button = region
        ? `<button class="source-fold-btn" type="button" data-fold-line="${index}" title="${escapeHtml(
            region.label
          )}">${isFolded ? ">" : "v"}</button>`
        : '<span class="source-fold-spacer"></span>';
      return `<div class="source-line${hidden ? " source-line-hidden" : ""}" data-source-line="${index}">
        <span class="source-lineno" aria-hidden="true">${index + 1}</span>
        ${button}<span class="source-line-code">${highlightLatexHtml(line)}</span>
      </div>`;
    })
    .join("");

  code.querySelectorAll("[data-fold-line]").forEach((button) => {
    button.addEventListener("click", () => {
      const lineNo = Number(button.dataset.foldLine);
      if (!state.source) return;
      if (state.source.folded.has(lineNo)) {
        state.source.folded.delete(lineNo);
      } else {
        state.source.folded.add(lineNo);
      }
      renderSourceText(state.source.kind, state.source.text, els.sourceSearch.value);
    });
  });
}

function setSourceModalBusy(on, hintText = "") {
  if (!els.sourceModalBusy) return;
  const show = Boolean(on);
  els.sourceModalBusy.classList.toggle("hidden", !show);
  els.sourceModalBusy.setAttribute("aria-hidden", show ? "false" : "true");
  els.sourceDialogBox.setAttribute("aria-busy", show ? "true" : "false");
  if (els.sourceModalBusyHint) {
    els.sourceModalBusyHint.textContent = show ? hintText || "Loading…" : "";
  }
}

function renderWrappedPlainSourceLines(code, text, highlightLine) {
  const lines = String(text).split("\n");
  code.innerHTML = lines
    .map(
      (line, index) => `<div class="source-line" data-source-line="${index}">
      <span class="source-lineno" aria-hidden="true">${index + 1}</span>
      <span class="source-fold-spacer"></span><span class="source-line-code">${highlightLine(line)}</span>
    </div>`
    )
    .join("");
}

function ensureVisibleForJumpToSourceLine(zeroBasedIdx) {
  if (!state.source || state.source.kind !== "latex") return;
  const lines = String(state.source.text).split("\n");
  const regions = buildLatexFoldRegions(lines);
  let changed = false;
  for (const start of [...state.source.folded]) {
    const region = regions.get(start);
    if (!region) continue;
    if (zeroBasedIdx > start && zeroBasedIdx <= region.end) {
      state.source.folded.delete(start);
      changed = true;
    }
  }
  if (changed) {
    renderSourceText(state.source.kind, state.source.text, els.sourceSearch.value);
  }
}

function syncSourceWordWrapUI() {
  const latex = Boolean(state.source && state.source.kind === "latex");
  if (els.sourceWordWrapBtn) {
    els.sourceWordWrapBtn.classList.toggle("hidden", !latex);
    els.sourceWordWrapBtn.setAttribute("aria-pressed", latex && state.sourceLatexWordWrap ? "true" : "false");
  }
  if (els.sourceViewerScroll) {
    els.sourceViewerScroll.classList.toggle("source-viewer-scroll--wrap", latex && state.sourceLatexWordWrap);
  }
}

function jumpToSourceLineFromInput() {
  if (!state.source || !els.sourceJumpLine || !els.sourceViewerScroll) return;
  const n = Number.parseInt(String(els.sourceJumpLine.value || "").trim(), 10);
  if (!Number.isFinite(n)) return;

  const lineCount = String(state.source.text).split("\n").length;
  const maxLine = Math.max(lineCount, 1);
  const target = Math.min(Math.max(n, 1), maxLine);
  const idx = target - 1;

  ensureVisibleForJumpToSourceLine(idx);

  const code = els.sourceViewer.querySelector("code");
  const row = code?.querySelector(`[data-source-line="${idx}"]`);
  row?.scrollIntoView({ block: "center", inline: "nearest" });
}

function renderSourceText(kind, text, query = "") {
  const code = els.sourceViewer.querySelector("code");
  if (kind === "latex") {
    renderLatexSource(code, text);
  } else if (kind === "bibtex") {
    renderWrappedPlainSourceLines(code, text, highlightBibtexHtml);
  } else {
    renderWrappedPlainSourceLines(code, text, (line) => escapeHtml(line));
  }
  const matchCount = markSearchMatches(code, query);
  const firstMatch = code.querySelector(".source-search-hit");
  els.sourceSearchState.textContent = query ? `${matchCount} match${matchCount === 1 ? "" : "es"}` : "";
  if (firstMatch) {
    firstMatch.scrollIntoView({ block: "center", inline: "nearest" });
  } else if (els.sourceViewerScroll) {
    els.sourceViewerScroll.scrollTop = 0;
  }
}

function resetSourceModalSidePanel() {
  state.bibtexRefsReport = null;
  els.refsSearch.value = "";
  els.bibtexRefsViewer.innerHTML = "";
  els.refsSearchState.textContent = "";
  els.sourceSplit.classList.remove("source-split--dual");
  els.sourceDialogBox.classList.remove("source-dialog--wide");
  els.bibtexRefsCol.classList.add("hidden");
  setSourceModalBusy(false);
}

function bibtexRefsRowHaystack(entry) {
  const key = String(entry.key || "");
  const occ = entry.occurrences || [];
  return [key, ...occ.map((o) => `${o.path}:${String(o.line)}`)].join("\n").toLowerCase();
}

function renderBibtexRefs(query = "") {
  const report = state.bibtexRefsReport || {};
  const needle = String(query || "").trim().toLowerCase();
  const rows = Array.isArray(report.keys) ? report.keys : [];
  const filtered = needle ? rows.filter((row) => bibtexRefsRowHaystack(row).includes(needle)) : rows;

  const blocks = [];

  const errMsg = report.error ? String(report.error).trim() : "";
  if (errMsg) {
    blocks.push(`<p class="text-red-700 text-xxs mb-2">${escapeHtml(errMsg)}</p>`);
  }

  const relRoot = report.content_root_relative ? String(report.content_root_relative).trim() : "";
  if (relRoot) {
    blocks.push(
      `<div class="refs-muted mono text-xxs mb-2">${escapeHtml(relRoot)}</div>`,
    );
  }

  if (!rows.length) {
    blocks.push(`<p class="refs-muted text-xxs">No missing-database-entry warnings in .blg.</p>`);
  } else if (!filtered.length) {
    blocks.push(`<p class="refs-muted text-xxs">No keys match the filter.</p>`);
  }

  filtered.forEach((entry) => {
    const hits = Array.isArray(entry.occurrences) ? entry.occurrences : [];
    const list =
      hits.length === 0
        ? `<li class="refs-muted">No citation command match in scanned .tex / .tikz.</li>`
        : hits
            .map((h) => {
              const p = escapeHtml(String(h.path || ""));
              const ln = escapeHtml(String(h.line ?? ""));
              return `<li>${p} <span class="refs-muted">line ${ln}</span></li>`;
            })
            .join("");
    blocks.push(`
      <section class="refs-section">
        <details open>
          <summary>${escapeHtml(String(entry.key || ""))} <span class="refs-muted font-normal">(${hits.length})</span></summary>
          <ul class="refs-hits">${list}</ul>
        </details>
      </section>
    `);
  });

  els.bibtexRefsViewer.innerHTML = blocks.join("");
  const highlightCount = needle ? markSearchMatches(els.bibtexRefsViewer, needle) : 0;
  const totalHits = rows.reduce((acc, r) => acc + ((r.occurrences && r.occurrences.length) || 0), 0);
  els.refsSearchState.textContent = needle
    ? `${filtered.length} shown · ${highlightCount} match${highlightCount === 1 ? "" : "es"}`
    : `${rows.length} key(s) · ${totalHits} cite match(es)`;
}

async function openSource(kind) {
  try {
    resetSourceModalSidePanel();
    state.source = null;
    syncSourceWordWrapUI();
    const data = await api(`/api/source/${encodeURIComponent(kind)}?t=${Date.now()}`);
    state.source = {
      kind: data.kind,
      label: data.label,
      path: data.path,
      text: data.text || "",
      folded: new Set(),
    };
    els.sourceTitle.textContent = data.label || "Source";
    els.sourcePath.textContent = data.path || "";
    els.sourceSearch.value = "";
    if (els.sourceJumpLine) els.sourceJumpLine.value = "";
    els.sourceModal.classList.remove("hidden");
    els.sourceModal.setAttribute("aria-hidden", "false");
    renderSourceText(data.kind, state.source.text, "");
    syncSourceWordWrapUI();
    els.sourceSearch.focus();
  } catch (error) {
    showError(error.message);
  }
}

async function openBibtexErrors() {
  resetSourceModalSidePanel();
  state.source = null;
  syncSourceWordWrapUI();
  els.sourceTitle.textContent = "BibTeX errors";
  els.sourcePath.textContent = "";
  els.sourceViewer.querySelector("code").innerHTML = "";
  els.sourceSearch.value = "";
  if (els.sourceJumpLine) els.sourceJumpLine.value = "";
  els.sourceModal.classList.remove("hidden");
  els.sourceModal.setAttribute("aria-hidden", "false");
  try {
    setSourceModalBusy(true, "Reading .blg …");
    const ts = Date.now();
    const src = await api(`/api/source/blg?t=${ts}`);
    setSourceModalBusy(true, "Scanning 00_CONTENT (.tex / .tikz) …");
    let refs = { keys: [] };
    try {
      refs = await api(`/api/bibtex/missing-refs?t=${ts}`);
    } catch (err) {
      refs = {
        keys: [],
        error: err.message || String(err),
      };
    }

    state.source = {
      kind: src.kind,
      label: src.label,
      path: src.path,
      text: src.text || "",
      folded: new Set(),
    };
    state.bibtexRefsReport = refs;

    els.sourceTitle.textContent = src.label || "Source";
    els.sourcePath.textContent = src.path || "";
    els.sourceSearch.value = "";
    if (els.sourceJumpLine) els.sourceJumpLine.value = "";

    els.sourceSplit.classList.add("source-split--dual");
    els.sourceDialogBox.classList.add("source-dialog--wide");
    els.bibtexRefsCol.classList.remove("hidden");

    renderSourceText(src.kind, state.source.text, "");
    syncSourceWordWrapUI();
    renderBibtexRefs("");
    els.sourceSearch.focus();
  } catch (error) {
    closeSource();
    showError(error.message);
  } finally {
    setSourceModalBusy(false);
  }
}

function closeSource() {
  els.sourceModal.classList.add("hidden");
  els.sourceModal.setAttribute("aria-hidden", "true");
  resetSourceModalSidePanel();
  state.source = null;
  syncSourceWordWrapUI();
}

function labelPrefix(label) {
  return `[${String(label || "").trim()}]`;
}

function headingKindLabel(type) {
  const labels = {
    chapter: "Chapter",
    section: "Section",
    subsection: "Subsection",
    subsubsection: "Subsubsection",
  };
  return labels[type] || "Heading";
}

function renderStructureItems(items) {
  if (!items || !items.length) return "";
  return `
    <ul class="structure-items">
      ${items
        .map(
          (item) => `
            <li class="structure-item">
              <span class="structure-label mono">${escapeHtml(labelPrefix(item.label))}</span>
              <span class="structure-kind">${escapeHtml(item.type || "item")}</span>
              <span>${escapeHtml(item.caption || "(no caption)")}</span>
            </li>
          `
        )
        .join("")}
    </ul>
  `;
}

function renderStructureNodes(nodes, showEmpty = true) {
  if (!nodes || !nodes.length) {
    return showEmpty ? `<p class="text-xxs text-neutral-500">No headings found.</p>` : "";
  }
  return nodes
    .map(
      (node) => `
        <details class="structure-node structure-level-${escapeHtml(node.level)}" open>
          <summary>
            <span class="structure-label mono">${escapeHtml(labelPrefix(node.label))}</span>
            <span class="structure-kind">${escapeHtml(headingKindLabel(node.type))}</span>
            <span>${escapeHtml(node.title || "(untitled)")}</span>
          </summary>
          ${renderStructureItems(node.items)}
          <div class="structure-children">${renderStructureNodes(node.children, false)}</div>
        </details>
      `
    )
    .join("");
}

function structureItemHaystack(item) {
  return [item.type, item.label, item.caption].map((x) => String(x || "")).join("\n").toLowerCase();
}

function structureNodeHaystack(node) {
  return [node.type, headingKindLabel(node.type), node.label, node.title]
    .map((x) => String(x || ""))
    .join("\n")
    .toLowerCase();
}

function filterStructureNodes(nodes, query) {
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) {
    return { nodes: nodes || [], matches: 0 };
  }

  let matches = 0;
  const walk = (items) =>
    (items || [])
      .map((node) => {
        const nodeMatches = structureNodeHaystack(node).includes(needle);
        const filteredItems = (node.items || []).filter((item) =>
          structureItemHaystack(item).includes(needle)
        );
        const childResult = walk(node.children);
        if (!nodeMatches && filteredItems.length === 0 && childResult.length === 0) {
          return null;
        }
        matches += (nodeMatches ? 1 : 0) + filteredItems.length;
        return {
          ...node,
          items: nodeMatches ? node.items || [] : filteredItems,
          children: childResult,
        };
      })
      .filter(Boolean);

  return { nodes: walk(nodes), matches };
}

function renderStructure(query = "") {
  const result = filterStructureNodes(state.structure || [], query);
  els.structureViewer.innerHTML = renderStructureNodes(result.nodes, true);
  els.structureSearchState.textContent = query
    ? `${result.matches} match${result.matches === 1 ? "" : "es"}`
    : "";
}

async function openStructure() {
  try {
    const data = await api(`/api/structure?t=${Date.now()}`);
    state.structure = data.tree || [];
    els.structureTitle.textContent = data.label || "Document Structure";
    els.structurePath.textContent = data.path || "";
    els.structureSearch.value = "";
    renderStructure("");
    els.structureModal.classList.remove("hidden");
    els.structureModal.setAttribute("aria-hidden", "false");
    els.structureSearch.focus();
  } catch (error) {
    showError(error.message);
  }
}

function closeStructure() {
  els.structureModal.classList.add("hidden");
  els.structureModal.setAttribute("aria-hidden", "true");
}

function floatItemHaystack(item) {
  return [item.env, item.line, item.caption, item.label]
    .map((x) => String(x ?? ""))
    .join("\n")
    .toLowerCase();
}

function filterFloatInventory(groups, query) {
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) {
    let filesShown = 0;
    let itemsShown = 0;
    (groups || []).forEach((g) =>
      (g.files || []).forEach((f) => {
        filesShown += 1;
        itemsShown += (f.items || []).length;
      })
    );
    return { groups: groups || [], filesShown, itemsShown };
  }
  let filesShown = 0;
  let itemsShown = 0;
  const out = [];
  (groups || []).forEach((g) => {
    const files = [];
    (g.files || []).forEach((file) => {
      const allItems = file.items || [];
      const pathMatch = `${file.path} ${file.name}`.toLowerCase().includes(needle);
      const filtered = allItems.filter((it) => floatItemHaystack(it).includes(needle));
      const items = pathMatch && filtered.length === 0 ? allItems : filtered;
      if (!items.length) return;
      files.push({ ...file, items });
      filesShown += 1;
      itemsShown += items.length;
    });
    if (files.length) {
      out.push({ ...g, files });
    }
  });
  return { groups: out, filesShown, itemsShown };
}

function renderFloatCaptionParts(caption, label) {
  const cap = String(caption || "").trim();
  const lab = String(label || "").trim();
  return {
    capText: cap ? cap : "(no caption)",
    labText: lab ? lab : "(no label)",
  };
}

function renderFloatInventory(query = "") {
  const data = state.floatInventory || {};
  const needleRaw = String(query || "").trim();
  const needle = needleRaw.toLowerCase();
  const filtered = filterFloatInventory(data.groups || [], query);
  const blocks = [];
  const err = data.error ? String(data.error).trim() : "";
  if (err) {
    blocks.push(`<p class="text-red-700 text-xxs">${escapeHtml(err)}</p>`);
  }
  if (!filtered.groups.length && !err) {
    const kind = data.kind === "tables" ? "tables" : "figures";
    const msg = needle
      ? "No matches for this filter."
      : `No ${kind} found under ${data.content_root_relative || data.content_root || "00_CONTENT"}.`;
    blocks.push(`<p class="text-xxs text-neutral-500">${escapeHtml(msg)}</p>`);
  }
  filtered.groups.forEach((group) => {
    const dirLabel = group.dir && group.dir !== "." ? group.dir : "(content root)";
    const fileBlocks = group.files
      .map((file) => {
        const items = file.items || [];
        const list = items
          .map((it) => {
            const { capText, labText } = renderFloatCaptionParts(it.caption, it.label);
            return `<li class="float-inventory-item">
              <div><span class="mono text-xxs">${escapeHtml(file.path)}</span><span class="refs-muted"> line ${escapeHtml(
              String(it.line)
            )}</span> <span class="structure-kind">${escapeHtml(String(it.env || ""))}</span></div>
              <div class="float-inventory-detail"><span class="refs-muted">caption:</span> ${escapeHtml(capText)}</div>
              <div class="float-inventory-detail"><span class="refs-muted">label:</span> ${escapeHtml(labText)}</div>
            </li>`;
          })
          .join("");
        return `<details class="structure-node structure-level-1">
          <summary class="mono">${escapeHtml(file.name)} <span class="refs-muted font-normal">(${items.length})</span></summary>
          <ul class="structure-items">${list}</ul>
        </details>`;
      })
      .join("");
    blocks.push(`<details class="structure-node structure-level-1" open>
      <summary class="mono">${escapeHtml(dirLabel)} <span class="refs-muted font-normal">(${group.files.length} file(s))</span></summary>
      <div class="structure-children">${fileBlocks}</div>
    </details>`);
  });
  els.floatInventoryViewer.innerHTML = blocks.join("");
  const highlightCount = needleRaw ? markSearchMatches(els.floatInventoryViewer, needleRaw) : 0;
  if (needleRaw) {
    els.floatInventorySearchState.textContent = `${filtered.filesShown} file(s) · ${filtered.itemsShown} item(s) · ${highlightCount} highlight(s)`;
  } else {
    els.floatInventorySearchState.textContent = `${filtered.filesShown} file(s) · ${filtered.itemsShown} item(s)`;
  }
}

async function openFloatInventory(kind) {
  try {
    const data = await api(`/api/content/inventory/${encodeURIComponent(kind)}?t=${Date.now()}`);
    state.floatInventory = data;
    els.floatInventoryTitle.textContent =
      data.label || (kind === "figures" ? "List of figures" : "List of tables");
    els.floatInventoryRoot.textContent =
      data.content_root_relative || data.content_root || "";
    els.floatInventorySearch.value = "";
    renderFloatInventory("");
    els.floatInventoryModal.classList.remove("hidden");
    els.floatInventoryModal.setAttribute("aria-hidden", "false");
    els.floatInventorySearch.focus();
  } catch (error) {
    showError(error.message);
  }
}

function closeFloatInventory() {
  els.floatInventoryModal.classList.add("hidden");
  els.floatInventoryModal.setAttribute("aria-hidden", "true");
  state.floatInventory = null;
}

function computeToolsStructuralDigest() {
  const tools = Object.values(state.tools || {}).sort((a, b) =>
    String(a.key).localeCompare(String(b.key)),
  );
  if (!tools.length) return "empty";
  return JSON.stringify(
    tools.map((t) => ({
      key: t.key,
      label: t.label,
      port: t.port,
      status: t.status,
      status_label: t.status_label,
      can_start: t.can_start,
      can_stop: t.can_stop,
      can_force_stop: t.can_force_stop,
      command: t.command || "",
      error: t.error || "",
      port_open: t.port_open,
      pids: t.pids || [],
      has_output: Boolean(t.output && String(t.output).length > 0),
    })),
  );
}

function syncToolsPanel() {
  const digest = computeToolsStructuralDigest();
  const toolCount = Object.keys(state.tools || {}).length;
  const rowCount = els.toolsPanel.querySelectorAll("[data-tool-row]").length;
  if (
    cachedToolsPanelLayoutKey === null ||
    digest !== cachedToolsPanelLayoutKey ||
    toolCount !== rowCount
  ) {
    renderToolsFull();
    cachedToolsPanelLayoutKey = computeToolsStructuralDigest();
    return;
  }
  patchToolsPanelContents();
}

function patchToolsPanelContents() {
  const tools = Object.values(state.tools || {}).sort((a, b) =>
    String(a.key).localeCompare(String(b.key)),
  );
  for (const tool of tools) {
    const row = els.toolsPanel.querySelector(`[data-tool-row="${CSS.escape(tool.key)}"]`);
    if (!row) {
      cachedToolsPanelLayoutKey = null;
      return;
    }
    const busy = state.busy.has(`tool:${tool.key}`);
    const status = tool.status || "stopped";
    const pidText = tool.pids && tool.pids.length ? `pid ${tool.pids.join(",")}` : "";
    row.querySelectorAll("[data-tool]").forEach((btn) => {
      const op = btn.dataset.op;
      btn.disabled =
        (op === "start" && (!tool.can_start || busy)) ||
        (op === "stop" && (!tool.can_stop || busy)) ||
        (op === "force_stop" && (!tool.can_force_stop || busy));
    });

    const dot = row.querySelector('[data-tool-field="dot"]');
    if (dot) dot.className = `status-dot ${statusClass(status)}`;

    const labelEl = row.querySelector('[data-tool-field="label"]');
    if (labelEl) labelEl.textContent = tool.label || "";

    const st = row.querySelector('[data-tool-field="status"]');
    if (st) st.textContent = tool.status_label || status;

    const pidSpan = row.querySelector('[data-tool-field="pid"]');
    if (pidSpan) pidSpan.textContent = pidText;

    const portSpan = row.querySelector('[data-tool-field="port"]');
    if (portSpan) portSpan.textContent = `port ${tool.port}`;

    const link = row.querySelector('[data-tool-field="link"]');
    if (link) {
      const open = Boolean(tool.port_open);
      link.href = tool.url || "#";
      link.className = `${open ? "link" : "link disabled"} text-xxs ml-auto`;
    }

    const cmd = row.querySelector('[data-tool-field="command"]');
    if (cmd) {
      if (tool.command) {
        cmd.removeAttribute("hidden");
        cmd.classList.remove("hidden");
        cmd.textContent = tool.command;
        cmd.setAttribute("title", tool.command);
      } else {
        cmd.textContent = "";
        cmd.removeAttribute("title");
        cmd.classList.add("hidden");
      }
    }

    const err = row.querySelector('[data-tool-field="error"]');
    if (err) {
      if (tool.error) {
        err.removeAttribute("hidden");
        err.classList.remove("hidden");
        err.textContent = tool.error;
      } else {
        err.textContent = "";
        err.classList.add("hidden");
      }
    }

    let pre = row.querySelector("pre.tool-output");
    const out = tool.output || "";
    if (!out) {
      pre?.remove();
      continue;
    }
    if (!pre) {
      pre = document.createElement("pre");
      pre.className = "tool-output mono";
      row.appendChild(pre);
    }
    if (!selectionSpansElement(pre) && pre.textContent !== out) {
      pre.textContent = out;
      pre.scrollTop = pre.scrollHeight;
    }
  }
}

function renderToolsFull() {
  const tools = Object.values(state.tools || {}).sort((a, b) =>
    String(a.key).localeCompare(String(b.key)),
  );
  if (!tools.length) {
    els.toolsPanel.innerHTML = `<p class="text-xxs text-neutral-500">No tools configured.</p>`;
    return;
  }

  els.toolsPanel.innerHTML = tools
    .map((tool) => {
      const busy = state.busy.has(`tool:${tool.key}`);
      const status = tool.status || "stopped";
      const pidText = tool.pids && tool.pids.length ? `pid ${tool.pids.join(",")}` : "";
      const linkClass = tool.port_open ? "link" : "link disabled";
      const command = tool.command
        ? `<div class="text-xxs text-neutral-500 mono truncate" data-tool-field="command" title="${escapeHtml(
            tool.command
          )}">${escapeHtml(tool.command)}</div>`
        : `<div class="text-xxs text-neutral-500 mono truncate hidden" data-tool-field="command" hidden></div>`;
      const error = tool.error
        ? `<div class="text-red-700 text-xxs mt-1" data-tool-field="error">${escapeHtml(tool.error)}</div>`
        : `<div class="text-red-700 text-xxs mt-1 hidden" data-tool-field="error" hidden></div>`;
      const output = tool.output
        ? `<pre class="tool-output mono">${escapeHtml(tool.output)}</pre>`
        : "";
      return `
        <div class="tool-row px-1 py-1" data-tool-row="${escapeHtml(tool.key)}">
          <div class="flex items-center gap-2">
            <span class="status-dot ${statusClass(status)}" data-tool-field="dot"></span>
            <span class="font-semibold text-xxs" data-tool-field="label">${escapeHtml(tool.label)}</span>
            <span class="text-xxs text-neutral-500" data-tool-field="status">${escapeHtml(
              tool.status_label || status
            )}</span>
            <span class="text-xxs text-neutral-500" data-tool-field="pid">${escapeHtml(pidText)}</span>
            <span class="text-xxs text-neutral-500" data-tool-field="port">port ${escapeHtml(tool.port)}</span>
            <a class="${linkClass} text-xxs ml-auto" data-tool-field="link" href="${escapeHtml(
        tool.url
      )}" target="_blank" rel="noopener">open</a>
          </div>
          <div class="flex gap-1 mt-1">
            <button class="btn-secondary" type="button" data-tool="${escapeHtml(
              tool.key
            )}" data-op="start" ${!tool.can_start || busy ? "disabled" : ""}>start</button>
            <button class="btn-secondary" type="button" data-tool="${escapeHtml(
              tool.key
            )}" data-op="stop" ${!tool.can_stop || busy ? "disabled" : ""}>stop</button>
            <button class="btn-danger" type="button" data-tool="${escapeHtml(
              tool.key
            )}" data-op="force_stop" ${
        !tool.can_force_stop || busy ? "disabled" : ""
      }>force stop</button>
          </div>
          ${command}
          ${error}
          ${output}
        </div>
      `;
    })
    .join("");
}

function statusClass(status) {
  if (status === "owned" || status === "external") return "running";
  if (status === "starting") return "starting";
  if (status === "occupied") return "failed";
  return "";
}

function latestOpenRunId() {
  const running = state.runs.filter((run) => run.status === "running");
  if (running.length) return running[running.length - 1].id;
  if (state.openRunId && state.runs.some((run) => run.id === state.openRunId)) {
    return state.openRunId;
  }
  if (!state.runs.length) return null;
  return state.runs[state.runs.length - 1].id;
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (minutes < 1) return `${rest}s`;
  return `${minutes}m ${String(rest).padStart(2, "0")}s`;
}

function computeRunsPanelLayoutKey() {
  if (!state.runs.length) return "empty";
  return `${state.runs.map((r) => r.id).join("\0")}\x1f${String(latestOpenRunId() ?? "")}`;
}

function formatRunSummaryLine(run) {
  const code =
    run.returncode === null || run.returncode === undefined ? "" : ` code ${run.returncode}`;
  return `${run.name} | ${run.started_label} | ${formatDuration(run.duration_seconds)}${
    run.status === "running" ? " | running" : run.status === "warning" ? ` | warning${code}` : code
  }`;
}

function runDotCssClass(run) {
  if (run.status === "running") return "running";
  if (run.status === "failed") return "failed";
  if (run.status === "warning") return "starting";
  return "";
}

function renderRunsFull() {
  if (!state.runs.length) {
    els.runsPanel.innerHTML = `<p class="text-xxs text-neutral-500">No command output yet.</p>`;
    return;
  }
  const openId = latestOpenRunId();
  els.runsPanel.innerHTML = state.runs
    .map((run) => {
      const open = run.id === openId;
      const title = formatRunSummaryLine(run);
      return `
        <article class="run-item" data-run-id="${escapeHtml(run.id)}">
          <div class="run-header">
            <span class="status-dot ${runDotCssClass(run)}"></span>
            <button class="flex-1 min-w-0 text-left text-xxs truncate" type="button" data-run-toggle="${escapeHtml(
              run.id
            )}" title="${escapeHtml(title)}">${escapeHtml(title)}</button>
            <button class="btn-danger shrink-0" type="button" data-run-delete="${escapeHtml(
              run.id
            )}">delete</button>
          </div>
          ${
            open
              ? `<pre class="run-output mono" data-run-output="${escapeHtml(run.id)}"></pre>`
              : ""
          }
        </article>
      `;
    })
    .join("");

  state.runs.forEach((run) => {
    const pre = els.runsPanel.querySelector(`[data-run-output="${CSS.escape(run.id)}"]`);
    if (pre) {
      pre.textContent = run.output || "";
      pre.scrollTop = pre.scrollHeight;
    }
  });
}

function patchRunsPanelContents() {
  const openId = latestOpenRunId();
  const articles = [...els.runsPanel.querySelectorAll("article.run-item")];
  if (articles.length !== state.runs.length) {
    cachedRunsPanelLayoutKey = null;
    return;
  }
  for (let i = 0; i < state.runs.length; i += 1) {
    const run = state.runs[i];
    const article = articles[i];
    if (article.dataset.runId !== run.id) {
      cachedRunsPanelLayoutKey = null;
      return;
    }
    const dot = article.querySelector(".run-header > .status-dot");
    if (dot) dot.className = `status-dot ${runDotCssClass(run)}`;
    const toggleBtn = article.querySelector("[data-run-toggle]");
    if (toggleBtn) {
      const label = formatRunSummaryLine(run);
      toggleBtn.textContent = label;
      toggleBtn.title = label;
    }
    const shouldOpen = run.id === openId;
    let pre = article.querySelector(`pre[data-run-output="${CSS.escape(run.id)}"]`);
    if (shouldOpen) {
      if (!pre) {
        pre = document.createElement("pre");
        pre.className = "run-output mono";
        pre.dataset.runOutput = run.id;
        article.appendChild(pre);
      }
      const out = run.output || "";
      if (!selectionSpansElement(pre) && pre.textContent !== out) {
        pre.textContent = out;
        pre.scrollTop = pre.scrollHeight;
      }
    } else if (pre) {
      pre.remove();
    }
  }
}

function syncRunsPanel() {
  const layoutKey = computeRunsPanelLayoutKey();
  const hasArticles = Boolean(els.runsPanel.querySelector("article.run-item"));
  const expectArticles = state.runs.length > 0;
  if (
    cachedRunsPanelLayoutKey === null ||
    layoutKey !== cachedRunsPanelLayoutKey ||
    expectArticles !== hasArticles
  ) {
    renderRunsFull();
    cachedRunsPanelLayoutKey = layoutKey;
    return;
  }
  patchRunsPanelContents();
}

async function startAction(action) {
  const key = `action:${action}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  render();
  try {
    await api(`/api/actions/${encodeURIComponent(action)}`, { method: "POST" });
    await loadState();
  } catch (error) {
    showError(error.message);
  } finally {
    state.busy.delete(key);
    render();
  }
}

async function operateTool(tool, operation) {
  const key = `tool:${tool}`;
  if (state.busy.has(key)) return;
  state.busy.add(key);
  render();
  try {
    await api(`/api/tools/${encodeURIComponent(tool)}/${encodeURIComponent(operation)}`, {
      method: "POST",
    });
    await loadState();
  } catch (error) {
    showError(error.message);
  } finally {
    state.busy.delete(key);
    render();
  }
}

function formatBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value < 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

async function compressPdf() {
  const key = "pdf:compress";
  if (state.busy.has(key)) return;
  state.busy.add(key);
  els.compressPdfState.textContent = "compressing...";
  render();
  try {
    const data = await api("/api/pdf/compress", {
      method: "POST",
      body: JSON.stringify({ level: els.pdfCompressionLevel.value || "ebook" }),
    });
    const before = formatBytes(data.before_size);
    const after = formatBytes(data.after_size);
    els.compressPdfState.textContent = before && after ? `${before} -> ${after}` : "compressed";
    await loadState();
  } catch (error) {
    els.compressPdfState.textContent = "";
    showError(error.message);
  } finally {
    state.busy.delete(key);
    render();
  }
}

async function deleteRun(runId) {
  try {
    await api(`/api/runs/${encodeURIComponent(runId)}`, { method: "DELETE" });
    await loadState();
  } catch (error) {
    showError(error.message);
  }
}

async function clearRuns() {
  try {
    await api("/api/runs/clear", { method: "POST" });
    await loadState();
  } catch (error) {
    showError(error.message);
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => startAction(button.dataset.action));
});

els.clearBtn.addEventListener("click", clearRuns);
els.reloadBtn.addEventListener("click", reloadApp);

els.tabMainBtn.addEventListener("click", () => {
  switchAssistTab("main");
});
els.tabProofBtn.addEventListener("click", async () => {
  switchAssistTab("proof");
  await loadProofTree();
  renderProofSidebar();
});
els.tabParagraphStyleBtn?.addEventListener("click", async () => {
  switchAssistTab("paragraphStyle");
  await loadParagraphStyleTree();
  renderStyleSidebar();
});
els.tabSynopsisBtn?.addEventListener("click", async () => {
  switchAssistTab("synopsis");
  await loadSynopsisTree();
});
els.synopsisReloadBtn?.addEventListener("click", async () => {
  await loadSynopsisTree();
});
els.synopsisMarkdownBtn?.addEventListener("click", synopsisExportMarkdown);
els.synopsisTree?.addEventListener("click", synopsisOnFoldToggleClick);
els.tabPanelSynopsis?.addEventListener("click", synopsisOnBulkFoldClick);

proofInitModelSelect();
els.proofFileCloseBtn?.addEventListener("click", proofCloseFileViewer);
els.proofFileReloadBtn?.addEventListener("click", () =>
  proofReloadFileViewer(true),
);
els.proofFileAnalyzeBtn?.addEventListener("click", () => {
  const wf = proofState.modalWorkflow || "proof";
  const rel =
    proofState.fileModalRelativePath ||
    (wf === "paragraphStyle" ? paragraphStyleState.session?.relativePath : proofState.session?.relativePath);
  if (!rel) return;
  const model = els.proofFileModel?.value || "gpt-5.4-mini";
  if (wf === "paragraphStyle") {
    styleRunAnalyze(rel, model);
    return;
  }
  proofRunAnalyze(rel, model);
});
els.proofFileModal?.addEventListener("click", (event) => {
  if (event.target === els.proofFileModal) proofCloseFileViewer();
});
els.proofApiErrorCloseBtn?.addEventListener("click", closeProofApiErrorModal);
els.proofApiErrorModal?.addEventListener("click", (event) => {
  if (event.target === els.proofApiErrorModal) closeProofApiErrorModal();
});
els.latexSourceBtn.addEventListener("click", () => openSource("latex"));
els.bibtexSourceBtn.addEventListener("click", () => openSource("bibtex"));
els.structureBtn.addEventListener("click", openStructure);
els.bibtexErrorsBtn.addEventListener("click", openBibtexErrors);
els.listFiguresBtn.addEventListener("click", () => openFloatInventory("figures"));
els.listTablesBtn.addEventListener("click", () => openFloatInventory("tables"));
els.compressPdfBtn.addEventListener("click", compressPdf);
els.sourceCloseBtn.addEventListener("click", closeSource);
els.structureCloseBtn.addEventListener("click", closeStructure);
els.floatInventoryCloseBtn.addEventListener("click", closeFloatInventory);
els.sourceModal.addEventListener("click", (event) => {
  if (event.target === els.sourceModal) closeSource();
});
els.structureModal.addEventListener("click", (event) => {
  if (event.target === els.structureModal) closeStructure();
});
els.floatInventoryModal.addEventListener("click", (event) => {
  if (event.target === els.floatInventoryModal) closeFloatInventory();
});
els.structureSearch.addEventListener("input", () => {
  renderStructure(els.structureSearch.value);
});
els.floatInventorySearch.addEventListener("input", () => {
  if (!state.floatInventory) return;
  renderFloatInventory(els.floatInventorySearch.value);
});
els.sourceSearch.addEventListener("input", () => {
  if (!state.source) return;
  renderSourceText(state.source.kind, state.source.text, els.sourceSearch.value);
});
els.sourceJumpBtn?.addEventListener("click", () => jumpToSourceLineFromInput());
els.sourceWordWrapBtn?.addEventListener("click", () => {
  if (!state.source || state.source.kind !== "latex") return;
  state.sourceLatexWordWrap = !state.sourceLatexWordWrap;
  syncSourceWordWrapUI();
});
els.sourceJumpLine?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  jumpToSourceLineFromInput();
});
els.refsSearch.addEventListener("input", () => {
  if (!state.bibtexRefsReport) return;
  renderBibtexRefs(els.refsSearch.value);
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (els.proofApiErrorModal && !els.proofApiErrorModal.classList.contains("hidden")) {
    closeProofApiErrorModal();
    return;
  }
  if (!els.floatInventoryModal.classList.contains("hidden")) {
    closeFloatInventory();
  } else if (!els.proofFileModal.classList.contains("hidden")) {
    proofCloseFileViewer();
  } else if (!els.structureModal.classList.contains("hidden")) {
    closeStructure();
  } else if (!els.sourceModal.classList.contains("hidden")) {
    closeSource();
  }
});

els.toolsPanel.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-tool]");
  if (!btn || !els.toolsPanel.contains(btn)) return;
  operateTool(btn.dataset.tool, btn.dataset.op);
});

els.runsPanel.addEventListener("click", (event) => {
  const del = event.target.closest("[data-run-delete]");
  if (del && els.runsPanel.contains(del)) {
    event.preventDefault();
    deleteRun(del.dataset.runDelete);
    return;
  }
  const toggle = event.target.closest("[data-run-toggle]");
  if (toggle && els.runsPanel.contains(toggle)) {
    event.preventDefault();
    state.openRunId = toggle.dataset.runToggle;
    cachedRunsPanelLayoutKey = null;
    syncRunsPanel();
  }
});

loadState().then(async () => {
  await loadProofTree();
  await loadParagraphStyleTree();
  await loadSynopsisTree();
});
state.pollTimer = setInterval(loadState, 1000);
