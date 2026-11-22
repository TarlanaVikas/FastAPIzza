import { api, el, setBusy, showFieldError, clearFormErrors, formAlert } from "./core.js";

/** Wire the contact form; on success swap the card content for a confirmation. */
export function wireContactForm(form, prefill = {}) {
  if (prefill.name) form.elements.name.value = prefill.name;
  if (prefill.email) form.elements.email.value = prefill.email;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormErrors(form);
    const { name, email, message, website } = form.elements;
    let invalid = false;
    if (!name.value.trim()) { showFieldError(name, "Enter your name."); invalid = true; }
    if (!email.validity.valid || !email.value.trim()) { showFieldError(email, "Enter a valid email address."); invalid = true; }
    if (message.value.trim().length < 5) { showFieldError(message, "Write a few words so we can help."); invalid = true; }
    if (invalid) return form.querySelector("[aria-invalid]")?.focus();
    const button = form.querySelector("button[type=submit]");
    setBusy(button, true, "Sending…");
    try {
      await api("/contact/", { method: "POST", auth: false, json: { name: name.value, email: email.value, message: message.value, website: website.value } });
      const card = form.closest(".card");
      card.replaceChildren(el("div", { class: "empty", role: "status" },
        el("h3", {}, "Message sent"), el("p", {}, "Thanks. The team will read it soon."),
        el("button", { class: "btn btn--outline", type: "button", onclick: () => location.reload() }, "Send another")));
    } catch (err) {
      formAlert(form, err.message);
      setBusy(button, false, "Send message");
    }
  });
}
