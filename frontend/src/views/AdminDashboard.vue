<template>
  <section>
    <h1 class="h4 mb-3">Admin Dashboard</h1>
    <div class="row g-3 mb-4">
      <div class="col-md-3" v-for="card in cards" :key="card.label">
        <div class="card shadow-sm">
          <div class="card-body">
            <div class="text-muted small">{{ card.label }}</div>
            <div class="h5 mb-0">{{ card.value }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <h2 class="h6 mb-0">Placement Statistics</h2>
          <div class="d-flex flex-wrap gap-2 align-items-end">
            <div>
              <label class="form-label form-label-sm mb-1">From</label>
              <input v-model="reportStartDate" type="date" class="form-control form-control-sm" />
            </div>
            <div>
              <label class="form-label form-label-sm mb-1">To</label>
              <input v-model="reportEndDate" type="date" class="form-control form-control-sm" />
            </div>
            <button class="btn btn-primary btn-sm" :disabled="reportExporting" @click="startReportExport">
              {{ reportExporting ? "Starting..." : "Export Report" }}
            </button>
            <button class="btn btn-outline-primary btn-sm" :disabled="!adminReportTaskId" @click="checkReportStatus">Check</button>
            <button
              class="btn btn-success btn-sm"
              :disabled="adminReportStatus !== 'COMPLETED'"
              @click="downloadReport"
            >
              Download
            </button>
          </div>
        </div>

        <div v-if="adminReportTaskId" class="alert alert-info py-2">
          Report task: {{ adminReportTaskId }} | Status: {{ adminReportStatus }}
          <span v-if="adminReportPath" class="ms-2">File ready</span>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <div class="border rounded p-2">
              <div class="small text-muted">Selected</div>
              <div class="h5 mb-0">{{ stats.selected }}</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="border rounded p-2">
              <div class="small text-muted">Shortlisted (yet to give interview)</div>
              <div class="h5 mb-0">{{ stats.shortlisted }}</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="border rounded p-2">
              <div class="small text-muted">Rejected</div>
              <div class="h5 mb-0">{{ stats.rejected }}</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="border rounded p-2">
              <div class="small text-muted">Selection Rate</div>
              <div class="h5 mb-0">{{ stats.selection_rate }}%</div>
            </div>
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Top Company</th>
                <th>Selections</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stats.top_companies_by_selections" :key="row.company">
                <td>{{ row.company }}</td>
                <td>{{ row.selected_count }}</td>
              </tr>
              <tr v-if="!stats.top_companies_by_selections.length">
                <td colspan="2" class="text-center text-muted">No selection stats yet</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>
  <div v-if="success" class="alert alert-success">{{ success }}</div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h2 class="h6 mb-3">Company Approvals & Search</h2>
        <div class="row g-2 mb-3">
          <div class="col-md-6">
            <input v-model="companyQuery" class="form-control" placeholder="Search company/email/name" />
          </div>
          <div class="col-md-3">
            <button class="btn btn-primary w-100" @click="fetchCompanies">Search</button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Company</th>
                <th>HR Contact</th>
                <th>Status</th>
                <th>User State</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="company in companies" :key="company.id">
                <td>{{ company.company_name }}</td>
                <td>{{ company.hr_contact }}</td>
                <td>{{ company.approval_status }}</td>
                <td>{{ company.active ? "Active" : "Inactive" }} / {{ company.blacklisted ? "Blacklisted" : "Clear" }}</td>
                <td>
                  <div class="d-flex gap-2 flex-wrap">
                    <button
                      class="btn btn-sm"
                      :class="company.approval_status === 'APPROVED' ? 'btn-success' : 'btn-outline-success'"
                      :disabled="company.approval_status === 'APPROVED'"
                      @click="updateCompanyApproval(company.id, 'APPROVED')"
                    >
                      {{ company.approval_status === 'APPROVED' ? 'Approved' : 'Approve' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="company.approval_status === 'REJECTED' ? 'btn-danger' : 'btn-outline-danger'"
                      :disabled="company.approval_status === 'REJECTED'"
                      @click="updateCompanyApproval(company.id, 'REJECTED')"
                    >
                      {{ company.approval_status === 'REJECTED' ? 'Rejected' : 'Reject' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="company.active ? 'btn-outline-secondary' : 'btn-dark'"
                      @click="toggleUserStatus(company.user_id, !company.active, company.blacklisted)"
                    >
                      {{ company.active ? "Deactivate" : "Activate" }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="company.blacklisted ? 'btn-dark' : 'btn-outline-dark'"
                      @click="toggleUserStatus(company.user_id, company.active, !company.blacklisted)"
                    >
                      {{ company.blacklisted ? "Unblacklist" : "Blacklist" }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!companies.length">
                <td colspan="5" class="text-center text-muted">No companies found</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary btn-sm" :disabled="companyPage <= 1" @click="changeCompanyPage(companyPage - 1)">Prev</button>
          <span class="align-self-center small text-muted">Page {{ companyPage }} / {{ companyPages }}</span>
          <button class="btn btn-outline-secondary btn-sm" :disabled="companyPage >= companyPages" @click="changeCompanyPage(companyPage + 1)">Next</button>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h2 class="h6 mb-3">Drive Approvals</h2>
        <div class="row g-2 mb-3">
          <div class="col-md-5">
            <input v-model="driveQuery" class="form-control" placeholder="Search job/company/branch" />
          </div>
          <div class="col-md-4">
            <select v-model="driveStatusFilter" class="form-select">
              <option value="">All Statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
          <div class="col-md-3">
            <button class="btn btn-primary w-100" @click="fetchDrives">Search</button>
 
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Company</th>
                <th>Job</th>
                <th>Branch</th>
                <th>Deadline</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="drive in drives"
                :key="drive.id"
                :class="{ 'drive-row-closed': drive.status === 'CLOSED' }"
              >
                <td>{{ drive.company }}</td>
                <td>{{ drive.job_title }}</td>
                <td>{{ drive.eligible_branch }}</td>
                <td>{{ new Date(drive.deadline).toLocaleDateString() }}</td>
                <td>{{ drive.status }}</td>
                <td>
                  <div class="d-flex gap-2 flex-wrap">
                    <button
                      class="btn btn-sm"
                      :class="drive.status === 'APPROVED' ? 'btn-success' : 'btn-outline-success'"
                      :disabled="drive.status === 'APPROVED'"
                      @click="updateDriveApproval(drive.id, 'APPROVED')"
                    >
                      {{ drive.status === 'APPROVED' ? 'Approved' : 'Approve' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="drive.status === 'REJECTED' ? 'btn-danger' : 'btn-outline-danger'"
                      :disabled="drive.status === 'REJECTED'"
                      @click="updateDriveApproval(drive.id, 'REJECTED')"
                    >
                      {{ drive.status === 'REJECTED' ? 'Rejected' : 'Reject' }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="drive.status === 'CLOSED' ? 'btn-secondary' : 'btn-outline-secondary'"
                      :disabled="drive.status === 'CLOSED'"
                      @click="updateDriveApproval(drive.id, 'CLOSED')"
                    >
                      {{ drive.status === 'CLOSED' ? 'Closed' : 'Close' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!drives.length">
                <td colspan="6" class="text-center text-muted">No drives found</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary btn-sm" :disabled="drivePage <= 1" @click="changeDrivePage(drivePage - 1)">Prev</button>
          <span class="align-self-center small text-muted">Page {{ drivePage }} / {{ drivePages }}</span>
          <button class="btn btn-outline-secondary btn-sm" :disabled="drivePage >= drivePages" @click="changeDrivePage(drivePage + 1)">Next</button>
        </div>
      </div>
    </div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h2 class="h6 mb-3">Student Search & Status</h2>
        <div class="row g-2 mb-3">
          <div class="col-md-6">
            <input v-model="studentQuery" class="form-control" placeholder="Search student/email/branch" />
          </div>
          <div class="col-md-3">
            <button class="btn btn-primary w-100" @click="fetchStudents">Search</button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Branch</th>
                <th>CGPA</th>
                <th>User State</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in students" :key="student.id">
                <td>{{ student.name }}</td>
                <td>{{ student.email }}</td>
                <td>{{ student.branch }}</td>
                <td>{{ student.cgpa }}</td>
                <td>{{ student.active ? "Active" : "Inactive" }} / {{ student.blacklisted ? "Blacklisted" : "Clear" }}</td>
                <td>
                  <div class="d-flex gap-2 flex-wrap">
                    <button
                      class="btn btn-sm"
                      :class="student.active ? 'btn-outline-secondary' : 'btn-dark'"
                      @click="toggleUserStatus(student.user_id, !student.active, student.blacklisted)"
                    >
                      {{ student.active ? "Deactivate" : "Activate" }}
                    </button>
                    <button
                      class="btn btn-sm"
                      :class="student.blacklisted ? 'btn-dark' : 'btn-outline-dark'"
                      @click="toggleUserStatus(student.user_id, student.active, !student.blacklisted)"
                    >
                      {{ student.blacklisted ? "Unblacklist" : "Blacklist" }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!students.length">
                <td colspan="6" class="text-center text-muted">No students found</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary btn-sm" :disabled="studentPage <= 1" @click="changeStudentPage(studentPage - 1)">Prev</button>
          <span class="align-self-center small text-muted">Page {{ studentPage }} / {{ studentPages }}</span>
          <button class="btn btn-outline-secondary btn-sm" :disabled="studentPage >= studentPages" @click="changeStudentPage(studentPage + 1)">Next</button>
        </div>
      </div>
    </div>

    <div class="card shadow-sm">
      <div class="card-body">
        <h2 class="h6 mb-3">All Applications</h2>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Student</th>
                <th>Email</th>
                <th>Company</th>
                <th>Drive</th>
                <th>Status</th>
                <th>Applied At</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="application in applications" :key="application.id">
                <td>{{ application.student }}</td>
                <td>{{ application.student_email }}</td>
                <td>{{ application.company }}</td>
                <td>{{ application.drive_title }}</td>
                <td>{{ application.status }}</td>
                <td>{{ new Date(application.applied_at).toLocaleString() }}</td>
              </tr>
              <tr v-if="!applications.length">
                <td colspan="6" class="text-center text-muted">No applications found</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary btn-sm" :disabled="applicationPage <= 1" @click="changeApplicationPage(applicationPage - 1)">Prev</button>
          <span class="align-self-center small text-muted">Page {{ applicationPage }} / {{ applicationPages }}</span>
          <button class="btn btn-outline-secondary btn-sm" :disabled="applicationPage >= applicationPages" @click="changeApplicationPage(applicationPage + 1)">Next</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";

import api from "../services/api";

const cards = ref([
  { label: "Students", value: 0 },
  { label: "Companies", value: 0 },
  { label: "Drives", value: 0 },
  { label: "Applications", value: 0 },
]);

const error = ref("");
const success = ref("");

const companyQuery = ref("");
const driveQuery = ref("");
const studentQuery = ref("");
const driveStatusFilter = ref("");

const companies = ref([]);
const drives = ref([]);
const students = ref([]);
const applications = ref([]);
const stats = ref({
  total_applications: 0,
  shortlisted: 0,
  selected: 0,
  rejected: 0,
  selection_rate: 0,
  top_companies_by_selections: [],
});
const reportExporting = ref(false);
const adminReportTaskId = ref("");
const adminReportStatus = ref("-");
const adminReportPath = ref("");

const today = new Date();
const reportEndDate = ref(today.toISOString().slice(0, 10));
const reportStartDate = ref(new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10));

const companyPage = ref(1);
const drivePage = ref(1);
const studentPage = ref(1);
const applicationPage = ref(1);

const companyPages = ref(1);
const drivePages = ref(1);
const studentPages = ref(1);
const applicationPages = ref(1);

async function fetchDashboard() {
  const response = await api.get("/admin/dashboard");
  cards.value = [
    { label: "Students", value: response.data.students },
    { label: "Companies", value: response.data.companies },
    { label: "Drives", value: response.data.drives },
    { label: "Applications", value: response.data.applications },
  ];
}

async function fetchCompanies() {
  const response = await api.get("/admin/companies", { params: { q: companyQuery.value, page: companyPage.value, per_page: 10 } });
  companies.value = response.data.items;
  companyPages.value = Math.max(1, response.data.pages || 1);
}

async function fetchDrives() {
  const response = await api.get("/admin/drives", {
    params: {
      q: driveQuery.value,
      status: driveStatusFilter.value,
      page: drivePage.value,
      per_page: 10,
    },
  });
  drives.value = response.data.items;
  drivePages.value = Math.max(1, response.data.pages || 1);
}

async function fetchStudents() {
  const response = await api.get("/admin/students", { params: { q: studentQuery.value, page: studentPage.value, per_page: 10 } });
  students.value = response.data.items;
  studentPages.value = Math.max(1, response.data.pages || 1);
}

async function fetchApplications() {
  const response = await api.get("/admin/applications", { params: { page: applicationPage.value, per_page: 10 } });
  applications.value = response.data.items;
  applicationPages.value = Math.max(1, response.data.pages || 1);
}

async function fetchStats() {
  const response = await api.get("/admin/stats");
  stats.value = response.data;
}

async function refreshAll() {
  const operations = [
    ["dashboard", fetchDashboard],
    ["stats", fetchStats],
    ["companies", fetchCompanies],
    ["drives", fetchDrives],
    ["students", fetchStudents],
    ["applications", fetchApplications],
  ];

  const failures = [];
  for (const [name, fn] of operations) {
    try {
      await fn();
    } catch (err) {
      failures.push(`${name}: ${err?.response?.data?.message || err?.message || "failed"}`);
    }
  }

  if (failures.length) {
    throw new Error(failures.join(" | "));
  }
}

async function changeCompanyPage(page) {
  companyPage.value = page;
  await fetchCompanies();
}

async function changeDrivePage(page) {
  drivePage.value = page;
  await fetchDrives();
}

async function changeStudentPage(page) {
  studentPage.value = page;
  await fetchStudents();
}

async function changeApplicationPage(page) {
  applicationPage.value = page;
  await fetchApplications();
}

async function updateCompanyApproval(companyId, status) {
  error.value = "";
  success.value = "";
  try {
    await api.put(`/admin/companies/${companyId}/approval`, { status });
    await refreshAll();
    success.value = `Company status updated to ${status}`;
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || "Failed to update company approval";
  }
}

async function updateDriveApproval(driveId, status) {
  error.value = "";
  success.value = "";
  try {
    await api.put(`/admin/drives/${driveId}/approval`, { status });
    await refreshAll();
    success.value = `Drive status updated to ${status}`;
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || "Failed to update drive status";
  }
}

async function toggleUserStatus(userId, isActive, isBlacklisted) {
  error.value = "";
  success.value = "";
  try {
    await api.put(`/admin/users/${userId}/status`, {
      is_active: isActive,
      is_blacklisted: isBlacklisted,
    });
    await refreshAll();
    success.value = "User status updated successfully";
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || "Failed to update user status";
  }
}

async function startReportExport() {
  error.value = "";
  success.value = "";
  if (!reportStartDate.value || !reportEndDate.value) {
    error.value = "Please choose both start and end dates";
    return;
  }
  reportExporting.value = true;
  try {
    const response = await api.post("/admin/reports/export", {
      start_date: reportStartDate.value,
      end_date: reportEndDate.value,
    });
    adminReportTaskId.value = response.data.task_id;
    adminReportStatus.value = "PENDING";
    adminReportPath.value = "";
    success.value = "Report export started";
  } catch (err) {
    error.value = err?.response?.data?.message || "Failed to start report export";
  } finally {
    reportExporting.value = false;
  }
}

async function checkReportStatus() {
  if (!adminReportTaskId.value) {
    return;
  }
  error.value = "";
  success.value = "";
  try {
    const response = await api.get(`/admin/reports/tasks/${adminReportTaskId.value}`);
    adminReportStatus.value = response.data.status;
    adminReportPath.value = response.data.result_path || "";
    if (response.data.status === "COMPLETED") {
      success.value = "Report export completed";
    }
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to fetch report status";
  }
}

async function downloadReport() {
  if (!adminReportTaskId.value || adminReportStatus.value !== "COMPLETED") {
    return;
  }
  error.value = "";
  success.value = "";
  try {
    const response = await api.get(`/admin/reports/tasks/${adminReportTaskId.value}/download`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `admin_report_${reportStartDate.value}_to_${reportEndDate.value}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    error.value = err?.response?.data?.message || "Unable to download report";
  }
}

onMounted(async () => {
  try {
    await refreshAll();
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || "Unable to load admin data";
  }
});
</script>

<style scoped>
.drive-row-closed {
  opacity: 0.62;
  transition: opacity 0.25s ease;
}

.drive-row-closed:hover {
  opacity: 0.78;
}
</style>
