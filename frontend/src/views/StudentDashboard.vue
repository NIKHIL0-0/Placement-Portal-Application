<template>
  <section>
    <h1 class="h4 mb-3">Student Dashboard</h1>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6 mb-3">Profile</h2>
        <form class="row g-2" @submit.prevent="updateProfile">
          <div class="col-md-3">
            <label class="form-label">Name</label>
            <input class="form-control" :value="data.student?.name || ''" disabled />
          </div>
          <div class="col-md-3">
            <label class="form-label">Branch</label>
            <input v-model="profileForm.branch" class="form-control" required />
          </div>
          <div class="col-md-2">
            <label class="form-label">CGPA</label>
            <input v-model.number="profileForm.cgpa" type="number" min="0" max="10" step="0.01" class="form-control" required />
          </div>
          <div class="col-md-2">
            <label class="form-label">Graduation Year</label>
            <input v-model.number="profileForm.graduation_year" type="number" min="2020" max="2100" class="form-control" required />
          </div>
          <div class="col-md-3">
            <label class="form-label">Resume URL</label>
            <input v-model="profileForm.resume_url" class="form-control" placeholder="https://..." />
          </div>
          <div class="col-12">
            <button class="btn btn-primary btn-sm" :disabled="profileSaving">{{ profileSaving ? "Saving..." : "Update Profile" }}</button>
            <a
              v-if="profileForm.resume_url || data.student?.resume_url"
              class="btn btn-outline-primary btn-sm ms-2"
              :href="toAbsoluteApiUrl(profileForm.resume_url || data.student?.resume_url)"
              target="_blank"
              rel="noreferrer"
            >
              View Resume
            </a>
          </div>
        </form>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6 mb-3">Company Directory</h2>
        <div class="row g-2 mb-3">
          <div class="col-md-6">
            <input v-model="companyQuery" class="form-control" placeholder="Search approved companies" />
          </div>
          <div class="col-md-2">
            <button class="btn btn-outline-primary w-100" @click="fetchCompanies">Search</button>
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Company</th>
                <th>HR Contact</th>
                <th>Website</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="company in companies" :key="company.id">
                <td>{{ company.company_name }}</td>
                <td>{{ company.hr_contact }}</td>
                <td>
                  <a v-if="company.website" :href="company.website" target="_blank" rel="noreferrer">{{ company.website }}</a>
                  <span v-else>-</span>
                </td>
              </tr>
              <tr v-if="!companies.length">
                <td colspan="3" class="text-center text-muted">No companies found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6 mb-3">Approved Drives</h2>
        <div class="row g-2 mb-3">
          <div class="col-md-4">
            <input v-model="driveQuery" class="form-control" placeholder="Search job title" />
          </div>
          <div class="col-md-4">
            <input v-model="branchFilter" class="form-control" placeholder="Filter by branch" />
          </div>
          <div class="col-md-2">
            <button class="btn btn-outline-primary w-100" @click="fetchDashboard">Search</button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Company</th>
                <th>Job</th>
                <th>Eligibility</th>
                <th>Deadline</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="drive in data.approved_drives" :key="drive.id">
                <td>{{ drive.company }}</td>
                <td>{{ drive.job_title }}</td>
                <td>{{ drive.eligible_branch }} / {{ drive.min_cgpa }} / {{ drive.eligible_year }}</td>
                <td>{{ new Date(drive.deadline).toLocaleDateString() }}</td>
                <td>
                  <button
                    class="btn btn-sm"
                    :class="isApplied(drive.id) ? 'btn-secondary' : 'btn-success'"
                    :disabled="isApplied(drive.id)"
                    @click="applyToDrive(drive.id)"
                  >
                    {{ isApplied(drive.id) ? "Applied" : "Apply" }}
                  </button>
                </td>
              </tr>
              <tr v-if="!data.approved_drives?.length">
                <td colspan="5" class="text-center text-muted">No approved drives found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h2 class="h6 mb-0">Application History</h2>
          <div class="d-flex gap-2">
            <button class="btn btn-outline-primary btn-sm" @click="fetchApplications">Refresh</button>
            <button class="btn btn-primary btn-sm" @click="startExport">Export CSV</button>
          </div>
        </div>

        <div v-if="exportTaskId" class="alert alert-info py-2">
          Export task: {{ exportTaskId }} | Status: {{ exportStatus }}
          <button class="btn btn-link btn-sm" @click="checkExportStatus">Check</button>
          <button v-if="exportStatus === 'COMPLETED'" class="btn btn-success btn-sm ms-2" @click="downloadExport">Download CSV</button>
          <span v-if="exportPath" class="ms-2">File ready</span>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Company</th>
                <th>Drive</th>
                <th>Status</th>
                <th>Applied At</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in applications" :key="app.id">
                <td>{{ app.company }}</td>
                <td>{{ app.drive_title }}</td>
                <td>{{ app.status }}</td>
                <td>{{ new Date(app.applied_at).toLocaleString() }}</td>
              </tr>
              <tr v-if="!applications.length">
                <td colspan="4" class="text-center text-muted">No applications found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import api from "../services/api";

