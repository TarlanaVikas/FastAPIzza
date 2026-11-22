/* Menu card + grid rendering shared by the landing page and the customer dashboard. */
import { el, money, pizzaArt, emptyState, skeletons } from "./core.js";

export function pizzaCard(pizza) {
  const href = `/user/place-order?pizza=${pizza.id}`;
  return el("article", { class: "pizza-card" },
    el("a", { class: "pizza-card__plate", href, tabindex: -1, "aria-hidden": "true" },
      el("img", { class: "pizza-card__img", src: pizzaArt(pizza), alt: "", loading: "lazy", width: 400, height: 400 })),
    el("div", { class: "pizza-card__body" },
      el("h3", {}, pizza.name),
      el("p", { class: "pizza-card__desc" }, pizza.description || "Made fresh to order."),
      el("div", { class: "pizza-card__foot" },
        el("p", { class: "pizza-card__price" }, el("small", {}, "from "), el("span", { class: "price" }, money(pizza.price))),
        el("a", { class: "btn btn--primary btn--sm", href, "aria-label": `Order ${pizza.name}` }, "Order"))));
}

export const menuSkeleton = (host, n = 3) => host.replaceChildren(...skeletons(n, "pizza-card pizza-card--skeleton"));

export function renderMenu(host, pizzas, { limit, emptyTitle, emptyText, emptyAction } = {}) {
  if (!pizzas.length) {
    host.replaceChildren(emptyState({ title: emptyTitle || "The menu is being prepared", text: emptyText || "No pizzas are listed yet. Check back soon.", action: emptyAction }));
    return;
  }
  host.replaceChildren(...pizzas.slice(0, limit ?? pizzas.length).map(pizzaCard));
}
