/* FastAPIzza shared client code: API access, auth guards, safe DOM helpers, UI primitives.
   Nothing here builds HTML from strings, so server data can never be interpreted as markup. */

const ACCESS_KEY = "fastapizza.access";
const REFRESH_KEY = "fastapizza.refresh";
const SVG_NS = "http://www.w3.org/2000/svg";

/* ---- Session storage ---------------------------------------------------- */
export const session = {
  get access() { return localStorage.getItem(ACCESS_KEY); },
  get refresh() { return localStorage.getItem(REFRESH_KEY); },
  get active() { return Boolean(this.refresh || this.access); },
  save({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    currentUser = null;
  },
};
let currentUser = null;

/* ---- API client --------------------------------------------------------- */
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

function describe(detail, fallback) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d) => {
      const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
      const msg = String(d.msg || "").replace(/^Value error, /, "");
      return field && field !== "body" ? `${labelFor(field)}: ${msg}` : msg;
    }).join(" ");
  }
  return fallback;
}
const labelFor = (f) => ({ pizza_id: "Pizza", pizza_size: "Size", quantity: "Quantity", price: "Price", name: "Name", username: "Username", email: "Email", password: "Password", message: "Message", description: "Description" }[f] || String(f));

let refreshing = null;
async function refreshAccess() {
  if (!session.refresh) return false;
  refreshing ||= fetch("/auth/refresh", { method: "POST", headers: { Authorization: `Bearer ${session.refresh}` } })
    .then(async (res) => {
      if (!res.ok) return false;
      session.save(await res.json());
      return true;
    })
    .catch(() => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

export async function api(path, { method = "GET", json, form, auth = true, signal } = {}) {
  const build = () => {
    const headers = {};
    let body;
    if (json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(json); }
    if (form) body = form; // the browser sets the multipart boundary
    if (auth && session.access) headers.Authorization = `Bearer ${session.access}`;
    return { method, headers, body, signal };
  };
  let res;
  try {
    res = await fetch(path, build());
    if (res.status === 401 && auth && await refreshAccess()) res = await fetch(path, build());
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) {
    if (res.status === 401 && auth) { session.clear(); }
    throw new ApiError(describe(data?.detail, `Something went wrong (${res.status}).`), res.status);
  }
  return data;
}

/* ---- DOM helpers -------------------------------------------------------- */
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key in node && !["list", "form", "for"].includes(key)) node[key] = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function svgUse(cls, href, extra = {}) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", cls);
  svg.setAttribute("aria-hidden", "true");
  for (const [k, v] of Object.entries(extra)) svg.setAttribute(k, v);
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", href);
  svg.append(use);
  return svg;
}
export const icon = (name) => svgUse("icon", `#i-${name}`);
export const glyph = (name) => svgUse("glyph", `#g-${name}`);

export const money = (n) => "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);
export const formatDate = (iso) => new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(iso));
export const plural = (n, one, many = one + "s") => `${n} ${n === 1 ? one : many}`;
export function debounce(fn, ms = 250) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* ---- Pizza + order presentation ----------------------------------------- */
const ART = ["margherita", "pepperoni", "veggie"];
export const pizzaArt = (pizza) => pizza?.image_url || pizza?.pizza_image || `/static/img/pizza-${ART[(pizza?.id ?? pizza?.pizza_id ?? 0) % ART.length]}.svg`;

export const SIZE_LABEL = { SMALL: "Small", MEDIUM: "Medium", LARGE: "Large", "EXTRA-LARGE": "Extra large" };
export const STATUS = {
  PENDING: { label: "Pending", slices: 2, tone: "pending" },
  "IN-TRANSIT": { label: "In transit", slices: 5, tone: "transit" },
  DELIVERED: { label: "Delivered", slices: 8, tone: "done" },
};

/** A pizza cut in eight: the number of filled slices shows how far along an order is. */
export function meter(slices, tone, label) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", `meter meter--${tone}`);
  svg.setAttribute("viewBox", "-12 -12 24 24");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", label);
  for (let i = 0; i < 8; i++) {
    const a1 = ((-90 + i * 45 + 2.5) * Math.PI) / 180, a2 = ((-90 + (i + 1) * 45 - 2.5) * Math.PI) / 180, r = 10.5;
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", `M0 0 L${(r * Math.cos(a1)).toFixed(2)} ${(r * Math.sin(a1)).toFixed(2)} A${r} ${r} 0 0 1 ${(r * Math.cos(a2)).toFixed(2)} ${(r * Math.sin(a2)).toFixed(2)}Z`);
    path.setAttribute("class", `slice${i < slices ? " is-on" : ""}`);
    svg.append(path);
  }
  return svg;
}
export function statusBadge(code) {
  const s = STATUS[code] || STATUS.PENDING;
  return el("span", { class: `status status--${s.tone}` }, meter(s.slices, s.tone, `${s.slices} of 8 slices`), s.label);
}