const data = ref({ student: null, approved_drives: [] });
const applications = ref([]);
const companies = ref([]);
const error = ref("");
const success = ref("");
const profileSaving = ref(false);

const driveQuery = ref("");
const branchFilter = ref("");
const companyQuery = ref("");

const profileForm = reactive({
  branch: "",
  cgpa: 0,
  graduation_year: new Date().getFullYear(),
  resume_url: "",
});

const exportTaskId = ref("");
const exportStatus = ref("-");
const exportPath = ref("");

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

const appliedDriveMap = computed(() => {
  const map = {};
  for (const app of applications.value) {
    map[app.drive_id] = app;
  }
  return map;
});

function isApplied(driveId) {
  return Boolean(appliedDriveMap.value[driveId]);
}

function toAbsoluteApiUrl(url) {
  if (!url) {
    return "";
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  if (url.startsWith("/")) {
    const apiOrigin = API_BASE.replace(/\/api\/?$/, "");
    return `${apiOrigin}${url}`;
  }
  return `${API_BASE}/${url}`;
}

function syncProfileForm() {
  if (!data.value.student) {
    return;
  }
  profileForm.branch = data.value.student.branch;
  profileForm.cgpa = data.value.student.cgpa;
  profileForm.graduation_year = data.value.student.graduation_year;
  profileForm.resume_url = data.value.student.resume_url || "";
}

async function fetchDashboard() {
  const response = await api.get("/student/dashboard", {
    params: {
      q: driveQuery.value,
      branch: branchFilter.value,
    },
  });
  data.value = response.data;
  syncProfileForm();
}

async function fetchApplications() {
  const response = await api.get("/student/applications");
  applications.value = response.data;
}

async function fetchCompanies() {
  const response = await api.get("/student/companies", { params: { q: companyQuery.value } });
  companies.value = response.data;
}

async function applyToDrive(driveId) {
  error.value = "";
  success.value = "";
  try {
    await api.post(`/student/drives/${driveId}/apply`);
    await fetchApplications();
    success.value = "Application submitted successfully";
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to apply for drive";
  }
}

async function updateProfile() {
  error.value = "";
  success.value = "";
  profileSaving.value = true;
  try {
    await api.put("/student/profile", {
      branch: profileForm.branch,
      cgpa: Number(profileForm.cgpa),
      graduation_year: Number(profileForm.graduation_year),
      resume_url: profileForm.resume_url,
    });
    await fetchDashboard();
    success.value = "Profile updated successfully";
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to update profile";
  } finally {
    profileSaving.value = false;
  }
}

async function startExport() {
  error.value = "";
  success.value = "";
  try {
    const response = await api.post("/student/applications/export");
    exportTaskId.value = response.data.task_id;
    exportStatus.value = "PENDING";
    exportPath.value = "";
    success.value = "CSV export started";
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to start export";
  }
}

async function checkExportStatus() {
  if (!exportTaskId.value) {
    return;
  }
  error.value = "";
  success.value = "";
  try {
    const response = await api.get(`/student/tasks/${exportTaskId.value}`);
    exportStatus.value = response.data.status;
    exportPath.value = response.data.result_path || "";
    if (response.data.status === "COMPLETED") {
      success.value = "Export completed successfully";
    }
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to fetch task status";
  }
}

async function downloadExport() {
  if (!exportTaskId.value || exportStatus.value !== "COMPLETED") {
    return;
  }

  error.value = "";
  success.value = "";
  try {
    const response = await api.get(`/student/tasks/${exportTaskId.value}/download`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `applications_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to download export";
  }
}

onMounted(async () => {
  try {
    await Promise.all([fetchDashboard(), fetchApplications(), fetchCompanies()]);
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to load student dashboard";
  }
});
</script>
