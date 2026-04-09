<template>
  <div class="row justify-content-center">
    <div class="col-lg-8">
      <div class="card shadow-sm">
        <div class="card-body">
          <h2 class="h4 mb-3">Register</h2>

          <div class="btn-group mb-3" role="group">
            <button class="btn" :class="mode === 'STUDENT' ? 'btn-primary' : 'btn-outline-primary'" @click="mode = 'STUDENT'">Student</button>
            <button class="btn" :class="mode === 'COMPANY' ? 'btn-primary' : 'btn-outline-primary'" @click="mode = 'COMPANY'">Company</button>
          </div>

          <form @submit.prevent="submit">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Full Name</label>
                <input v-model="form.full_name" type="text" class="form-control" required />
              </div>
              <div class="col-md-6">
                <label class="form-label">Email</label>
                <input v-model="form.email" type="email" class="form-control" required />
              </div>
              <div class="col-md-6">
                <label class="form-label">Password</label>
                <input v-model="form.password" type="password" class="form-control" minlength="6" required />
              </div>

              <template v-if="mode === 'STUDENT'">
                <div class="col-md-6">
                  <label class="form-label">Branch</label>
                  <input v-model="form.branch" type="text" class="form-control" required />
                </div>
                <div class="col-md-6">
                  <label class="form-label">CGPA</label>
                  <input v-model.number="form.cgpa" type="number" min="0" max="10" step="0.01" class="form-control" required />
                </div>
                <div class="col-md-6">
                  <label class="form-label">Graduation Year</label>
                  <input v-model.number="form.graduation_year" type="number" min="2020" max="2100" class="form-control" required />
                </div>
                <div class="col-md-12">
                  <label class="form-label">Resume URL (optional)</label>
                  <input v-model="form.resume_url" type="url" class="form-control" />
                </div>
              </template>

              <template v-else>
                <div class="col-md-6">
                  <label class="form-label">Company Name</label>
                  <input v-model="form.company_name" type="text" class="form-control" required />
                </div>
                <div class="col-md-6">
                  <label class="form-label">HR Contact</label>
                  <input v-model="form.hr_contact" type="text" class="form-control" required />
                </div>
                <div class="col-md-12">
                  <label class="form-label">Website (optional)</label>
                  <input v-model="form.website" type="url" class="form-control" />
                </div>
              </template>
            </div>

            <button class="btn btn-success mt-3" :disabled="loading">{{ loading ? "Submitting..." : "Register" }}</button>
          </form>

          <p v-if="message" class="text-success mt-3 mb-0">{{ message }}</p>
          <p v-if="error" class="text-danger mt-3 mb-0">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";

import api from "../services/api";

const mode = ref("STUDENT");
const loading = ref(false);
const message = ref("");
const error = ref("");

const form = reactive({
  full_name: "",
  email: "",
  password: "",
  branch: "",
  cgpa: 0,
  graduation_year: new Date().getFullYear(),
  resume_url: "",
  company_name: "",
  hr_contact: "",
  website: "",
});

async function submit() {
  loading.value = true;
  message.value = "";
  error.value = "";
  try {
    if (mode.value === "STUDENT") {
      await api.post("/auth/register/student", {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        branch: form.branch,
        cgpa: form.cgpa,
        graduation_year: form.graduation_year,
        resume_url: form.resume_url || null,
      });
      message.value = "Student registration successful. You can login now.";
    } else {
      await api.post("/auth/register/company", {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        company_name: form.company_name,
        hr_contact: form.hr_contact,
        website: form.website || null,
      });
      message.value = "Company registration submitted. Wait for admin approval before login.";
    }
  } catch (err) {
    error.value = err?.response?.data?.message || "Registration failed";
  } finally {
    loading.value = false;
  }
}
</script>
