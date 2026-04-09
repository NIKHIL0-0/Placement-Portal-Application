<template>
  <div class="min-vh-100 bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container">
        <RouterLink class="navbar-brand" to="/">Placement Portal</RouterLink>
        <div class="d-flex gap-2">
          <RouterLink v-if="!authStore.user" class="btn btn-outline-info btn-sm" to="/register">Register</RouterLink>
          <RouterLink v-if="!authStore.user" class="btn btn-outline-light btn-sm" to="/login">Login</RouterLink>
          <button v-else class="btn btn-warning btn-sm" @click="logout">Logout</button>
        </div>
      </div>
    </nav>

    <main class="container py-4">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";

import { authStore } from "./store";

const router = useRouter();

function logout() {
  authStore.clearSession();
  router.push("/login");
}
</script>
