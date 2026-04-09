import { createRouter, createWebHistory } from "vue-router";

import { authStore } from "./store";
import AdminDashboard from "./views/AdminDashboard.vue";
import CompanyDashboard from "./views/CompanyDashboard.vue";
import HomeView from "./views/HomeView.vue";
import LoginView from "./views/LoginView.vue";
import RegisterView from "./views/RegisterView.vue";
import StudentDashboard from "./views/StudentDashboard.vue";

const routes = [
  { path: "/", component: HomeView },
  { path: "/login", component: LoginView },
  { path: "/register", component: RegisterView },
  { path: "/admin", component: AdminDashboard, meta: { role: "ADMIN" } },
  { path: "/company", component: CompanyDashboard, meta: { role: "COMPANY" } },
  { path: "/student", component: StudentDashboard, meta: { role: "STUDENT" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  if (!to.meta.role) {
    return next();
  }
  if (!authStore.user || !authStore.token) {
    return next("/login");
  }
  if (authStore.user.role !== to.meta.role) {
    return next("/");
  }
  return next();
});

export default router;
