import { boot, api, el, $, icon, money, pizzaArt, formatDate, statusBadge, SIZE_LABEL, STATUS, loadingBlock, emptyState, errorState, toast, confirmDialog, modal, setBusy, formAlert } from "../core.js";

await boot("user");
const list = $("#order-list");
const filters = $("#order-filters");
let orders = [];
let filter = "ALL";
let sizes = [];

function renderFilters() {
  const counts = { ALL: orders.length };
  for (const o of orders) counts[o.order_status] = (counts[o.order_status] || 0) + 1;
  const items = [["ALL", "All"], ...Object.entries(STATUS).map(([k, v]) => [k, v.label])];
  filters.replaceChildren(...items.map(([key, label]) =>
    el("button", { class: "chip", type: "button", "aria-pressed": String(filter === key), onclick: () => { filter = key; renderFilters(); renderList(); } },
      label, el("span", { class: "chip__count" }, counts[key] || 0))));
  filters.hidden = orders.length === 0;
}

function row(order) {
  const pending = order.order_status === "PENDING";
  return el("article", { class: "order-row" },
    el("img", { class: "thumb thumb--lg", src: pizzaArt({ image_url: order.pizza_image, id: order.pizza_id ?? order.id }), alt: "", loading: "lazy", width: 64, height: 64 }),
    el("div", { class: "order-row__main" },
      el("h3", {}, order.pizza_name),
      el("p", { class: "muted" }, `${SIZE_LABEL[order.pizza_size] ?? order.pizza_size} × ${order.quantity} · ${formatDate(order.created_at)} · Order #${order.id}`)),
    el("div", { class: "order-row__side" },
      el("span", { class: "price order-row__total" }, money(order.total)),
      statusBadge(order.order_status)),
    pending ? el("div", { class: "order-row__actions" },
      el("button", { class: "btn btn--outline btn--sm", type: "button", onclick: () => edit(order) }, icon("edit"), "Edit"),
      el("button", { class: "btn btn--danger btn--sm", type: "button", onclick: () => cancel(order) }, icon("trash"), "Cancel")) : null);
}

function renderList() {
  const shown = filter === "ALL" ? orders : orders.filter((o) => o.order_status === filter);
  if (!orders.length) {
    return list.replaceChildren(emptyState({ title: "No orders yet", text: "When you order a pizza it will show up here, with its progress.", action: { label: "Browse the menu", href: "/user/dashboard" } }));
  }
  if (!shown.length) return list.replaceChildren(emptyState({ title: `Nothing ${STATUS[filter].label.toLowerCase()}`, text: "No orders in this state right now." }));
  list.replaceChildren(...shown.map(row));
}

async function load() {
  list.replaceChildren(loadingBlock("Loading your orders…"));
  try {
    [orders, sizes] = await Promise.all([api("/orders/mine"), api("/pizzas/sizes", { auth: false })]);
    renderFilters(); renderList();
  } catch (err) { list.replaceChildren(errorState(err.message, load)); }
}

async function cancel(order) {
  const ok = await confirmDialog({ title: "Cancel this order?", message: `${order.pizza_name} × ${order.quantity} (${money(order.total)}) will be removed.`, confirmLabel: "Cancel order", danger: true });
  if (!ok) return;
  try { await api(`/orders/${order.id}`, { method: "DELETE" }); toast("Order cancelled."); await load(); }
  catch (err) { toast(err.message, "error"); await load(); }
}

function edit(order) {
  let size = order.pizza_size, qty = order.quantity;
  const form = el("form", { class: "form", novalidate: true });
  const total = el("strong", { class: "price" });
  const select = el("select", { class: "select", id: "edit-size" }, sizes.map((s) => el("option", { value: s.code, selected: s.code === size }, s.label)));
  const qtyInput = el("input", { class: "input", id: "edit-qty", type: "number", min: 1, max: 10, value: qty, inputMode: "numeric" });
  const unitBase = order.unit_price / (sizes.find((s) => s.code === order.pizza_size)?.multiplier || 1);
  const update = () => {
    size = select.value; qty = Math.min(10, Math.max(1, Number(qtyInput.value) || 1));
    total.textContent = money(Math.round(unitBase * sizes.find((s) => s.code === size).multiplier * 100) / 100 * qty);
  };
  select.addEventListener("change", update); qtyInput.addEventListener("input", update); update();
  form.append(
    el("div", { class: "field" }, el("label", { for: "edit-size" }, "Size"), select),
    el("div", { class: "field" }, el("label", { for: "edit-qty" }, "Quantity"), qtyInput),
    el("div", { class: "leader" }, el("span", {}, "New total"), total));
  const { close } = modal({
    title: `Edit ${order.pizza_name}`, body: form,
    footer: (closeDialog) => {
      const save = el("button", { class: "btn btn--primary", type: "button", onclick: async () => {
        update(); setBusy(save, true, "Saving…");
        try { await api(`/orders/${order.id}`, { method: "PUT", json: { pizza_size: size, quantity: qty } }); closeDialog("saved"); toast("Order updated."); await load(); }
        catch (err) { setBusy(save, false, "Save changes"); formAlert(form, err.message); if (err.status === 409) { closeDialog("x"); await load(); } }
      } }, "Save changes");
      return [el("button", { class: "btn btn--outline", type: "button", onclick: () => closeDialog("") }, "Close"), save];
    },
  });
  form.addEventListener("submit", (e) => e.preventDefault());
}
load();
