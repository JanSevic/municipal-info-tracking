/* Obecní radar – statický web nad daty z GitHub Actions.
 * Pravidla filtru musí odpovídat collector/matching.py (filtr na webu = filtr v e-mailu).
 */
(() => {
  "use strict";

  const PAGE = 50;
  const $ = (s) => document.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k);
    return n;
  };
  const fmtDate = (iso) => {
    if (!iso) return "";
    const [y, m, d] = iso.slice(0, 10).split("-");
    return `${+d}. ${+m}. ${y}`;
  };
  const isoDaysAgo = (days) => {
    const d = new Date(); d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
  };
  const plural = (n, one, few, many) => (n === 1 ? one : n >= 2 && n <= 4 ? few : many);
  const toast = (msg) => {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2600);
  };

  // ---------- stav ----------
  const S = {
    meta: null, obce: [], obceByKod: new Map(), dupNames: new Set(), presets: [], site: {},
    months: {}, fulltext: {}, records: [],
    f: { preset: "drinov", sources: null, obce: [], keywords: [], mode: "or", q: "", from: isoDaysAgo(30), to: "" },
    shown: PAGE,
  };

  const kwCache = new Map();
  const kwRx = (kw) => {
    if (!kwCache.has(kw)) {
      // stejná pravidla jako collector/matching.py
      const k = kw.trim();
      const esc = k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const cs = k !== k.toLowerCase();
      const whole = cs && k.length <= 4;
      kwCache.set(kw, new RegExp(`(?<![\\p{L}\\p{N}_])${esc}${whole ? "(?![\\p{L}\\p{N}_])" : ""}`, cs ? "u" : "iu"));
    }
    return kwCache.get(kw);
  };

  // ---------- načtení dat ----------
  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  function neededMonths() {
    const all = S.meta.months;
    const from = S.f.from ? S.f.from.slice(0, 7) : "0000-00";
    const to = S.f.to ? S.f.to.slice(0, 7) : "9999-99";
    return all.filter((m) => m >= from && m <= to);
  }

  async function ensureData() {
    const months = neededMonths();
    const missing = months.filter((m) => !S.months[m]);
    if (missing.length) {
      const res = await Promise.all(missing.map((m) => getJSON(`data/records/${m}.json`).catch(() => [])));
      missing.forEach((m, i) => (S.months[m] = res[i]));
    }
    if (S.f.keywords.length) {
      const ftMissing = months.filter((m) => !S.fulltext[m]);
      if (ftMissing.length) {
        const res = await Promise.all(ftMissing.map((m) => getJSON(`data/fulltext/${m}.json`).catch(() => ({}))));
        ftMissing.forEach((m, i) => (S.fulltext[m] = res[i]));
      }
    }
    S.records = months.flatMap((m) => S.months[m]);
  }

  // ---------- filtr ----------
  function kwHits(rec) {
    if (!S.f.keywords.length) return [];
    const month = (rec.published || "").slice(0, 7);
    const hay = `${rec.title}\n${rec.category || ""}\n${(S.fulltext[month] || {})[rec.id] || rec.snippet || ""}`;
    return S.f.keywords.filter((k) => kwRx(k).test(hay));
  }

  function fullText(rec) {
    return (S.fulltext[(rec.published || "").slice(0, 7)] || {})[rec.id] || "";
  }

  // výňatek z místa prvního nálezu (klíčové slovo nebo vybraná obec)
  function snippetNode(rec, hits) {
    const txt = fullText(rec) || rec.snippet || "";
    if (!txt) return null;
    const pats = hits.map(kwRx);
    for (const k of S.f.obce) {
      const o = S.obceByKod.get(k);
      if (o && (rec.obce || []).includes(k)) {
        const first = o.nazev.split(" ")[0];
        const stem = first.length > 4 ? first.replace(/[aeiouyáéíóúůýě]$/i, "") : first;
        pats.push(new RegExp(`(?<![\\p{L}\\p{N}_])${stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "u"));
      }
    }
    let best = null;
    for (const rx of pats) {
      const m = rx.exec(txt);
      if (m && (!best || m.index < best.index)) best = { index: m.index, len: m[0].length };
    }
    if (!best) {
      const short = txt.slice(0, 260);
      return el("p", { class: "snippet" }, short + (txt.length > 260 ? "…" : ""));
    }
    const a = Math.max(0, best.index - 130), b = Math.min(txt.length, best.index + best.len + 170);
    let end = best.index + best.len;
    while (end < txt.length && /[\p{L}\p{N}]/u.test(txt[end])) end++;
    return el("p", { class: "snippet" }, a > 0 ? "…" : "", txt.slice(a, best.index),
      el("mark", {}, txt.slice(best.index, end)), txt.slice(end, b), b < txt.length ? "…" : "");
  }

  function passes(rec) {
    const f = S.f;
    if (f.sources && !f.sources.includes(rec.source)) return false;
    if (f.from && rec.published < f.from) return false;
    if (f.to && rec.published > f.to) return false;
    if (f.q) {
      const q = f.q.toLocaleLowerCase("cs");
      if (!`${rec.title} ${rec.ref || ""} ${rec.category || ""}`.toLocaleLowerCase("cs").includes(q)) return false;
    }
    const wantObce = f.obce.length > 0, wantKw = f.keywords.length > 0;
    if (!wantObce && !wantKw) return true;
    const hitObec = wantObce && (rec.obce || []).some((k) => f.obce.includes(k));
    const hitKw = wantKw && kwHits(rec).length > 0;
    if (f.mode === "and" && wantObce && wantKw) return hitObec && hitKw;
    return hitObec || hitKw;
  }

  // ---------- URL ----------
  function toHash() {
    const f = S.f, p = new URLSearchParams();
    p.set("p", f.preset);
    if (f.preset === "vlastni") {
      if (f.sources) p.set("src", f.sources.join(","));
      if (f.obce.length) p.set("obce", f.obce.join(","));
      if (f.keywords.length) p.set("kw", f.keywords.join("|"));
      if (f.mode !== "or") p.set("mode", f.mode);
    }
    if (f.q) p.set("q", f.q);
    p.set("od", f.from || "");
    if (f.to) p.set("do", f.to);
    return "#" + p.toString();
  }
  function fromHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (!p.has("p")) return;
    const preset = p.get("p");
    if (preset !== "vlastni" && S.presets.some((x) => x.id === preset)) applyPreset(preset, false);
    else {
      S.f.preset = "vlastni";
      S.f.sources = p.get("src") ? p.get("src").split(",") : null;
      S.f.obce = p.get("obce") ? p.get("obce").split(",").map(Number) : [];
      S.f.keywords = p.get("kw") ? p.get("kw").split("|") : [];
      S.f.mode = p.get("mode") || "or";
    }
    S.f.q = p.get("q") || "";
    if (p.has("od")) S.f.from = p.get("od");
    S.f.to = p.get("do") || "";
  }

  // ---------- vykreslení filtrů ----------
  function applyPreset(id, rerender = true) {
    const p = S.presets.find((x) => x.id === id);
    S.f.preset = id;
    S.f.sources = p.filter.sources ? [...p.filter.sources] : null;
    S.f.obce = [...(p.filter.obce || [])];
    S.f.keywords = [...(p.filter.keywords || [])];
    S.f.mode = p.filter.mode || "or";
    if (rerender) update();
  }
  function markCustom() { S.f.preset = "vlastni"; }

  function renderPresets() {
    const box = $("#presets"); box.replaceChildren();
    const opts = [...S.presets.map((p) => ({ id: p.id, name: p.name })), { id: "vlastni", name: "Vlastní" }];
    for (const o of opts) {
      box.append(el("button", {
        type: "button", role: "radio", "aria-checked": String(S.f.preset === o.id),
        onclick: () => { if (o.id === "vlastni") { markCustom(); update(); } else applyPreset(o.id); },
      }, o.name));
    }
    const p = S.presets.find((x) => x.id === S.f.preset);
    $("#preset-desc").textContent = p ? p.popis : "Vlastní výběr zdrojů, obcí a klíčových slov.";
  }

  function renderChips() {
    const oc = $("#obce-chips"); oc.replaceChildren();
    for (const k of S.f.obce) {
      const o = S.obceByKod.get(k);
      oc.append(el("span", { class: "chip" }, o ? o.nazev : String(k),
        o ? el("small", {}, ` (${o.okres})`) : null,
        el("button", { type: "button", "aria-label": "Odebrat", onclick: () => { S.f.obce = S.f.obce.filter((x) => x !== k); markCustom(); update(); } }, "×")));
    }
    const kc = $("#kw-chips"); kc.replaceChildren();
    for (const k of S.f.keywords) {
      kc.append(el("span", { class: "chip" }, k,
        el("button", { type: "button", "aria-label": "Odebrat", onclick: () => { S.f.keywords = S.f.keywords.filter((x) => x !== k); markCustom(); update(); } }, "×")));
    }
    $("#mode-sec").hidden = !(S.f.obce.length && S.f.keywords.length);
    document.querySelectorAll("input[name=mode]").forEach((r) => (r.checked = r.value === S.f.mode));
  }

  const STATUS_TXT = { blokovano: "nedostupné z GitHubu", pripravuje: "připravuje se" };
  function renderSources() {
    const box = $("#sources"); box.replaceChildren();
    const groups = {};
    for (const s of S.meta.sources) (groups[s.group] ||= []).push(s);
    for (const [g, list] of Object.entries(groups)) {
      const grp = el("div", { class: "src-group" }, el("h3", {}, g));
      for (const s of list) {
        const checked = !S.f.sources || S.f.sources.includes(s.id);
        grp.append(el("label", { class: "src" },
          el("input", { type: "checkbox", checked, onchange: (e) => toggleSource(s.id, e.target.checked) }),
          el("span", {}, s.name,
            s.govradar ? el("span", { class: "badge gr", title: "Zdroj sledovaný i GovRadarem" }, "GovRadar") : null,
            s.status !== "ok" ? el("span", { class: "badge warn" }, STATUS_TXT[s.status] || s.status) : null)));
      }
      box.append(grp);
    }
  }
  function toggleSource(id, on) {
    const all = S.meta.sources.map((s) => s.id);
    let cur = S.f.sources ? [...S.f.sources] : [...all];
    cur = on ? [...new Set([...cur, id])] : cur.filter((x) => x !== id);
    S.f.sources = cur.length === all.length ? null : cur;
    markCustom(); update();
  }

  // ---------- výsledky ----------
  function renderList() {
    const recs = S.records.filter(passes).sort((a, b) => (b.published || "").localeCompare(a.published || "") || b.id.localeCompare(a.id));
    $("#count").textContent = recs.length.toLocaleString("cs");
    $("#count-label").textContent = plural(recs.length, "záznam", "záznamy", "záznamů");
    const names = Object.fromEntries(S.meta.sources.map((s) => [s.id, s.name]));
    const list = $("#list"); list.replaceChildren();
    for (const r of recs.slice(0, S.shown)) {
      const hits = kwHits(r);
      const obceTags = (r.obce || []).map((k) => S.obceByKod.get(k)).filter(Boolean);
      obceTags.sort((a, b) => S.f.obce.includes(b.kod) - S.f.obce.includes(a.kod));
      list.append(el("li", { class: "item" },
        el("div", { class: "meta" },
          el("span", { class: "src-name" }, names[r.source] || r.source),
          el("time", { datetime: r.published }, fmtDate(r.published)),
          r.valid_to ? el("span", {}, `do ${fmtDate(r.valid_to)}`) : null,
          r.category ? el("span", {}, r.category) : null,
          r.ref ? el("span", {}, r.ref) : null),
        el("h3", {}, el("a", { href: r.url, target: "_blank", rel: "noopener" }, r.title || "(bez názvu)")),
        snippetNode(r, hits),
        r.docs && r.docs.length ? el("div", { class: "docs" }, r.docs.slice(0, 6).filter((d) => d.url).map((d) => el("a", { href: d.url, target: "_blank", rel: "noopener" }, "📎 " + d.name))) : null,
        el("div", { class: "tags" },
          hits.map((k) => el("span", { class: "tag hit" }, k)),
          obceTags.slice(0, 8).map((o) => el("span", { class: "tag" + (S.f.obce.includes(o.kod) ? " hit" : ""), title: `okres ${o.okres}` },
            S.dupNames.has(o.nazev) ? `${o.nazev} (${o.okres})` : o.nazev)),
          obceTags.length > 8 ? el("span", { class: "tag" }, `+${obceTags.length - 8}`) : null,
          r.text_status === "bez_textu" ? el("span", { class: "tag warn", title: "Příloha neobsahuje čitelný text (sken) – zkontrolujte ručně." }, "příloha bez textu") : null,
          r.text_status === "nestazeno" ? el("span", { class: "tag warn", title: "Příloha je příliš velká nebo archiv – text se neprohledával." }, "příloha neprohledána") : null)));
    }
    $("#more").hidden = recs.length <= S.shown;
    $("#empty").hidden = recs.length > 0;
  }

  async function update({ keepPage = false } = {}) {
    if (!keepPage) S.shown = PAGE;
    renderPresets(); renderChips(); renderSources();
    $("#q").value = S.f.q; $("#from").value = S.f.from; $("#to").value = S.f.to;
    history.replaceState(null, "", toHash());
    try { await ensureData(); } catch (e) { toast("Nepodařilo se načíst data."); console.error(e); }
    renderList();
  }

  // ---------- obce – našeptávač ----------
  function setupObecCombo() {
    const input = $("#obec-input"), listEl = $("#obec-list");
    let items = [], active = -1;
    const norm = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
    const close = () => { listEl.hidden = true; active = -1; };
    const add = (o) => {
      if (!S.f.obce.includes(o.kod)) S.f.obce.push(o.kod);
      input.value = ""; close(); markCustom(); update();
    };
    const draw = () => {
      listEl.replaceChildren(...items.map((o, i) => el("li", {
        role: "option", "aria-selected": String(i === active), onmousedown: (e) => { e.preventDefault(); add(o); },
      }, o.nazev, el("small", {}, ` – okres ${o.okres}`))));
      listEl.hidden = !items.length;
    };
    input.addEventListener("input", () => {
      const q = norm(input.value.trim());
      items = q.length < 2 ? [] : S.obce.filter((o) => norm(o.nazev).startsWith(q)).concat(
        S.obce.filter((o) => !norm(o.nazev).startsWith(q) && norm(o.nazev).includes(q))).slice(0, 12);
      active = items.length ? 0 : -1; draw();
    });
    input.addEventListener("keydown", (e) => {
      if (listEl.hidden) return;
      if (e.key === "ArrowDown") { active = Math.min(active + 1, items.length - 1); draw(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); draw(); e.preventDefault(); }
      else if (e.key === "Enter" && active >= 0) { add(items[active]); e.preventDefault(); }
      else if (e.key === "Escape") close();
    });
    input.addEventListener("blur", close);
  }

  // ---------- odběr e-mailem ----------
  async function encryptEmail(email) {
    const pem = await (await fetch("config/public_key.pem", { cache: "no-cache" })).text();
    const b64 = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
    const der = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const key = await crypto.subtle.importKey("spki", der, { name: "RSA-OAEP", hash: "SHA-256" }, false, ["encrypt"]);
    const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "RSA-OAEP" }, key, new TextEncoder().encode(email)));
    let bin = ""; ct.forEach((b) => (bin += String.fromCharCode(b)));
    return "enc:" + btoa(bin);
  }

  function setupSubscribe() {
    const dlg = $("#sub-dialog"), form = $("#sub-form");
    $("#subscribe").addEventListener("click", () => {
      $("#sub-out").hidden = true; form.reset();
      const p = S.presets.find((x) => x.id === S.f.preset);
      form.elements.name.value = p ? p.name : "";
      dlg.showModal();
    });
    $("#sub-generate").addEventListener("click", async () => {
      if (!form.reportValidity()) return;
      const fd = new FormData(form);
      let email;
      try { email = await encryptEmail(String(fd.get("email")).trim()); }
      catch (e) { console.error(e); toast("Šifrovací klíč není k dispozici – viz README."); return; }
      const id = Array.from(crypto.getRandomValues(new Uint8Array(4)), (b) => b.toString(16).padStart(2, "0")).join("");
      const entry = {
        id, name: String(fd.get("name")).trim(), frequency: fd.get("frequency"),
        created: new Date().toISOString().slice(0, 10),
        filter: { sources: S.f.sources, obce: S.f.obce, keywords: S.f.keywords, mode: S.f.mode },
        _obce_nazvy: S.f.obce.map((k) => (S.obceByKod.get(k) || {}).nazev).filter(Boolean),
        email,
      };
      $("#sub-json").value = JSON.stringify(entry, null, 1) + ",";
      if (S.site.repo) {
        $("#sub-edit").href = `https://github.com/${S.site.repo}/edit/${S.site.branch || "main"}/config/subscriptions.json`;
        $("#sub-edit").hidden = false;
      } else $("#sub-edit").hidden = true;
      $("#sub-out").hidden = false;
    });
    $("#sub-copy").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText($("#sub-json").value); toast("Zkopírováno."); }
      catch { $("#sub-json").select(); }
    });
  }

  function renderStatus() {
    const fmt = (s) => (s ? fmtDate(s) + " " + s.slice(11, 16) : "–");
    $("#lastrun").textContent = S.meta.last_run ? `Aktualizováno ${fmt(S.meta.last_run)}` : "";
    $("#status").replaceChildren(
      el("tr", {}, el("th", {}, "Zdroj"), el("th", {}, "Poslední úspěšné stažení"), el("th", {}, "Poznámka")),
      ...S.meta.sources.map((s) => el("tr", {},
        el("td", {}, el("a", { href: s.url, target: "_blank", rel: "noopener" }, s.name)),
        el("td", { class: s.last_ok ? "ok" : "" }, fmt(s.last_ok)),
        el("td", { class: s.last_error ? "bad" : "" }, s.status !== "ok" ? STATUS_TXT[s.status] : (s.last_error || "")))));
  }

  // ---------- start ----------
  async function init() {
    const [meta, obce, presets, site] = await Promise.all([
      getJSON("data/meta.json"), getJSON("config/obce.json"), getJSON("config/presets.json"),
      getJSON("config/site.json").catch(() => ({})),
    ]);
    Object.assign(S, { meta, obce, presets, site });
    const seen = new Set();
    obce.forEach((o) => { S.obceByKod.set(o.kod, o); if (seen.has(o.nazev)) S.dupNames.add(o.nazev); seen.add(o.nazev); });
    applyPreset("drinov", false);
    fromHash();
    renderStatus();

    $("#q").addEventListener("input", (e) => { S.f.q = e.target.value.trim(); clearTimeout(init._q); init._q = setTimeout(update, 200); });
    $("#from").addEventListener("change", (e) => { S.f.from = e.target.value; update(); });
    $("#to").addEventListener("change", (e) => { S.f.to = e.target.value; update(); });
    $("#quick-range").addEventListener("click", (e) => {
      const d = e.target.dataset.days; if (d == null) return;
      S.f.from = d === "0" ? "" : isoDaysAgo(+d); S.f.to = ""; update();
    });
    $("#kw-input").addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const v = e.target.value.trim();
      if (v && !S.f.keywords.includes(v)) { S.f.keywords.push(v); markCustom(); update(); }
      e.target.value = "";
    });
    document.querySelectorAll("input[name=mode]").forEach((r) => r.addEventListener("change", () => { S.f.mode = r.value; markCustom(); update(); }));
    $("#src-all").addEventListener("click", () => { S.f.sources = null; markCustom(); update(); });
    $("#src-none").addEventListener("click", () => { S.f.sources = []; markCustom(); update(); });
    $("#more").addEventListener("click", () => { S.shown += PAGE; renderList(); });
    $("#share").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(location.href); toast("Odkaz zkopírován."); } catch { toast(location.href); }
    });
    window.addEventListener("hashchange", () => { if (location.hash !== toHash()) { fromHash(); update(); } });
    $("#filters-toggle").addEventListener("click", (e) => {
      const on = document.body.classList.toggle("show-filters");
      e.target.setAttribute("aria-expanded", String(on));
    });
    setupObecCombo();
    setupSubscribe();
    update();
  }

  init().catch((e) => {
    console.error(e);
    $("#lastrun").textContent = "Data zatím nejsou k dispozici.";
    $("#empty").hidden = false;
    $("#empty").textContent = "Data zatím nejsou k dispozici – počkejte na první běh sběru.";
  });
})();