export function initials(name = "") {
  return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "?";
}
export function avatar(user, size = "2.5rem") {
  const node = el("span", { class: "avatar" });
  node.style.setProperty("--size", size);
  if (user?.image) node.append(el("img", { src: user.image, alt: "", loading: "lazy" }));
  else node.append(initials(user?.name));
  return node;
}

export const loadingBlock = (text = "Loading…") =>
  el("div", { class: "loading-block", role: "status" }, el("span", { class: "loader" }), text);

export function skeletons(count, className) {
  return Array.from({ length: count }, () => el("div", { class: `skeleton ${className}`, "aria-hidden": "true" }));
}

export function emptyState({ title, text, action, image = "/static/img/empty-box.svg" }) {
  const actionEl = action && (action.href
    ? el("a", { class: "btn btn--primary", href: action.href }, action.label)
    : el("button", { class: "btn btn--primary", type: "button", onclick: action.onClick }, action.label));
  return el("div", { class: "empty" }, el("img", { src: image, alt: "", width: 320, height: 240 }), el("h3", {}, title), text && el("p", {}, text), actionEl);
}

export function errorState(message, retry) {
  return el("div", { class: "empty" },
    el("img", { src: "/static/img/empty-box.svg", alt: "", width: 320, height: 240 }),
    el("h3", {}, "That didn't load"), el("p", {}, message),
    retry && el("button", { class: "btn btn--outline", type: "button", onclick: retry }, icon("refresh"), "Try again"));
}

/* ---- Toasts and dialogs ------------------------------------------------- */
const TOAST_GLYPH = { success: "leaf", error: "chili", info: "tomato" };
export function toast(message, type = "success") {
  const host = $("#toasts");
  if (!host) return;
  const node = el("div", { class: "toast", role: type === "error" ? "alert" : "status" },
    glyph(TOAST_GLYPH[type] || "leaf"), el("span", { class: "toast__text" }, message),
    el("button", { type: "button", "aria-label": "Dismiss", onclick: () => remove() }, icon("close")));
  const remove = () => { node.classList.add("is-leaving"); setTimeout(() => node.remove(), 200); };
  host.append(node);
  setTimeout(remove, type === "error" ? 7000 : 4500);
}

/** Build a modal <dialog>; resolves when closed. `content` is a function receiving close(value). */
export function modal({ title, body, footer, onClose }) {
  const dialog = el("dialog", { class: "dialog", "aria-labelledby": "dialog-title" });
  const close = (value) => dialog.close(value);
  dialog.append(
    el("div", { class: "dialog__head" }, el("h2", { id: "dialog-title" }, title), el("button", { class: "icon-btn", type: "button", "aria-label": "Close", onclick: () => close("") }, icon("close"))),
    el("div", { class: "dialog__body" }, body),
    footer ? el("div", { class: "dialog__foot" }, footer(close)) : null,
  );
  dialog.addEventListener("close", () => { onClose?.(dialog.returnValue); dialog.remove(); });
  dialog.addEventListener("click", (e) => { if (e.target === dialog) close(""); }); // backdrop click
  document.body.append(dialog);
  dialog.showModal();
  return { dialog, close };
}

export function confirmDialog({ title, message, confirmLabel = "Confirm", danger = false }) {
  return new Promise((resolve) => {
    modal({
      title, body: el("p", {}, message),
      footer: (close) => [
        el("button", { class: "btn btn--outline", type: "button", onclick: () => close("no") }, "Keep it"),
        el("button", { class: `btn ${danger ? "btn--danger-solid" : "btn--primary"}`, type: "button", onclick: () => close("yes") }, confirmLabel),
      ],
      onClose: (value) => resolve(value === "yes"),
    });
  });
}

/* ---- Form helpers ------------------------------------------------------- */
export function setBusy(button, busy, label) {
  button.disabled = busy;
  button.classList.toggle("is-loading", busy);
  if (label !== undefined) { button.dataset.label ??= button.textContent; button.textContent = busy ? label : button.dataset.label; }
}
export function showFieldError(input, message) {
  clearFieldError(input);
  input.setAttribute("aria-invalid", "true");
  const id = `${input.id || input.name}-error`;
  const err = el("p", { class: "field__error", id }, icon("alert"), message);
  input.setAttribute("aria-describedby", id);
  (input.closest(".password-wrap") || input).insertAdjacentElement("afterend", err);
}
export function clearFieldError(input) {
  input.removeAttribute("aria-invalid");
  input.removeAttribute("aria-describedby");
  const wrap = input.closest(".password-wrap") || input;
  if (wrap.nextElementSibling?.classList.contains("field__error")) wrap.nextElementSibling.remove();
}
export function clearFormErrors(form) { $$("[aria-invalid]", form).forEach(clearFieldError); $$(".alert[data-form-alert]", form).forEach((a) => a.remove()); }
export function formAlert(form, message, type = "error") {
  $$(".alert[data-form-alert]", form).forEach((a) => a.remove());
  const node = el("div", { class: `alert alert--${type}`, role: type === "error" ? "alert" : "status", "data-form-alert": "" }, icon(type === "error" ? "alert" : "check"), message);
  form.prepend(node);
  return node;
}
export function wirePasswordToggles(root = document) {
  $$(".password-toggle", root).forEach((btn) => btn.addEventListener("click", () => {
    const input = btn.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    btn.replaceChildren(icon(show ? "eye-off" : "eye"));
  }));
}

