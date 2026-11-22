import { boot, api, el, $, avatar, loadUser, money, setBusy, toast, showFieldError, clearFormErrors, formAlert } from "../core.js";

let user = await boot("user");
const form = $("#profile-form");
const USERNAME = /^[A-Za-z0-9_.-]{3,25}$/;

function render(profile) {
  $("#profile-avatar").replaceChildren(avatar(profile, "6rem"));
  $(".profile__name").textContent = profile.name;
  $("#profile-handle").textContent = `@${profile.username} · ${profile.email}`;
  $("#profile-badges").replaceChildren(el("span", { class: `badge ${profile.is_staff ? "badge--staff" : ""}` }, profile.is_staff ? "Staff" : "Customer"));
  const s = profile.stats;
  $("#profile-stats").replaceChildren(
    ...[[s.orders_count, "Orders placed"], [s.pizzas_ordered, "Pizzas ordered"], [money(s.total_spent), "Total spent"]]
      .map(([v, label]) => el("div", { class: "stat" }, el("span", { class: "stat__value" }, v), el("span", { class: "stat__label" }, label))));
  form.elements.name.value = profile.name;
  form.elements.username.value = profile.username;
  form.elements.email.value = profile.email;
}
render(user);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearFormErrors(form);
  const { name, username, email } = form.elements;
  const problems = [];
  if (!name.value.trim()) problems.push([name, "Enter your name."]);
  if (!USERNAME.test(username.value.trim())) problems.push([username, "Use 3 to 25 letters, numbers, dots, dashes or underscores."]);
  if (!email.value.trim() || !email.validity.valid) problems.push([email, "Enter a valid email address."]);
  if (problems.length) { problems.forEach(([i, m]) => showFieldError(i, m)); return problems[0][0].focus(); }
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Saving…");
  try {
    user = await api("/auth/user", { method: "PUT", json: { name: name.value.trim(), username: username.value.trim(), email: email.value.trim() } });
    render(user);
    toast("Profile saved.");
  } catch (err) {
    if (err.status === 409) { const t = /email/i.test(err.message) ? email : username; showFieldError(t, err.message); t.focus(); }
    else formAlert(form, err.message);
  } finally { setBusy(button, false, "Save changes"); }
});

$("#avatar-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) return toast("Choose an image under 5 MB.", "error");
  const body = new FormData();
  body.set("avatar", file);
  try {
    await api("/auth/user/avatar", { method: "POST", form: body });
    user = await loadUser(true);
    render(user);
    toast("Photo updated.");
    document.querySelectorAll("[data-user-menu] .avatar, [data-sidebar-who] .avatar").forEach((n) => n.replaceWith(avatar(user, n.style.getPropertyValue("--size"))));
  } catch (err) { toast(err.message, "error"); }
});
