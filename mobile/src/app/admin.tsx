import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { router } from "expo-router";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import {
  createAdminActivity,
  deleteActivity,
  downloadPdfReport,
  generatePdfReport,
  getAdminActivities,
  getAdminWorkers,
  getCurrentUser,
  setAccessToken,
  updateActivity,
} from "../services/api";

type Report = {
  id: number;
  created_at?: string;
  speaker_id?: string;
  worker_name?: string;
  organization?: string;
  district?: string;
  hindi_text?: string;
  translated_text?: string;
  activity?: string;
  beneficiaries?: string;
  location?: string;
  audio_file?: string | null;
  photo_file?: string | null;
};
type Worker = {
  id: number;
  worker_id: string;
  name: string;
  organization: string;
};
type Draft = {
  speaker_id: string;
  worker_name: string;
  organization: string;
  district: string;
  hindi_text: string;
  translated_text: string;
  activity: string;
  beneficiaries: string;
  location: string;
};
const emptyDraft: Draft = {
  speaker_id: "",
  worker_name: "",
  organization: "",
  district: "",
  hindi_text: "",
  translated_text: "",
  activity: "",
  beneficiaries: "",
  location: "",
};
const COLORS = {
  primary: "#087F8C",
  primaryDark: "#075B66",
  text: "#172B32",
  muted: "#71838A",
  border: "#DCE7E9",
  danger: "#D64545",
};

