import { reactive } from "vue";

export const authStore = reactive({
  token: localStorage.getItem("access_token"),
  user: JSON.parse(localStorage.getItem("user") || "null"),
  setSession(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(user));
  },
  clearSession() {
    this.token = null;
    this.user = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
  },
});
