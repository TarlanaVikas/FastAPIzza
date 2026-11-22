import { boot, api, el, $, debounce, errorState, statusBadge, SIZE_LABEL, money, formatDate, icon } from "../core.js";
import { renderMenu, menuSkeleton } from "../menu.js";

const user = await boot("user");

const hour = new Date().getHours();
const part = hour < 5 ? "Late night" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
$("#greeting").textContent = `${part}, ${user.name.split(" ")[0]}.`;

// The most recent order that's still on its way.
api("/orders/mine").then((orders) => {
  const active = orders.find((o) => o.order_status !== "DELIVERED");
  if (!active) return;
  const host = $("#latest-order");
  host.hidden = false;
  host.replaceChildren(
    el("div", { class: "latest__text" }, el("strong", {}, "Your latest order"),
      el("span", {}, `${SIZE_LABEL[active.pizza_size] ?? active.pizza_size} ${active.pizza_name} × ${active.quantity} · ${money(active.total)} · ${formatDate(active.created_at)}`)),
    statusBadge(active.order_status),
    el("a", { class: "btn btn--outline btn--sm", href: "/user/order-data" }, "View orders", icon("arrow-right")));
}).catch(() => {});

const host = $("#menu-list");
const input = $("#q");
let controller;

async function load() {
  const term = input.value.trim();
  controller?.abort();
  controller = new AbortController();
  menuSkeleton(host);
  try {
    const pizzas = await api(`/pizzas/${term ? `?search=${encodeURIComponent(term)}` : ""}`, { auth: false, signal: controller.signal });
    renderMenu(host, pizzas, term
      ? { emptyTitle: `No pizza matches “${term}”`, emptyText: "Check the spelling or try a shorter name.", emptyAction: { label: "Clear search", onClick: () => { input.value = ""; load(); input.focus(); } } }
      : {});
  } catch (err) {
    if (err.name !== "AbortError") host.replaceChildren(errorState(err.message, load));
  }
}
input.addEventListener("input", debounce(load, 250));
$("#menu-search").addEventListener("submit", (e) => { e.preventDefault(); load(); });
load();
