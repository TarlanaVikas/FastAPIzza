import { boot, api, el, $, icon, money, pizzaArt, SIZE_LABEL, setBusy, toast, formAlert, errorState, emptyState } from "../core.js";
import { pizzaCard } from "../menu.js";

await boot("user");
const root = $("#order-root");
const pizzaId = Number(new URLSearchParams(location.search).get("pizza"));

async function start() {
  if (!Number.isInteger(pizzaId) || pizzaId < 1) {
    return root.replaceChildren(emptyState({ title: "Pick a pizza first", text: "Choose one from the menu and we'll bring you back here.", action: { label: "Go to the menu", href: "/user/dashboard" } }));
  }
  try {
    const [pizza, sizes, all] = await Promise.all([api(`/pizzas/${pizzaId}`, { auth: false }), api("/pizzas/sizes", { auth: false }), api("/pizzas/", { auth: false })]);
    render(pizza, sizes, all.filter((p) => p.id !== pizza.id).slice(0, 3));
  } catch (err) {
    root.replaceChildren(err.status === 404
      ? emptyState({ title: "That pizza isn't on the menu", text: "It may have been removed.", action: { label: "Back to the menu", href: "/user/dashboard" } })
      : errorState(err.message, start));
  }
}

function render(pizza, sizes, others) {
  document.title = `Order ${pizza.name} · FastAPIzza`;
  let size = sizes[0].code, qty = 1;
  const unit = () => Math.round(pizza.price * sizes.find((s) => s.code === size).multiplier * 100) / 100;

  const summary = el("div", { class: "receipt", "aria-live": "polite" });
  const totalEl = el("span", { class: "price receipt__total" });
  const qtyInput = el("input", { id: "qty", type: "number", min: 1, max: 10, value: 1, inputMode: "numeric", "aria-label": "Quantity" });
  const minus = el("button", { type: "button", "aria-label": "One fewer" }, icon("minus"));
  const plus = el("button", { type: "button", "aria-label": "One more" }, icon("plus"));
  const submit = el("button", { class: "btn btn--primary btn--block", type: "submit" }, "Place order");

  const refresh = () => {
    qty = Math.min(10, Math.max(1, Number(qtyInput.value) || 1));
    qtyInput.value = qty;
    minus.disabled = qty <= 1; plus.disabled = qty >= 10;
    summary.replaceChildren(
      el("div", { class: "leader" }, el("span", {}, `${qty} × ${SIZE_LABEL[size]} ${pizza.name}`), el("span", { class: "price" }, money(unit() * qty))));
    totalEl.textContent = money(unit() * qty);
  };
  minus.addEventListener("click", () => { qtyInput.value = qty - 1; refresh(); });
  plus.addEventListener("click", () => { qtyInput.value = qty + 1; refresh(); });
  qtyInput.addEventListener("input", refresh);
  qtyInput.addEventListener("blur", refresh);

  const sizeChoices = sizes.map((s, i) => el("label", { class: "choice" },
    el("input", { type: "radio", name: "size", value: s.code, checked: i === 0, onchange: () => { size = s.code; refresh(); } }),
    el("span", { class: "choice__body" }, el("strong", {}, s.label), el("span", { class: "price" }, money(Math.round(pizza.price * s.multiplier * 100) / 100)))));

  const form = el("form", { class: "form card order-form", novalidate: true },
    el("h2", { class: "card__title" }, "Your order"),
    el("fieldset", { class: "choice-grid" }, el("legend", { class: "field__label order-form__legend" }, "Size"), ...sizeChoices),
    el("div", { class: "field" }, el("label", { for: "qty" }, "Quantity"), el("div", {}, el("div", { class: "stepper" }, minus, qtyInput, plus)), el("p", { class: "field__hint" }, "Up to 10 per order.")),
    el("div", { class: "receipt-wrap" }, summary, el("div", { class: "leader receipt__sum" }, el("strong", {}, "Total"), totalEl)),
    submit);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setBusy(submit, true, "Placing order…");
    try {
      await api("/orders/", { method: "POST", json: { pizza_id: pizza.id, pizza_size: size, quantity: qty } });
      toast("Order placed. We're on it.");
      location.assign("/user/order-data");
    } catch (err) {
      setBusy(submit, false, "Place order");
      if (err.status === 404) { toast(err.message, "error"); return start(); }
      formAlert(form, err.message);
    }
  });

  root.replaceChildren(
    el("a", { class: "back-link", href: "/user/dashboard" }, "← Back to the menu"),
    el("div", { class: "order-layout" },
      el("section", { class: "order-hero", "aria-label": pizza.name },
        el("div", { class: "order-hero__plate" }, el("img", { src: pizzaArt(pizza), alt: "", width: 480, height: 480 })),
        el("h1", {}, pizza.name),
        el("p", { class: "muted order-hero__desc" }, pizza.description || "Made fresh to order."),
        el("p", {}, el("small", { class: "muted" }, "from "), el("span", { class: "price order-hero__price" }, money(pizza.price)))),
      form),
    others.length ? el("section", { class: "more", "aria-labelledby": "more-title" }, el("h2", { id: "more-title" }, "Also on the menu"), el("div", { class: "menu-grid" }, others.map(pizzaCard))) : null);
  refresh();
}
start();
