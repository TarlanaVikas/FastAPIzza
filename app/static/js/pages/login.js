import { boot, api, session, $, setBusy, showFieldError, clearFormErrors, formAlert, safeNext, homeFor } from "../core.js";

await boot("guest");
const form = $("#login-form");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFormErrors(form);
  const { username, password } = form.elements;
  let invalid = false;
  if (!username.value.trim()) { showFieldError(username, "Enter your username."); invalid = true; }
  if (!password.value) { showFieldError(password, "Enter your password."); invalid = true; }
  if (invalid) return form.querySelector("[aria-invalid]").focus();

  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Logging in…");
  try {
    const tokens = await api("/auth/login", { method: "POST", auth: false, json: { username: username.value.trim(), password: password.value } });
    session.save(tokens);
    location.assign(safeNext(homeFor(tokens)));
  } catch (err) {
    formAlert(form, err.message);
    setBusy(button, false, "Log in");
  }
});
