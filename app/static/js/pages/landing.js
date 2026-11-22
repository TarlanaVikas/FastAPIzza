import { boot, api, $, $$, meter, errorState } from "../core.js";
import { renderMenu, menuSkeleton } from "../menu.js";
import { wireContactForm } from "../contact-form.js";

await boot("public");

$$(".steps__meter").forEach((node) => {
  const n = Number(node.dataset.slices);
  node.replaceChildren(meter(n, n === 8 ? "done" : n === 5 ? "transit" : "pending", `${n} of 8 slices`));
});

const host = $("#menu-list");
async function loadMenu() {
  menuSkeleton(host);
  try { renderMenu(host, await api("/pizzas/", { auth: false }), { limit: 6 }); }
  catch (err) { host.replaceChildren(errorState(err.message, loadMenu)); }
}
loadMenu();
wireContactForm($("#contact-form"));