export default function AdminScreen() {
  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reports, setReports] = useState<Report[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [selected, setSelected] = useState<Report | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const account = await getCurrentUser();
      if (account.data?.role !== "admin") {
        router.replace("/");
        return;
      }
      setAuthorized(true);
      const [reportResult, workerResult] = await Promise.all([
        getAdminActivities(),
        getAdminWorkers(),
      ]);
      setReports(reportResult.data || []);
      setWorkers(workerResult.data || []);
    } catch {
      await setAccessToken(null);
      router.replace("/login");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  async function logout() {
    await setAccessToken(null);
    router.replace("/login");
  }

  function createForWorker(worker: Worker) {
    setSelected(null);
    setDraft({
      ...emptyDraft,
      speaker_id: worker.worker_id,
      worker_name: worker.name,
      organization: worker.organization || "",
    });
    setModal("create");
  }

  function editReport(report: Report) {
    setSelected(report);
    setDraft({
      speaker_id: report.speaker_id || "",
      worker_name: report.worker_name || "",
      organization: report.organization || "",
      district: report.district || "",
      hindi_text: report.hindi_text || "",
      translated_text: report.translated_text || "",
      activity: report.activity || "",
      beneficiaries: report.beneficiaries || "",
      location: report.location || "",
    });
    setModal("edit");
  }

  async function saveReport() {
    if (!draft.speaker_id.trim() || !draft.hindi_text.trim()) {
      Alert.alert(
        "Missing information",
        "Worker ID and Hindi transcription are required.",
      );
      return;
    }
    try {
      setSaving(true);
      if (modal === "create") {
        await createAdminActivity(draft);
      } else if (selected) {
        await updateActivity(selected.id, draft);
      }
      setModal(null);
      await loadWorkspace();
      Alert.alert(
        "Saved",
        modal === "create"
          ? "Report created for the worker."
          : "Report updated.",
      );
    } catch (error) {
      Alert.alert(
        "Could not save report",
        error instanceof Error ? error.message : "Please try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  function confirmDelete(report: Report) {
    Alert.alert(
      "Delete report?",
      `Delete report #${report.id} for ${report.worker_name || report.speaker_id}?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => void removeReport(report),
        },
      ],
    );
  }

  async function removeReport(report: Report) {
    try {
      setBusyId(report.id);
      await deleteActivity(report.id);
      setReports((current) => current.filter((item) => item.id !== report.id));
    } catch (error) {
      Alert.alert(
        "Could not delete report",
        error instanceof Error ? error.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function downloadReport(report: Report) {
    try {
      setBusyId(report.id);
      const reportDate = String(
        report.created_at || new Date().toISOString(),
      ).slice(0, 10);
      const generated = await generatePdfReport({
        start_date: reportDate,
        end_date: reportDate,
        log_id: report.id,
      });
      const filename = generated.data?.pdf;
      if (!filename) throw new Error("The server did not return a PDF file.");
      const destination = `${FileSystem.cacheDirectory}field-report-${report.id}.pdf`;
      const download = await downloadPdfReport(filename, destination);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(download.uri, {
          mimeType: "application/pdf",
          dialogTitle: `Report #${report.id}`,
        });
      } else {
        Alert.alert("PDF downloaded", `Saved to ${download.uri}`);
      }
    } catch (error) {
      Alert.alert(
        "Download failed",
        error instanceof Error ? error.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
    }
  }

  function field(label: string, key: keyof Draft, multiline = false) {
    return (
      <View style={styles.formField} key={key}>
        <Text style={styles.formLabel}>{label}</Text>
        <TextInput
          value={draft[key]}
          onChangeText={(value) =>
            setDraft((current) => ({ ...current, [key]: value }))
          }
          style={[styles.input, multiline && styles.multiline]}
          multiline={multiline}
          textAlignVertical={multiline ? "top" : "center"}
          placeholder={label}
        />
      </View>
    );
  }

  if (loading || !authorized)
    return (
      <SafeAreaView style={styles.safe}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </SafeAreaView>
    );

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>ADMINISTRATOR</Text>
            <Text style={styles.title}>All worker reports</Text>
            <Text style={styles.subtitle}>
              View and manage records across every worker account.
            </Text>
          </View>
          <TouchableOpacity style={styles.logout} onPress={logout}>
            <Text style={styles.logoutText}>Sign out</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statLabel}>All reports</Text>
            <Text style={styles.statValue}>{reports.length}</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statLabel}>Workers</Text>
            <Text style={styles.statValue}>{workers.length}</Text>
          </View>
        </View>
{/* 
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <View>
              <Text style={styles.sectionTitle}>Create a report</Text>
              <Text style={styles.sectionHint}>
                Select the worker the report belongs to.
              </Text>
            </View>
          </View>
          {workers.length === 0 ? (
            <Text style={styles.empty}>
              No worker accounts are registered yet.
            </Text>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.workerList}
            >
              {workers.map((worker) => (
                <TouchableOpacity
                  key={worker.id}
                  style={styles.workerChip}
                  onPress={() => createForWorker(worker)}
                >
                  <Text style={styles.workerChipName}>{worker.name}</Text>
                  <Text style={styles.workerChipId}>{worker.worker_id}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          )}
        </View> */}

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <View>
              <Text style={styles.sectionTitle}>Every report</Text>
              <Text style={styles.sectionHint}>
                Open, edit, download, or delete any worker record.
              </Text>
            </View>
            <TouchableOpacity onPress={() => void loadWorkspace()}>
              <Text style={styles.refresh}>Refresh</Text>
            </TouchableOpacity>
          </View>
          {reports.length === 0 ? (
            <Text style={styles.empty}>No reports found.</Text>
          ) : (
            reports.map((report) => (
              <View key={report.id} style={styles.reportCard}>
                <View style={styles.reportHeading}>
                  <View style={styles.flex}>
                    <Text style={styles.reportTitle}>Report #{report.id}</Text>
                    <Text style={styles.reportMeta}>
                      {report.worker_name || "Worker"} ·{" "}
                      {report.speaker_id || "—"}
                    </Text>
                    <Text style={styles.reportMeta}>
                      {report.organization || "Organisation not set"} ·{" "}
                      {report.created_at || "Date not set"}
                    </Text>
                  </View>
                  <Text style={styles.badge}>WORKER</Text>
                </View>
                <Text style={styles.reportActivity}>
                  {report.activity ||
                    report.translated_text ||
                    "No activity description"}
                </Text>
                <Text style={styles.reportMeta}>
                  Location: {report.location || "—"} · Beneficiaries:{" "}
                  {report.beneficiaries || "—"}
                </Text>
                <Text style={styles.reportBodyLabel}>Hindi transcription</Text>
                <Text style={styles.reportBody}>
                  {report.hindi_text || "—"}
                </Text>
                {!!report.translated_text && (
                  <>
                    <Text style={styles.reportBodyLabel}>
                      English translation
                    </Text>
                    <Text style={styles.reportBody}>
                      {report.translated_text}
                    </Text>
                  </>
                )}
                <View style={styles.actions}>
                  <TouchableOpacity
                    style={styles.editButton}
                    onPress={() => editReport(report)}
                  >
                    <Text style={styles.editText}>Edit</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.downloadButton}
                    disabled={busyId === report.id}
                    onPress={() => void downloadReport(report)}
                  >
                    <Text style={styles.downloadText}>
                      {busyId === report.id ? "Working…" : "Download PDF"}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.deleteButton}
                    disabled={busyId === report.id}
                    onPress={() => confirmDelete(report)}
                  >
                    <Text style={styles.deleteText}>Delete</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      <Modal
        visible={modal !== null}
        animationType="slide"
        onRequestClose={() => setModal(null)}
      >
        <SafeAreaView style={styles.modalSafe}>
          <ScrollView contentContainerStyle={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.eyebrow}>
                  {modal === "create"
                    ? "NEW REPORT"
                    : `EDIT REPORT #${selected?.id}`}
                </Text>
                <Text style={styles.modalTitle}>
                  {modal === "create" ? "Create report" : "Update report"}
                </Text>
              </View>
              <TouchableOpacity onPress={() => setModal(null)}>
                <Text style={styles.refresh}>Cancel</Text>
              </TouchableOpacity>
            </View>
            {modal === "create" && (
              <>
                <Text style={styles.formLabel}>Worker account</Text>
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.workerList}
                >
                  {workers.map((worker) => (
                    <TouchableOpacity
                      key={worker.id}
                      style={[
                        styles.workerChip,
                        draft.speaker_id === worker.worker_id &&
                          styles.workerChipSelected,
                      ]}
                      onPress={() =>
                        setDraft((current) => ({
                          ...current,
                          speaker_id: worker.worker_id,
                          worker_name: worker.name,
                          organization: worker.organization || "",
                        }))
                      }
                    >
                      <Text style={styles.workerChipName}>{worker.name}</Text>
                      <Text style={styles.workerChipId}>
                        {worker.worker_id}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </>
            )}
            {field("Worker ID", "speaker_id")}
            {field("Worker name", "worker_name")}
            {field("Organisation", "organization")}
            {field("District", "district")}
            {field("Hindi transcription", "hindi_text", true)}
            {field("English translation", "translated_text", true)}
            {field("Activity", "activity", true)}
            {field("Beneficiaries", "beneficiaries")}
            {field("Location", "location")}
            <TouchableOpacity
              style={[styles.saveButton, saving && styles.disabled]}
              onPress={() => void saveReport()}
              disabled={saving}
            >
              <Text style={styles.saveText}>
                {saving
                  ? "Saving…"
                  : modal === "create"
                    ? "Create report"
                    : "Save changes"}
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F3F7F8" },
  container: { padding: 18, paddingBottom: 40 },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
    marginTop: 14,
    marginBottom: 18,
  },
  eyebrow: {
    color: COLORS.primary,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.7,
  },
  title: { color: COLORS.text, fontSize: 27, fontWeight: "900", marginTop: 5 },
  subtitle: {
    color: COLORS.muted,
    fontSize: 13,
    lineHeight: 19,
    marginTop: 5,
    maxWidth: 280,
  },
  logout: {
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  logoutText: { color: COLORS.primaryDark, fontWeight: "800", fontSize: 12 },
  statsRow: { flexDirection: "row", gap: 12, marginBottom: 16 },
  stat: {
    flex: 1,
    padding: 16,
    borderRadius: 14,
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  statLabel: { fontSize: 12, color: COLORS.muted },
  statValue: {
    fontSize: 24,
    fontWeight: "900",
    color: COLORS.text,
    marginTop: 3,
  },
  section: {
    padding: 16,
    backgroundColor: "white",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 13,
  },
  sectionTitle: { fontSize: 17, color: COLORS.text, fontWeight: "800" },
  sectionHint: { color: COLORS.muted, fontSize: 12, marginTop: 3 },
  refresh: { color: COLORS.primary, fontWeight: "800", fontSize: 13 },
  empty: { paddingVertical: 18, color: COLORS.muted, textAlign: "center" },
  workerList: { gap: 10, paddingVertical: 3 },
  workerChip: {
    backgroundColor: "#F4F8F9",
    borderColor: COLORS.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 11,
    minWidth: 108,
  },
  workerChipSelected: {
    borderColor: COLORS.primary,
    backgroundColor: "#E7F5F4",
  },
  workerChipName: { color: COLORS.text, fontSize: 12, fontWeight: "800" },
  workerChipId: { color: COLORS.muted, fontSize: 11, marginTop: 3 },
  reportCard: {
    backgroundColor: "#FBFDFD",
    borderRadius: 13,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 14,
    marginTop: 11,
  },
  reportHeading: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  flex: { flex: 1 },
  reportTitle: { fontSize: 15, color: COLORS.text, fontWeight: "900" },
  reportMeta: {
    fontSize: 11,
    lineHeight: 17,
    color: COLORS.muted,
    marginTop: 3,
  },
  badge: {
    color: COLORS.primaryDark,
    backgroundColor: "#E4F5F5",
    overflow: "hidden",
    paddingVertical: 5,
    paddingHorizontal: 8,
    fontSize: 9,
    fontWeight: "900",
    borderRadius: 8,
  },
  reportActivity: {
    fontSize: 14,
    color: COLORS.text,
    fontWeight: "700",
    marginTop: 12,
  },
  reportBodyLabel: {
    color: COLORS.muted,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1,
    marginTop: 12,
  },
  reportBody: {
    color: COLORS.text,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 4,
  },
  actions: { flexDirection: "row", gap: 8, marginTop: 15 },
  editButton: {
    flex: 1,
    alignItems: "center",
    padding: 10,
    borderRadius: 9,
    backgroundColor: "#EDF3F5",
  },
  editText: { color: COLORS.text, fontWeight: "800", fontSize: 12 },
  downloadButton: {
    flex: 1.5,
    alignItems: "center",
    padding: 10,
    borderRadius: 9,
    backgroundColor: COLORS.primary,
  },
  downloadText: { color: "white", fontWeight: "800", fontSize: 12 },
  deleteButton: {
    flex: 1,
    alignItems: "center",
    padding: 10,
    borderRadius: 9,
    backgroundColor: "#FFF0ED",
  },
  deleteText: { color: COLORS.danger, fontWeight: "800", fontSize: 12 },
  modalSafe: { flex: 1, backgroundColor: "#F3F7F8" },
  modalContent: { padding: 20, paddingBottom: 40 },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 12,
  },
  modalTitle: {
    color: COLORS.text,
    fontSize: 23,
    fontWeight: "900",
    marginTop: 4,
  },
  formField: { marginTop: 15 },
  formLabel: {
    color: COLORS.text,
    fontWeight: "800",
    fontSize: 12,
    marginBottom: 6,
  },
  input: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: COLORS.border,
    fontSize: 14,
    color: COLORS.text,
  },
  multiline: { minHeight: 82 },
  saveButton: {
    marginTop: 22,
    alignItems: "center",
    padding: 15,
    backgroundColor: COLORS.primary,
    borderRadius: 11,
  },
  saveText: { color: "white", fontWeight: "900" },
  disabled: { opacity: 0.55 },
});
