<template>
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card shadow-sm">
        <div class="card-body">
          <h2 class="h4 mb-3">Login</h2>
          <form @submit.prevent="submitLogin">
            <div class="mb-3">
              <label class="form-label">Email</label>
              <input v-model="form.email" type="email" class="form-control" required />
            </div>
            <div class="mb-3">
              <label class="form-label">Password</label>
              <input v-model="form.password" type="password" class="form-control" required />
            </div>
            <button class="btn btn-primary" :disabled="loading">{{ loading ? "Please wait..." : "Login" }}</button>
          </form>

          <p v-if="error" class="text-danger mt-3 mb-0">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import api from "../services/api";
import { authStore } from "../store";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const form = reactive({
  email: "",
  password: "",
});

async function submitLogin() {
  loading.value = true;
  error.value = "";
  try {
    const response = await api.post("/auth/login", form);
    authStore.setSession(response.data.access_token, response.data.user);

    if (response.data.user.role === "ADMIN") {
      router.push("/admin");
    } else if (response.data.user.role === "COMPANY") {
      router.push("/company");
    } else {
      router.push("/student");
    }
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to login";
  } finally {
    loading.value = false;
  }
}
</script>
