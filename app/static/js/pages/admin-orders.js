import { boot, api, el, $, money, pizzaArt, formatDate, meter, SIZE_LABEL, STATUS, loadingBlock, emptyState, errorState, toast } from "../core.js";

await boot("staff");
const host = $("#order-table");
const filters = $("#order-filters");
let orders = [];
let filter = "ALL";

function renderFilters() {
  const counts = { ALL: orders.length };
  for (const o of orders) counts[o.order_status] = (counts[o.order_status] || 0) + 1;
  filters.replaceChildren(...[["ALL", "All"], ...Object.entries(STATUS).map(([k, v]) => [k, v.label])].map(([key, label]) =>
    el("button", { class: "chip", type: "button", "aria-pressed": String(filter === key), onclick: () => { filter = key; renderFilters(); render(); } },
      label, el("span", { class: "chip__count" }, counts[key] || 0))));
}

function statusSelect(order) {
  const select = el("select", { class: "select select--inline", "aria-label": `Status of order ${order.id}` },
    Object.entries(STATUS).map(([code, s]) => el("option", { value: code, selected: code === order.order_status }, s.label)));
  select.addEventListener("change", async () => {
    const previous = order.order_status;
    select.disabled = true;
    try {
      const updated = await api(`/orders/${order.id}/status`, { method: "PATCH", json: { order_status: select.value } });
      Object.assign(order, updated);
      toast(`Order #${order.id} is now ${STATUS[order.order_status].label.toLowerCase()}.`);
      renderFilters(); render();
    } catch (err) { select.value = previous; select.disabled = false; toast(err.message, "error"); }
  });
  return select;
}

function render() {
  const shown = filter === "ALL" ? orders : orders.filter((o) => o.order_status === filter);
  if (!orders.length) return host.replaceChildren(emptyState({ title: "No orders yet", text: "Orders appear here as soon as customers place them." }));
  if (!shown.length) return host.replaceChildren(emptyState({ title: "Nothing here", text: "No orders match this filter." }));
  const rows = shown.map((o) => el("tr", {},
    el("td", { class: "cell-lead" }, el("div", { class: "cell-main" },
      el("img", { class: "thumb", src: pizzaArt({ image_url: o.pizza_image, id: o.pizza_id ?? o.id }), alt: "", loading: "lazy", width: 48, height: 48 }),
      el("div", {}, el("strong", {}, o.pizza_name), el("small", {}, `${SIZE_LABEL[o.pizza_size] ?? o.pizza_size} × ${o.quantity} · #${o.id}`)))),
    el("td", { "data-label": "Customer" }, el("span", {}, o.customer.name, el("small", { class: "muted block" }, `@${o.customer.username}`))),
    el("td", { "data-label": "Placed" }, formatDate(o.created_at)),
    el("td", { "data-label": "Total", class: "num" }, el("span", { class: "price" }, money(o.total))),
    el("td", { "data-label": "Status" }, el("div", { class: "status-cell" }, meter(STATUS[o.order_status].slices, STATUS[o.order_status].tone, `${STATUS[o.order_status].slices} of 8 slices`), statusSelect(o)))));
  host.replaceChildren(el("div", { class: "table-wrap" }, el("table", { class: "table" },
    el("thead", {}, el("tr", {}, ["Order", "Customer", "Placed", "Total", "Status"].map((h, i) => el("th", { class: i === 3 ? "num" : "" }, h)))),
    el("tbody", {}, rows))));
}

async function load(manual = false) {
  if (!orders.length || !manual) host.replaceChildren(loadingBlock("Loading orders…"));
  try { orders = await api("/orders/"); renderFilters(); render(); if (manual) toast("Orders refreshed.", "info"); }
  catch (err) { host.replaceChildren(errorState(err.message, () => load())); }
}
$("#refresh").addEventListener("click", () => load(true));
load();
