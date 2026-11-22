import { boot, api, session, $, setBusy, showFieldError, clearFormErrors, formAlert } from "../core.js";

await boot("guest");
const form = $("#register-form");
const USERNAME = /^[A-Za-z0-9_.-]{3,25}$/;
const MAX_IMAGE = 5 * 1024 * 1024;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFormErrors(form);
  const { name, username, email, password, image } = form.elements;
  const problems = [];
  if (!name.value.trim()) problems.push([name, "Enter your name."]);
  if (!USERNAME.test(username.value.trim())) problems.push([username, "Use 3 to 25 letters, numbers, dots, dashes or underscores."]);
  if (!email.value.trim() || !email.validity.valid) problems.push([email, "Enter a valid email address."]);
  if (password.value.length < 8) problems.push([password, "Use at least 8 characters."]);
  if (image.files[0] && image.files[0].size > MAX_IMAGE) problems.push([image, "Choose an image under 5 MB."]);
  if (problems.length) { problems.forEach(([input, msg]) => showFieldError(input, msg)); return problems[0][0].focus(); }

  const body = new FormData();
  body.set("name", name.value.trim());
  body.set("username", username.value.trim());
  body.set("email", email.value.trim());
  body.set("password", password.value);
  if (image.files[0]) body.set("image", image.files[0]);

  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Creating account…");
  try {
    await api("/auth/signup", { method: "POST", auth: false, form: body });
    // Sign straight in so the new customer lands on the menu.
    const tokens = await api("/auth/login", { method: "POST", auth: false, json: { username: username.value.trim(), password: password.value } });
    session.save(tokens);
    location.assign("/user/dashboard");
  } catch (err) {
    if (err.status === 409) {
      const target = /email/i.test(err.message) ? email : username;
      showFieldError(target, err.message);
      target.focus();
    } else formAlert(form, err.message);
    setBusy(button, false, "Create account");
  }
});
