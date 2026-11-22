import { boot, $ } from "../core.js";
import { wireContactForm } from "../contact-form.js";

const user = await boot("user");
wireContactForm($("#contact-form"), user);
