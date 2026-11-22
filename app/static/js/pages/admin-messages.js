import { boot, api, el, $, icon, formatDate, loadingBlock, emptyState, errorState, toast, confirmDialog } from "../core.js";

await boot("staff");
const host = $("#message-list");

async function remove(m) {
  if (!await confirmDialog({ title: "Delete this message?", message: `The note from ${m.name} will be removed for good.`, confirmLabel: "Delete message", danger: true })) return;
  try { await api(`/contact/${m.id}`, { method: "DELETE" }); toast("Message deleted."); load(); } catch (err) { toast(err.message, "error"); }
}

async function load() {
  host.replaceChildren(loadingBlock("Loading messages…"));
  try {
    const messages = await api("/contact/");
    if (!messages.length) return host.replaceChildren(emptyState({ title: "Inbox is empty", text: "Messages from the contact form show up here." }));
    host.replaceChildren(el("div", { class: "message-list" }, messages.map((m) => el("article", { class: "card message" },
      el("div", { class: "message__head" },
        el("div", {}, el("strong", {}, m.name), el("a", { class: "message__mail", href: `mailto:${m.email}` }, m.email)),
        el("time", { class: "muted", datetime: m.created_at }, formatDate(m.created_at))),
      el("p", { class: "message__body" }, m.message),
      el("div", {}, el("button", { class: "btn btn--danger btn--sm", type: "button", onclick: () => remove(m) }, icon("trash"), "Delete"))))));
  } catch (err) { host.replaceChildren(errorState(err.message, load)); }
}
load();
