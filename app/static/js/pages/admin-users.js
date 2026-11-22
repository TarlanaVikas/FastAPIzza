import { boot, api, el, $, avatar, formatDate, loadingBlock, emptyState, errorState } from "../core.js";

await boot("staff");
const host = $("#user-table");

async function load() {
  host.replaceChildren(loadingBlock("Loading customers…"));
  try {
    const users = await api("/auth/users");
    if (!users.length) return host.replaceChildren(emptyState({ title: "No accounts yet", text: "People who sign up will appear here." }));
    const rows = users.map((u) => el("tr", {},
      el("td", { class: "cell-lead" }, el("div", { class: "cell-main" }, avatar(u, "2.5rem"), el("div", {}, el("strong", {}, u.name), el("small", {}, `@${u.username}`)))),
      el("td", { "data-label": "Email" }, el("a", { href: `mailto:${u.email}` }, u.email)),
      el("td", { "data-label": "Role" }, el("span", { class: `badge ${u.is_staff ? "badge--staff" : ""}` }, u.is_staff ? "Staff" : "Customer")),
      el("td", { "data-label": "Account" }, el("span", { class: `badge ${u.is_active ? "badge--ok" : "badge--off"}` }, u.is_active ? "Active" : "Disabled")),
      el("td", { "data-label": "Orders", class: "num" }, u.orders_count),
      el("td", { "data-label": "Joined" }, u.created_at ? formatDate(u.created_at) : "–")));
    host.replaceChildren(el("div", { class: "table-wrap" }, el("table", { class: "table" },
      el("thead", {}, el("tr", {}, ["Name", "Email", "Role", "Account", "Orders", "Joined"].map((h, i) => el("th", { class: i === 4 ? "num" : "" }, h)))),
      el("tbody", {}, rows))));
  } catch (err) { host.replaceChildren(errorState(err.message, load)); }
}
load();
