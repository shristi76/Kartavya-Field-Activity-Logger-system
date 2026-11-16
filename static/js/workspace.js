const requestJson = async (url, options = {}) => {
  const token = sessionStorage.getItem("field_access_token");
  const headers = { ...(options.headers || {}), "X-Requested-With": "XMLHttpRequest", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  const response = await fetch(url, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401) { sessionStorage.removeItem("field_access_token"); location.href = "/auth"; throw new Error("Please sign in again."); }
  if (!response.ok) throw new Error(body.error || "The request could not be completed.");
  return body;
};
let user = null;
let activities = [];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function showMessage(message, error = false) {
  const el = document.querySelector("#statusMessage");
  el.textContent = message; el.style.display = "block"; el.style.color = error ? "#b83d31" : "#16805a";
  window.setTimeout(() => { el.style.display = "none"; }, 5000);
}
async function loadActivities() {
  const tbody = document.querySelector("#activitiesTableBody");
  tbody.innerHTML = '<tr><td colspan="8" class="empty-state">Loading reports…</td></tr>';
  try {
    const result = await requestJson(user.role === "admin" ? "/api/admin/activities" : "/api/activities?limit=100"); activities = result.data || [];
    const total = document.querySelector("#totalReports"); if (total) total.textContent = String(activities.length);
    const workerCount = document.querySelector("#workerCount"); if (workerCount) workerCount.textContent = String(new Set(activities.map(row => row.user_id)).size);
    if (!activities.length) { tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No reports yet.</td></tr>'; return; }
    tbody.innerHTML = activities.map(row => user.role === "admin" ? `<tr>
      <td>#${row.id}${row.audio_file ? `<br><a href="/api/audio/${encodeURIComponent(row.audio_file)}">Open audio</a>` : ""}</td><td>${escapeHtml(row.created_at)}</td>
      <td>${escapeHtml(row.worker_name || row.speaker_id)}<br><small>ID: ${escapeHtml(row.speaker_id)}</small></td><td>${escapeHtml(row.organization || "—")}</td>
      <td>${escapeHtml(row.activity || row.translated_text || "—")}</td><td>${escapeHtml(row.beneficiaries || "—")}</td><td>${escapeHtml(row.location || "—")}</td>
      <td><div class="admin-actions"><button class="btn btn-secondary" data-view="${row.id}">View</button><button class="btn btn-secondary" data-edit="${row.id}">Edit</button><button class="btn btn-primary" data-export="${row.id}">PDF</button><button class="btn btn-danger" data-delete="${row.id}">Delete</button></div></td>
    </tr>` : `<tr>
      <td>${row.id}</td><td>${escapeHtml(row.created_at)}</td>
      <td>${escapeHtml(row.worker_name || row.speaker_id)}<br><small>${escapeHtml(row.organization || "")}</small></td>
      <td>${row.audio_file ? `<a href="/api/audio/${encodeURIComponent(row.audio_file)}">Open audio</a>` : "—"}</td>
      <td>${escapeHtml(row.activity || row.translated_text || "—")}</td><td>${escapeHtml(row.beneficiaries || "—")}</td><td>${escapeHtml(row.location || "—")}</td>
      <td><button class="btn btn-secondary" data-edit="${row.id}">Edit</button> <button class="btn btn-primary" data-export="${row.id}">Download</button> ${user.role === "admin" ? `<button class="btn btn-danger" data-delete="${row.id}">Delete</button>` : ""}</td>
    </tr>`).join("");
    tbody.querySelectorAll("[data-edit]").forEach(button => button.addEventListener("click", () => editActivity(Number(button.dataset.edit))));
    tbody.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => viewActivity(Number(button.dataset.view))));
    tbody.querySelectorAll("[data-delete]").forEach(button => button.addEventListener("click", () => removeActivity(Number(button.dataset.delete))));
    tbody.querySelectorAll("[data-export]").forEach(button => button.addEventListener("click", () => downloadOne(Number(button.dataset.export))));
  } catch (error) { tbody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(error.message)}</td></tr>`; }
}
function viewActivity(id) {
  const row = activities.find(item => item.id === id); if (!row) return;
  document.querySelector("#detailTitle").textContent = `Report #${row.id}`;
  const fields = [
    ["Worker", row.worker_name], ["Worker ID", row.speaker_id], ["Organisation", row.organization], ["Date", row.created_at],
    ["District", row.district], ["Location", row.location], ["Beneficiaries", row.beneficiaries], ["Activity", row.activity],
    ["Translation", row.translated_text], ["Hindi transcription", row.hindi_text], ["Audio file", row.audio_file], ["Photo file", row.photo_file],
  ];
  document.querySelector("#activityDetails").innerHTML = fields.map(([label, value]) => `<div class="detail-field ${["Activity", "Translation", "Hindi transcription"].includes(label) ? "wide" : ""}"><strong>${escapeHtml(label)}</strong>${escapeHtml(value || "—")}</div>`).join("");
  document.querySelector("#activityDialog").showModal();
}
async function editActivity(id) {
  const row = activities.find(item => item.id === id); if (!row) return;
  const editDialog = document.querySelector("#editDialog");
  if (user.role === "admin" && editDialog) {
    const form = document.querySelector("#adminEditForm");
    editDialog.dataset.reportId = String(id);
    for (const field of ["worker_name", "speaker_id", "organization", "district", "hindi_text", "translated_text", "activity", "beneficiaries", "location"]) form.elements.namedItem(field).value = row[field] || "";
    editDialog.showModal();
    return;
  }
  const activity = prompt("Activity", row.activity || ""); if (activity === null) return;
  const locationValue = prompt("Location", row.location || ""); if (locationValue === null) return;
  try {
    await requestJson(`/api/activities/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ hindi_text: row.hindi_text, activity, location: locationValue, translated_text: row.translated_text || "", beneficiaries: row.beneficiaries || "", worker_name: row.worker_name || "", organization: row.organization || "", district: row.district || "" }) });
    await loadActivities(); showMessage("Report updated.");
  } catch (error) { showMessage(error.message, true); }
}
async function saveAdminEdit(event) {
  event.preventDefault();
  const dialog = document.querySelector("#editDialog");
  const id = Number(dialog.dataset.reportId);
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  try {
    await requestJson(`/api/activities/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    dialog.close();
    await loadActivities();
    showMessage("Report updated.");
  } catch (error) { showMessage(error.message, true); }
}
async function removeActivity(id) {
  if (!confirm(`Delete report #${id}? This cannot be undone.`)) return;
  try { await requestJson(`/api/activities/${id}`, { method: "DELETE" }); await loadActivities(); showMessage("Report deleted."); }
  catch (error) { showMessage(error.message, true); }
}
async function downloadOne(id) {
  const row = activities.find(item => item.id === id); if (!row) return;
  const date = String(row.created_at || "").slice(0, 10); const today = new Date().toISOString().slice(0, 10);
  await generateAndDownload(date || today, date || today, row.speaker_id, "pdf", id);
}
async function generateAndDownload(start, end, speakerId, format, logId = null) {
  try {
    const result = await requestJson("/api/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start_date: start, end_date: end, ...(logId ? { log_id: logId } : {}), ...(user.role === "admin" && speakerId && !logId ? { speaker_id: speakerId } : {}) }) });
    const filename = result.data[format]; const response = await fetch(`/api/reports/${format}/${encodeURIComponent(filename)}`, { headers: { Authorization: `Bearer ${sessionStorage.getItem("field_access_token")}` } });
    if (!response.ok) throw new Error("Could not download this report.");
    const link = document.createElement("a"); link.href = URL.createObjectURL(await response.blob()); link.download = filename; link.click(); URL.revokeObjectURL(link.href);
  } catch (error) { showMessage(error.message, true); }
}
async function initializeWorkspace() {
  try {
    const result = await requestJson("/api/auth/me"); user = result.data;
    if (user.role === "admin" && location.pathname !== "/admin") { location.replace("/admin"); return; }
    if (user.role !== "admin" && location.pathname === "/admin") { location.replace("/"); return; }
    document.querySelector("#accountLabel").textContent = `${user.name} · ${user.role}`;
    const speakerInput = document.querySelector("#speakerId");
    if (speakerInput) { speakerInput.value = user.worker_id; speakerInput.readOnly = true; }
    document.querySelector("#logoutButton").addEventListener("click", () => { sessionStorage.removeItem("field_access_token"); location.href = "/auth"; });
    if (user.role === "admin") {
      // Admins have a dedicated all-records dashboard.
    } else {
      const workerIdentity = document.querySelector("#workerIdentityGroup"); if (workerIdentity) workerIdentity.style.display = "block";
    }
    const refreshButton = document.querySelector("#refreshButton"); if (refreshButton) refreshButton.addEventListener("click", loadActivities);
    const closeDetails = document.querySelector("#closeDetails"); if (closeDetails) closeDetails.addEventListener("click", () => document.querySelector("#activityDialog").close());
    const editForm = document.querySelector("#adminEditForm"); if (editForm) editForm.addEventListener("submit", saveAdminEdit);
    for (const id of ["cancelEdit", "cancelEditFooter"]) { const button = document.querySelector(`#${id}`); if (button) button.addEventListener("click", () => document.querySelector("#editDialog").close()); }
    const reportType = document.querySelector("#reportType");
    if (reportType && document.querySelector("#adminMonthGroup")) reportType.addEventListener("change", () => {
      const type = reportType.value;
      document.querySelector("#adminMonthGroup").style.display = type === "monthly" ? "" : "none";
      document.querySelector("#adminYearGroup").style.display = type === "yearly" ? "" : "none";
      document.querySelector("#adminStartGroup").style.display = type === "custom" ? "" : "none";
      document.querySelector("#adminEndGroup").style.display = type === "custom" ? "" : "none";
    });
    document.querySelector("#generateReportButton").addEventListener("click", async () => {
      const type = document.querySelector("#reportType").value; let start, end;
      if (type === "monthly") { const month = document.querySelector("#reportMonth").value; if (!month) return showMessage("Choose a month.", true); start = `${month}-01`; end = new Date(Number(month.slice(0,4)), Number(month.slice(5,7)), 0).toISOString().slice(0,10); }
      else if (type === "yearly") { const year = document.querySelector("#reportYear").value; if (!year) return showMessage("Choose a year.", true); start = `${year}-01-01`; end = `${year}-12-31`; }
      else { start = document.querySelector("#startDate").value; end = document.querySelector("#endDate").value; }
      if (!start || !end) return showMessage("Choose a date range.", true);
      await generateAndDownload(start, end, null, document.querySelector("#reportFormat").value);
    });
    await loadActivities();
  } catch (error) { if (error.message) showMessage(error.message, true); }
}
document.addEventListener("DOMContentLoaded", initializeWorkspace);
