<template>
  <section>
    <h1 class="h4 mb-3">Company Dashboard</h1>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6">Company</h2>
        <p class="mb-1"><strong>Name:</strong> {{ data.company?.name || "-" }}</p>
        <p class="mb-0"><strong>Status:</strong> {{ data.company?.approval_status || "-" }}</p>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6 mb-3">Create Placement Drive</h2>
        <form class="row g-3" @submit.prevent="createDrive">
          <div class="col-md-6">
            <label class="form-label">Job Title</label>
            <input v-model="driveForm.job_title" class="form-control" required />
          </div>
          <div class="col-md-6">
            <label class="form-label">Eligible Branch</label>
            <input v-model="driveForm.eligible_branch" class="form-control" required />
          </div>
          <div class="col-md-12">
            <label class="form-label">Job Description</label>
            <textarea v-model="driveForm.job_description" class="form-control" rows="3" required />
          </div>
          <div class="col-md-4">
            <label class="form-label">Minimum CGPA</label>
            <input v-model.number="driveForm.min_cgpa" type="number" min="0" max="10" step="0.01" class="form-control" required />
          </div>
          <div class="col-md-4">
            <label class="form-label">Eligible Year</label>
            <input v-model.number="driveForm.eligible_year" type="number" min="2020" max="2100" class="form-control" required />
          </div>
          <div class="col-md-4">
            <label class="form-label">Application Deadline</label>
            <input v-model="driveForm.application_deadline" type="datetime-local" class="form-control" required />
          </div>
          <div class="col-12">
            <button class="btn btn-primary" :disabled="submittingDrive || data.company?.approval_status !== 'APPROVED'">
              {{ submittingDrive ? "Submitting..." : "Create Drive" }}
            </button>
            <small v-if="data.company?.approval_status !== 'APPROVED'" class="text-muted ms-2">Company must be admin-approved to create drives.</small>
          </div>
        </form>
      </div>
    </div>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h2 class="h6">Placement Drives</h2>
        <div class="table-responsive">
          <table class="table table-sm">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Deadline</th>
                <th>Applicants</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="drive in data.drives" :key="drive.id">
                <td>{{ drive.id }}</td>
                <td>{{ drive.job_title }}</td>
                <td>{{ drive.status }}</td>
                <td>{{ new Date(drive.deadline).toLocaleString() }}</td>
                <td>{{ drive.applicants }}</td>
                <td>
                  <button class="btn btn-outline-primary btn-sm" @click="loadDriveApplications(drive.id)">View Applicants</button>
                </td>
              </tr>
              <tr v-if="!data.drives?.length">
                <td colspan="6" class="text-center text-muted">No drives found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card shadow-sm" v-if="selectedDriveId">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h2 class="h6 mb-0">Applicants for Drive #{{ selectedDriveId }}</h2>
          <button class="btn btn-outline-secondary btn-sm" @click="selectedDriveId = null">Close</button>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Student</th>
                <th>Email</th>
                <th>Branch/CGPA</th>
                <th>Status</th>
                <th>Interview</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in selectedDriveApplications" :key="app.application_id">
                <td>{{ app.student_name }}</td>
                <td>{{ app.student_email }}</td>
                <td>{{ app.branch }} / {{ app.cgpa }}</td>
                <td>{{ app.status }}</td>
                <td>{{ app.interview ? new Date(app.interview).toLocaleString() : "Not scheduled" }}</td>
                <td>
                  <div class="d-flex gap-2 flex-wrap">
                    <button
                      class="btn btn-sm"
                      :class="app.status === 'SHORTLISTED' ? 'btn-primary action-selected' : 'btn-outline-primary'"
                      :disabled="app.status === 'SHORTLISTED'"
                      @click="updateApplicationStatus(app.application_id, 'SHORTLISTED')"
                    >
                      {{ app.status === 'SHORTLISTED' ? 'Shortlisted' : 'Shortlist' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="app.status === 'SELECTED' ? 'btn-success action-selected' : 'btn-outline-success'"
                      :disabled="app.status === 'SELECTED'"
                      @click="updateApplicationStatus(app.application_id, 'SELECTED')"
                    >
                      {{ app.status === 'SELECTED' ? 'Selected' : 'Select' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="app.status === 'REJECTED' ? 'btn-danger action-selected' : 'btn-outline-danger'"
                      :disabled="app.status === 'REJECTED'"
                      @click="updateApplicationStatus(app.application_id, 'REJECTED')"
                    >
                      {{ app.status === 'REJECTED' ? 'Rejected' : 'Reject' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="interviewForm.applicationId === app.application_id ? 'btn-secondary action-selected' : 'btn-outline-secondary'"
                      @click="openInterviewForm(app.application_id, app.interview)"
                    >
                      {{ app.interview ? 'Edit Interview' : 'Schedule Interview' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!selectedDriveApplications.length">
                <td colspan="6" class="text-center text-muted">No applicants found</td>
              </tr>
            </tbody>
          </table>
        </div>

        <form v-if="interviewForm.applicationId" class="border rounded p-3 mt-3" @submit.prevent="scheduleInterview">
          <h3 class="h6">Schedule Interview for Application #{{ interviewForm.applicationId }}</h3>
          <div class="row g-2">
            <div class="col-md-4">
              <label class="form-label">Interview Date/Time</label>
              <input ref="interviewDateInput" v-model="interviewForm.interview_at" type="datetime-local" class="form-control" required />
            </div>
            <div class="col-md-3">
              <label class="form-label">Mode</label>
              <select v-model="interviewForm.mode" class="form-select">
                <option value="ONLINE">ONLINE</option>
                <option value="OFFLINE">OFFLINE</option>
              </select>
            </div>
            <div class="col-md-5">
              <label class="form-label">Meeting Link / Location</label>
              <input v-model="interviewForm.meeting_link" class="form-control" />
            </div>
          </div>
          <div class="mt-3 d-flex gap-2">
            <button class="btn btn-primary" type="submit">Save Interview</button>
            <button class="btn btn-outline-secondary" type="button" @click="clearInterviewForm">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from "vue";

import api from "../services/api";

const data = ref({ company: null, drives: [] });
const error = ref("");
const success = ref("");
const submittingDrive = ref(false);

const selectedDriveId = ref(null);
const selectedDriveApplications = ref([]);
const interviewDateInput = ref(null);

const driveForm = reactive({
  job_title: "",
  job_description: "",
  eligible_branch: "",
  min_cgpa: 0,
  eligible_year: new Date().getFullYear(),
  application_deadline: "",
});

const interviewForm = reactive({
  applicationId: null,
  interview_at: "",
  mode: "ONLINE",
  meeting_link: "",
});

function toIsoDateTime(localDateTime) {
  if (!localDateTime) {
    return "";
  }
  return new Date(localDateTime).toISOString();
}

function toLocalDateTimeInput(isoDateTime) {
  if (!isoDateTime) {
    return "";
  }
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (value) => String(value).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function clearDriveForm() {
  driveForm.job_title = "";
  driveForm.job_description = "";
  driveForm.eligible_branch = "";
  driveForm.min_cgpa = 0;
  driveForm.eligible_year = new Date().getFullYear();
  driveForm.application_deadline = "";
}

function clearInterviewForm() {
  interviewForm.applicationId = null;
  interviewForm.interview_at = "";
  interviewForm.mode = "ONLINE";
  interviewForm.meeting_link = "";
}

async function loadDashboard() {
  const response = await api.get("/company/dashboard");
  data.value = response.data;
}

async function createDrive() {
  error.value = "";
  success.value = "";
  submittingDrive.value = true;
  try {
    await api.post("/company/drives", {
      job_title: driveForm.job_title,
      job_description: driveForm.job_description,
      eligible_branch: driveForm.eligible_branch,
      min_cgpa: Number(driveForm.min_cgpa),
      eligible_year: Number(driveForm.eligible_year),
      application_deadline: toIsoDateTime(driveForm.application_deadline),
    });
    clearDriveForm();
    await loadDashboard();
    success.value = "Drive created successfully and sent for admin approval";
  } catch (err) {
    error.value = err?.response?.data?.message || "Failed to create drive";
  } finally {
    submittingDrive.value = false;
  }
}

async function loadDriveApplications(driveId) {
  error.value = "";
  try {
    const response = await api.get(`/company/drives/${driveId}/applications`);
    selectedDriveId.value = driveId;
    selectedDriveApplications.value = response.data;
    clearInterviewForm();
  } catch (err) {
    error.value = err?.response?.data?.message || "Failed to load applications";
  }
}

async function updateApplicationStatus(applicationId, status) {
  error.value = "";
  success.value = "";
  try {
    await api.put(`/company/applications/${applicationId}/status`, { status });
    if (selectedDriveId.value) {
      await loadDriveApplications(selectedDriveId.value);
    }
    success.value = `Application status updated to ${status}`;
  } catch (err) {
    error.value = err?.response?.data?.message || "Failed to update status";
  }
}

async function openInterviewForm(applicationId, interviewAt) {
  interviewForm.applicationId = applicationId;
  interviewForm.interview_at = toLocalDateTimeInput(interviewAt);
  await nextTick();
  if (interviewDateInput.value) {
    interviewDateInput.value.focus();
    if (typeof interviewDateInput.value.showPicker === "function") {
      interviewDateInput.value.showPicker();
    }
  }
}

async function scheduleInterview() {
  error.value = "";
  success.value = "";
  try {
    await api.post(`/company/applications/${interviewForm.applicationId}/interview`, {
      interview_at: toIsoDateTime(interviewForm.interview_at),
      mode: interviewForm.mode,
      meeting_link: interviewForm.meeting_link,
    });
    if (selectedDriveId.value) {
      await loadDriveApplications(selectedDriveId.value);
    }
    success.value = "Interview scheduled successfully";
    clearInterviewForm();
  } catch (err) {
    error.value = err?.response?.data?.message || "Failed to schedule interview";
  }
}

onMounted(async () => {
  try {
    await loadDashboard();
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to load company dashboard";
  }
});
</script>

<style scoped>
.action-selected {
  opacity: 0.65;
  transition: opacity 0.2s ease;
}

.action-selected:hover {
  opacity: 0.8;
}
</style>
