import { boot, api, el, $, icon, money, pizzaArt, loadingBlock, emptyState, errorState, toast, confirmDialog, modal, setBusy, formAlert, showFieldError, clearFormErrors } from "../core.js";

await boot("staff");
const host = $("#pizza-table");
let pizzas = [];

async function loadStats() {
  const settle = (p) => p.then((v) => v.length, () => null);
  const [menu, pending, customers, messages] = await Promise.all([
    settle(api("/pizzas/", { auth: false })), settle(api("/orders/?status=PENDING")), settle(api("/auth/users")), settle(api("/contact/"))]);
  const stat = (value, label, href) => el("a", { class: "stat stat--link", href }, el("span", { class: "stat__value" }, value ?? "–"), el("span", { class: "stat__label" }, label));
  $("#admin-stats").replaceChildren(
    stat(menu, "Pizzas on the menu", "/admin/dashboard"), stat(pending, "Pending orders", "/admin/orders"),
    stat(customers, "Accounts", "/admin/users"), stat(messages, "Messages", "/admin/messages"));
}

function render() {
  if (!pizzas.length) {
    return host.replaceChildren(emptyState({ title: "The menu is empty", text: "Add the first pizza so customers have something to order.", action: { label: "Add pizza", onClick: () => openForm() } }));
  }
  const rows = pizzas.map((p) => el("tr", {},
    el("td", { class: "cell-lead" }, el("div", { class: "cell-main" },
      el("img", { class: "thumb", src: pizzaArt(p), alt: "", loading: "lazy", width: 48, height: 48 }),
      el("div", {}, el("strong", {}, p.name), el("small", { class: "clamp" }, p.description || "No description")))),
    el("td", { "data-label": "Price (small)", class: "num" }, el("span", { class: "price" }, money(p.price))),
    el("td", { class: "actions-cell" }, el("div", { class: "actions" },
      el("button", { class: "btn btn--outline btn--sm", type: "button", onclick: () => openForm(p), "aria-label": `Edit ${p.name}` }, icon("edit"), "Edit"),
      el("button", { class: "btn btn--danger btn--sm", type: "button", onclick: () => remove(p), "aria-label": `Delete ${p.name}` }, icon("trash"), "Delete")))));
  host.replaceChildren(el("div", { class: "table-wrap" }, el("table", { class: "table" },
    el("thead", {}, el("tr", {}, el("th", {}, "Pizza"), el("th", { class: "num" }, "Price (small)"), el("th", {}, el("span", { class: "sr-only" }, "Actions")))),
    el("tbody", {}, rows))));
}

async function load() {
  host.replaceChildren(loadingBlock("Loading the menu…"));
  try { pizzas = await api("/pizzas/", { auth: false }); render(); }
  catch (err) { host.replaceChildren(errorState(err.message, load)); }
}

async function remove(p) {
  const ok = await confirmDialog({ title: `Delete ${p.name}?`, message: "It disappears from the menu. Past orders keep its name and price.", confirmLabel: "Delete pizza", danger: true });
  if (!ok) return;
  try { await api(`/pizzas/${p.id}`, { method: "DELETE" }); toast(`${p.name} removed.`); await Promise.all([load(), loadStats()]); }
  catch (err) { toast(err.message, "error"); }
}

function openForm(pizza) {
  const editing = Boolean(pizza);
  const form = el("form", { class: "form", novalidate: true },
    el("div", { class: "field" }, el("label", { for: "f-name" }, "Name"), el("input", { class: "input", id: "f-name", name: "name", required: true, maxLength: 200, value: pizza?.name ?? "" })),
    el("div", { class: "field" }, el("label", { for: "f-price" }, "Price for a small (₹)"), el("input", { class: "input", id: "f-price", name: "price", type: "number", min: "1", step: "0.01", inputMode: "decimal", required: true, value: pizza?.price ?? "" }),
      el("p", { class: "field__hint" }, "Medium, large and extra large are priced from this automatically.")),
    el("div", { class: "field" }, el("label", { for: "f-desc" }, "Description"), el("textarea", { class: "textarea textarea--short", id: "f-desc", name: "description", maxLength: 500 }, pizza?.description ?? "")),
    el("div", { class: "field" }, el("label", { for: "f-image" }, editing ? "Replace photo" : "Photo", el("span", { class: "muted" }, " (optional)")),
      el("input", { class: "file-input", id: "f-image", name: "image", type: "file", accept: "image/png,image/jpeg,image/webp,image/gif" }),
      el("p", { class: "field__hint" }, "Without one, the menu shows a drawn pizza.")));
  const preview = el("img", { class: "thumb thumb--lg", src: pizzaArt(pizza ?? { id: pizzas.length }), alt: "Current picture", width: 64, height: 64 });
  form.querySelector("#f-image").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) preview.src = URL.createObjectURL(f); });
  form.prepend(el("div", { class: "preview" }, preview));
  const { dialog } = modal({
    title: editing ? `Edit ${pizza.name}` : "Add a pizza", body: form,
    footer: (close) => {
      const save = el("button", { class: "btn btn--primary", type: "submit", form: "pizza-form" }, editing ? "Save changes" : "Add pizza");
      return [el("button", { class: "btn btn--outline", type: "button", onclick: () => close("") }, "Cancel"), save];
    },
  });
  form.id = "pizza-form";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearFormErrors(form);
    const { name, price, description, image } = form.elements;
    const priceNumber = Number(price.value);
    const problems = [];
    if (!name.value.trim()) problems.push([name, "Enter a pizza name."]);
    if (!(priceNumber > 0)) problems.push([price, "Enter a price above zero."]);
    if (image.files[0] && image.files[0].size > 5 * 1024 * 1024) problems.push([image, "Choose an image under 5 MB."]);
    if (problems.length) { problems.forEach(([i, m]) => showFieldError(i, m)); return problems[0][0].focus(); }
    const body = new FormData();
    body.set("name", name.value.trim()); body.set("price", String(priceNumber)); body.set("description", description.value.trim());
    if (image.files[0]) body.set("image", image.files[0]);
    const save = dialog.querySelector("button[type=submit]");
    setBusy(save, true, "Saving…");
    try {
      await api(editing ? `/pizzas/${pizza.id}` : "/pizzas/", { method: editing ? "PUT" : "POST", form: body });
      dialog.close("saved");
      toast(editing ? "Pizza updated." : "Pizza added to the menu.");
      await Promise.all([load(), loadStats()]);
    } catch (err) { setBusy(save, false, editing ? "Save changes" : "Add pizza"); formAlert(form, err.message); }
  });
}

$("#add-pizza").addEventListener("click", () => openForm());
load();
loadStats();