/* ---- Auth + shell ------------------------------------------------------- */
export async function loadUser(force = false) {
  if (currentUser && !force) return currentUser;
  currentUser = await api("/auth/user");
  return currentUser;
}

export function safeNext(fallback) {
  const next = new URLSearchParams(location.search).get("next");
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/\\") ? next : fallback;
}
export const homeFor = (user) => (user.is_staff ? "/admin/dashboard" : "/user/dashboard");

export function goToLogin() {
  const next = encodeURIComponent(location.pathname + location.search);
  location.replace(`/auth/login?next=${next}`);
}

export async function logout() {
  session.clear();
  location.assign("/auth/login");
}

function wireChrome() {
  const navToggle = $("[data-nav-toggle]");
  const nav = $("#site-nav");
  navToggle?.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(open));
  });
  const sidebar = $("#sidebar");
  const sideToggle = $("[data-sidebar-toggle]");
  const setSidebar = (open) => { sidebar.classList.toggle("is-open", open); sideToggle?.setAttribute("aria-expanded", String(open)); };
  sideToggle?.addEventListener("click", () => setSidebar(!sidebar.classList.contains("is-open")));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sidebar?.classList.contains("is-open")) { setSidebar(false); sideToggle?.focus(); } });
  document.addEventListener("click", (e) => { if (sidebar?.classList.contains("is-open") && !sidebar.contains(e.target) && !sideToggle.contains(e.target)) setSidebar(false); });
  $$("[data-logout]").forEach((b) => b.addEventListener("click", logout));
}

function renderUserMenu(host, user) {
  const trigger = el("button", { class: "dropdown__trigger", type: "button", "aria-haspopup": "true", "aria-expanded": "false" },
    avatar(user, "2rem"), el("span", {}, user.name.split(" ")[0]), icon("chevron-down"));
  const panel = el("div", { class: "dropdown__panel", hidden: true },
    el("div", { class: "dropdown__who" }, el("strong", {}, user.name), el("small", {}, `@${user.username}`)),
    el("a", { href: "/user/profile" }, icon("user"), "Your profile"),
    el("a", { href: "/user/order-data" }, icon("receipt"), "My orders"),
    user.is_staff ? el("a", { href: "/admin/dashboard" }, icon("shield"), "Staff dashboard") : null,
    el("button", { type: "button", onclick: logout }, icon("logout"), "Log out"));
  const setOpen = (open) => { panel.hidden = !open; trigger.setAttribute("aria-expanded", String(open)); };
  trigger.addEventListener("click", () => setOpen(panel.hidden));
  document.addEventListener("click", (e) => { if (!host.contains(e.target)) setOpen(false); });
  host.addEventListener("keydown", (e) => { if (e.key === "Escape") { setOpen(false); trigger.focus(); } });
  host.replaceChildren(trigger, panel);
}

/**
 * Page start-up. guard: "public" | "guest" | "user" | "staff".
 * Returns the signed-in user (or null on public pages) once the page may render.
 */
export async function boot(guard = "public") {
  wireChrome();
  wirePasswordToggles();
  let user = null;

  if (guard === "public") {
    const member = session.active;
    $$("[data-guest-only]").forEach((n) => (n.hidden = member));
    $$("[data-member-only]").forEach((n) => (n.hidden = !member));
    return null;
  }
  if (guard === "guest") {
    if (session.active) {
      try { user = await loadUser(); location.replace(safeNext(homeFor(user))); return new Promise(() => {}); } catch { session.clear(); }
    }
    return null;
  }
  if (!session.active) { goToLogin(); return new Promise(() => {}); }
  try { user = await loadUser(); } catch (err) {
    if (err.status === 401 || err.status === 403) { session.clear(); goToLogin(); return new Promise(() => {}); }
    document.body.classList.remove("is-booting");
    toast(err.message, "error");
    throw err;
  }
  if (guard === "staff" && !user.is_staff) { location.replace("/user/dashboard"); return new Promise(() => {}); }

  const menuHost = $("[data-user-menu]");
  if (menuHost) renderUserMenu(menuHost, user);
  const who = $("[data-sidebar-who]");
  if (who) who.replaceChildren(avatar(user, "2.25rem"), el("div", {}, el("strong", {}, user.name), el("small", {}, `@${user.username}`)));
  document.body.classList.remove("is-booting");
  return user;
}
