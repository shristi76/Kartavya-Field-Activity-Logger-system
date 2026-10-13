
import React, { useCallback, useEffect, useState } from "react";
import * as ImagePicker from "expo-image-picker";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import {
  ActivityIndicator,
  Alert,
  Image,
  Keyboard,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import {
  uploadAudio,
  processActivity,
  saveActivity,
  getRecentActivities,
  updateActivity,
  deleteActivity,
  uploadPhoto,
  generatePdfReport,
  getPdfDownloadUrl,
} from "@/services/api";

const COLORS = {
  primary: "#087F8C",
  primaryDark: "#075B66",
  primaryLight: "#E4F5F5",
  background: "#F4F8F9",
  white: "#FFFFFF",
  text: "#172B32",
  muted: "#71838A",
  border: "#DCE7E9",
  success: "#16865B",
  danger: "#D64545",
};

type ReportValue = string | number | boolean | null | undefined;
type ActivityReport = Record<string, ReportValue>;


type RecentActivity = {
  id?: number | string;
  speaker_id?: string;
  worker_name?: string;
  hindi_text?: string;
  translated_text?: string;
  date?: string;
  activity?: string;
  organization?: string;
  location?: string;
  village?: string;
  block?: string;
  district?: string;
  people_visited?: number | string | null;
  households_visited?: number | string | null;
  beneficiaries_assisted?: number | string | null;
  beneficiaries?: number | string | null;
  issues_identified?: string | null;
  education_related_issues?: string | null;
  health_and_wellbeing_concerns?: string | null;
  family_and_child_welfare_concerns?: string | null;
  livelihood_and_financial_issues?: string | null;
  government_scheme_and_benefit_issues?: string | null;
  elderly_and_disability_support_needs?: string | null;
  assistance_provided?: string | null;
  actions_taken?: string | null;
  referrals_made?: string | null;
  services_or_benefits_accessed?: string | null;
  referral_required?: string | null;
  follow_up_required?: string | null;
  follow_up_date?: string | null;
  responsible_person?: string | null;
  outcomes_and_progress?: string | null;
  additional_notes?: string | null;
  audio_file?: string | null;
  photo_file?: string | null;
};

type ActivityPayload = {
  speaker_id: string;
  worker_name: string;
  organization: string;
  district: string;
  hindi_text: string;
  translated_text: string;
  activity: string;
  location: string;
  beneficiaries: string;

  village?: string;
  block?: string;
  // district?: string;
  people_visited?: number | null;
  households_visited?: number | null;
  beneficiaries_assisted?: number | null;
  issues_identified?: string;
  education_related_issues?: string;
  health_and_wellbeing_concerns?: string;
  family_and_child_welfare_concerns?: string;
  livelihood_and_financial_issues?: string;
  government_scheme_and_benefit_issues?: string;
  elderly_and_disability_support_needs?: string;
  assistance_provided?: string;
  actions_taken?: string;
  referrals_made?: string;
  services_or_benefits_accessed?: string;
  referral_required?: string;
  follow_up_required?: string;
  follow_up_date?: string;
  responsible_person?: string;
  outcomes_and_progress?: string;
  additional_notes?: string;
  audio_file?: string;
  photo_file?: string;
};



function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function getActivityList(result: unknown): RecentActivity[] {
  if (!result || typeof result !== "object") return [];

  const response = result as {
    data?: unknown;
    activities?: unknown;
  };

  if (Array.isArray(response.data)) {
    return response.data as RecentActivity[];
  }

  if (Array.isArray(response.activities)) {
    return response.activities as RecentActivity[];
  }

  if (
    response.data &&
    typeof response.data === "object" &&
    "activities" in response.data
  ) {
    const nested = (response.data as { activities?: unknown }).activities;
    if (Array.isArray(nested)) return nested as RecentActivity[];
  }

  return [];
}

function SectionHeading({
  number,
  title,
  subtitle,
}: {
  number: string;
  title: string;
  subtitle: string;
}) {
  return (
    <View style={styles.sectionHeading}>
      <View style={styles.sectionNumber}>
        <Text style={styles.sectionNumberText}>{number}</Text>
      </View>
      <View style={styles.sectionHeadingText}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionSubtitle}>{subtitle}</Text>
      </View>
    </View>
  );
}

export default function HomeScreen() {
  
  const recorder = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
    android: {
      ...RecordingPresets.HIGH_QUALITY.android,
      audioSource: "voice_recognition",
    },
  });

  const recorderState = useAudioRecorderState(recorder);

  const [workerId, setWorkerId] = useState("");
  const [workerName, setWorkerName] = useState("");
  const [organization, setOrganization] = useState("");
  const [district, setDistrict] = useState("");
  const [report, setReport] = useState<ActivityReport | null>(null);
  const [transcription, setTranscription] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [activity, setActivity] = useState("");
  const [beneficiaries, setBeneficiaries] = useState("");
  const [location, setLocation] = useState("");
  const [audioFile, setAudioFile] = useState<string | null>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

  const [selectedPhotoUri, setSelectedPhotoUri] = useState<string | null>(
    null
  );
  const [uploadedPhotoFile, setUploadedPhotoFile] = useState<string | null>(
    null
  );
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);

  const [activityId, setActivityId] = useState<number | string | null>(null);
  const [editingActivityId, setEditingActivityId] = useState<
    number | string | null
  >(null);

  const [isUploading, setIsUploading] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isUpdatingActivity, setIsUpdatingActivity] = useState(false);
  const [deletingActivityId, setDeletingActivityId] = useState<
    number | string | null
  >(null);

  const [debugMessage, setDebugMessage] = useState("");
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>(
    []
  );
  const [isLoadingActivities, setIsLoadingActivities] = useState(false);
  const [isRefreshingActivities, setIsRefreshingActivities] = useState(false);
  const [activitiesError, setActivitiesError] = useState("");

  const isRecording = recorderState.isRecording;
  const isEditing = editingActivityId !== null;

  const isBusy =
    isUploading ||
    isReprocessing ||
    isSaving ||
    isUpdatingActivity ||
    isUploadingPhoto ||
    deletingActivityId !== null;

  const loadRecentActivities = useCallback(async (refresh = false) => {
    try {
      if (refresh) {
        setIsRefreshingActivities(true);
      } else {
        setIsLoadingActivities(true);
      }

      setActivitiesError("");
      const result = await getRecentActivities(20);
      setRecentActivities(getActivityList(result));
    } catch (error) {
      console.error("Load recent activities error:", error);
      setActivitiesError(
        getErrorMessage(error, "Could not load recent activities.")
      );
    } finally {
      setIsLoadingActivities(false);
      setIsRefreshingActivities(false);
    }
  }, []);

  useEffect(() => {
    void loadRecentActivities();
  }, [loadRecentActivities]);

  function resetReviewForm() {
    setReport(null);
    setTranscription("");
    setTranslatedText("");
    setActivity("");
    setBeneficiaries("");
    setLocation("");
    setAudioFile(null);
    setSelectedPhotoUri(null);
    setUploadedPhotoFile(null);
    setActivityId(null);
    setEditingActivityId(null);
  }

  async function startRecording() {
    Keyboard.dismiss();

    if (isBusy || isRecording) return;

    if (isEditing) {
      Alert.alert(
        "Finish editing first",
        "Update or cancel the activity you are editing before starting a new recording."
      );
      return;
    }

    if (!workerId.trim()) {
      Alert.alert(
        "Worker ID required",
        "Please enter your worker ID before recording."
      );
      return;
    }

    try {
      const permission = await AudioModule.requestRecordingPermissionsAsync();

      if (!permission.granted) {
        Alert.alert(
          "Microphone permission required",
          "Please allow microphone access to record an activity."
        );
        return;
      }

      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
      });

      resetReviewForm();
      setDebugMessage("");

      await recorder.prepareToRecordAsync();
      recorder.record();
      setDebugMessage("Recording in progress...");
    } catch (error) {
      console.error("Recording start error:", error);
      Alert.alert(
        "Recording error",
        getErrorMessage(error, "Could not start recording.")
      );
    }
  }

  async function stopRecording() {
    if (!isRecording || isUploading) return;

    try {
      await recorder.stop();
      const uri = recorder.uri;

      if (!uri) {
        setDebugMessage("Recording file not found.");
        Alert.alert(
          "Recording unavailable",
          "The recording file could not be found. Please try again."
        );
        return;
      }

      setIsUploading(true);
      setDebugMessage("Uploading audio and processing activity...");

      const result = await uploadAudio(uri, workerId.trim());
      const generatedReport = result.report ?? {};

      setTranscription(result.transcription ?? "");
      setAudioFile(result.audio_file ?? null);
      setActivityId(null);
      setEditingActivityId(null);
      setSelectedPhotoUri(null);
      setUploadedPhotoFile(null);

      setWorkerName(String(generatedReport.worker_name || workerName));
      setOrganization(String(generatedReport.organization || organization));
      setDistrict(String(generatedReport.district || district));
      setTranslatedText(String(generatedReport.translated_text ?? ""));
      setActivity(String(generatedReport.activity ?? ""));
      setBeneficiaries(String(generatedReport.beneficiaries ?? ""));
      setLocation(String(generatedReport.location ?? ""));

      setReport(
        generatedReport &&
          typeof generatedReport === "object" &&
          !Array.isArray(generatedReport)
          ? (generatedReport as ActivityReport)
          : {}
      );

      setDebugMessage("Recording processed successfully.");

      Alert.alert(
        "Processing complete",
        "Your transcription and activity details are ready to review."
      );
    } catch (error) {
      console.error("Recording upload error:", error);
      setDebugMessage("Could not process the recording.");

      Alert.alert(
        "Processing error",
        getErrorMessage(
          error,
          "Something went wrong while uploading the recording."
        )
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRecording() {
    if (isRecording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  }

  // Select an image from the device gallery.
  async function handleChooseImage() {
    try {
      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        Alert.alert(
          "Permission required",
          "Please allow photo library access to select an image."
        );
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: true,
        quality: 0.8,
      });

      if (result.canceled || !result.assets?.length) return;

      setSelectedPhotoUri(result.assets[0].uri);

      // The new selection has not been uploaded yet.
      setUploadedPhotoFile(null);
    } catch (error) {
      console.error("Choose image error:", error);
      Alert.alert("Error", "Could not select the image.");
    }
  }

  // Upload the selected image to the Flask API.

const handleUploadImage = async () => {
  if (!selectedPhotoUri) {
    Alert.alert("No image selected", "Please choose an image first.");
    return;
  }

  setIsUploadingPhoto(true);

  try {
    const response = await uploadPhoto(selectedPhotoUri);

    // Your Flask API returns the filename inside response.data.
    const photoPath =
      response.data?.filename ??
      response.photo_file ??
      response.filename ??
      response.file_path ??
      response.path;

    if (typeof photoPath !== "string" || !photoPath.trim()) {
      console.log(
        "Photo upload response:",
        JSON.stringify(response, null, 2)
      );

      throw new Error("The server did not return a photo filename.");
    }

    setUploadedPhotoFile(photoPath);

    Alert.alert("Success", "Photo uploaded successfully.");
  } catch (error) {
    console.error("Photo upload error:", error);

    Alert.alert(
      "Photo upload failed",
      error instanceof Error
        ? error.message
        : "An unexpected error occurred."
    );
  } finally {
    setIsUploadingPhoto(false);
  }
};
  async function handleProcessActivity() {
    Keyboard.dismiss();

    if (isBusy || (activityId !== null && !isEditing)) return;

    if (!transcription.trim()) {
      Alert.alert(
        "Transcription required",
        "Please enter the Hindi transcription first."
      );
      return;
    }

    try {
      setIsReprocessing(true);
      setDebugMessage("Processing edited transcription...");

      const result = await processActivity(transcription.trim());
      const data = result.data ?? {};

      setWorkerName(String(data.worker_name || workerName));
      setOrganization(String(data.organization || organization));
      setDistrict(String(data.district || district));
      setTranslatedText(String(data.translated_text ?? ""));
      setActivity(String(data.activity ?? ""));
      setBeneficiaries(String(data.beneficiaries ?? ""));
      setLocation(String(data.location ?? ""));

      setReport(
        data &&
          typeof data === "object" &&
          !Array.isArray(data)
          ? (data as ActivityReport)
          : {}
      );

      setDebugMessage("Activity details updated.");

      Alert.alert(
        "Updated successfully",
        "The activity details have been generated from your edited transcription. Review the fields before saving."
      );
    } catch (error) {
      console.error("Activity processing error:", error);
      setDebugMessage("Could not process the edited transcription.");

      Alert.alert(
        "Processing error",
        getErrorMessage(error, "Could not process the transcription.")
      );
    } finally {
      setIsReprocessing(false);
    }
  }

  function handleEditActivity(item: RecentActivity) {
    if (item.id === undefined || item.id === null) {
      Alert.alert("Cannot edit", "This activity has no ID.");
      return;
    }

    if (isBusy || isRecording) {
      Alert.alert(
        "Please wait",
        "Finish the current operation before editing an activity."
      );
      return;
    }

    Keyboard.dismiss();

    setEditingActivityId(item.id);
    setActivityId(item.id);
    setWorkerId(item.speaker_id ?? "");
    setWorkerName(item.worker_name ?? "");
    setOrganization(item.organization ?? "");
    setDistrict(item.district ?? "");
    setTranscription(item.hindi_text ?? "");
    setTranslatedText(item.translated_text ?? "");
    setActivity(item.activity ?? "");
    setBeneficiaries(String(item.beneficiaries ?? ""));
    setLocation(item.location ?? "");
    setAudioFile(item.audio_file ?? null);

    // Preserve the saved path. The existing image can be previewed only
    // if the backend provides a usable image URL.
    setUploadedPhotoFile(item.photo_file ?? null);
    setSelectedPhotoUri(null);

    setReport({
      hindi_text: item.hindi_text,
      translated_text: item.translated_text,
      activity: item.activity,
      beneficiaries: item.beneficiaries,
      location: item.location,
      worker_name: item.worker_name,
      organization: item.organization,
      district: item.district,
    });

    setDebugMessage(`Editing activity #${item.id}.`);

    Alert.alert(
      "Edit activity",
      `Activity #${item.id} is loaded into the Review Activity form. Make your changes and press Update Activity.`
    );
  }

  function handleCancelEdit() {
    Alert.alert(
      "Cancel editing?",
      "Your unsaved changes will be discarded.",
      [
        { text: "Continue editing", style: "cancel" },
        {
          text: "Discard changes",
          style: "destructive",
          onPress: () => {
            resetReviewForm();
            setDebugMessage("Editing cancelled.");
          },
        },
      ]
    );
  }

  async function handleUpdateActivity() {
    if (editingActivityId === null || isBusy) return;

    if (!workerId.trim()) {
      Alert.alert("Missing Worker ID", "Please enter your Worker ID.");
      return;
    }

    if (!transcription.trim()) {
      Alert.alert(
        "Missing Transcription",
        "Please enter the Hindi transcription."
      );
      return;
    }

    try {
      Keyboard.dismiss();
      setIsUpdatingActivity(true);
      setDebugMessage("Updating saved activity...");

      const payload: ActivityPayload = {
        speaker_id: workerId.trim(),
        worker_name: workerName.trim(),
        organization: organization.trim(),
        district: district.trim(),
        hindi_text: transcription.trim(),
        translated_text: translatedText.trim(),
        activity: activity.trim(),
        beneficiaries: beneficiaries.trim(),
        location: location.trim(),
        audio_file: audioFile || undefined,
        photo_file: uploadedPhotoFile || undefined,
      };

      await updateActivity(
        Number(editingActivityId),
        payload as Parameters<typeof updateActivity>[1]
      );

      const updatedId = editingActivityId;

      setEditingActivityId(null);
      setActivityId(updatedId);
      setDebugMessage("Activity updated successfully.");

      await loadRecentActivities(true);

      Alert.alert(
        "Activity updated",
        `Activity #${updatedId} was updated successfully.`
      );
    } catch (error) {
      console.error("Update activity error:", error);
      setDebugMessage("Could not update the activity.");

      Alert.alert(
        "Update failed",
        getErrorMessage(
          error,
          "Could not update this activity. Please try again."
        )
      );
    } finally {
      setIsUpdatingActivity(false);
    }
  }





  async function handleSaveActivity() {
    Keyboard.dismiss();

    if (editingActivityId !== null) {
      await handleUpdateActivity();
      return;
    }

    if (isBusy) return;

    if (activityId !== null) {
      Alert.alert(
        "Already saved",
        "This activity has already been saved. Start a new recording to create another activity."
      );
      return;
    }

    if (!workerId.trim()) {
      Alert.alert("Missing Worker ID", "Please enter your Worker ID.");
      return;
    }

    if (!transcription.trim()) {
      Alert.alert(
        "Missing Transcription",
        "Please record or enter the Hindi transcription first."
      );
      return;
    }

    try {
      setIsSaving(true);
      setDebugMessage("Saving reviewed activity...");

      const result = await saveActivity({
        speaker_id: workerId.trim(),
        worker_name: workerName.trim(),
        organization: organization.trim(),
        district: district.trim(),
        hindi_text: transcription.trim(),
        translated_text: translatedText.trim(),
        activity: activity.trim(),
        beneficiaries: beneficiaries.trim(),
        location: location.trim(),
        audio_file: audioFile || undefined,
        photo_file: uploadedPhotoFile || undefined,
      });

      const savedId = result.data?.id;

      if (savedId !== undefined && savedId !== null) {
        setActivityId(savedId);
      }

      setDebugMessage("Activity saved successfully.");
      await loadRecentActivities(true);

      Alert.alert(
        "Activity Saved",
        savedId !== undefined && savedId !== null
          ? `Your activity was saved successfully. Activity ID: ${savedId}`
          : "Your activity was saved successfully."
      );
    } catch (error) {
      console.error("Save activity error:", error);
      setDebugMessage("Could not save the activity.");

      Alert.alert(
        "Save Failed",
        getErrorMessage(
          error,
          "Could not save the activity. Please check your connection and try again."
        )
      );
    } finally {
      setIsSaving(false);
    }
  }

  function handleDeleteActivity(item: RecentActivity) {
    if (item.id === undefined || item.id === null) {
      Alert.alert("Cannot delete", "This activity has no ID.");
      return;
    }

    if (isBusy || isRecording) {
      Alert.alert(
        "Please wait",
        "Finish the current operation before deleting an activity."
      );
      return;
    }

    Alert.alert(
      "Delete activity?",
      `Are you sure you want to delete activity #${item.id}? This action cannot be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => void confirmDeleteActivity(item.id!),
        },
      ]
    );
  }

  async function confirmDeleteActivity(id: number | string) {
    try {
      setDeletingActivityId(id);
      setDebugMessage(`Deleting activity #${id}...`);

      await deleteActivity(Number(id));

      if (String(editingActivityId) === String(id)) {
        resetReviewForm();
      }

      setDebugMessage("Activity deleted successfully.");
      await loadRecentActivities(true);

      Alert.alert("Deleted", `Activity #${id} was deleted successfully.`);
    } catch (error) {
      console.error("Delete activity error:", error);

      Alert.alert(
        "Delete failed",
        getErrorMessage(
          error,
          "Could not delete this activity. Please try again."
        )
      );
    } finally {
      setDeletingActivityId(null);
    }
  }

  const meterValue =
    typeof recorderState.metering === "number"
      ? Math.max(
          0,
          Math.min(100, (recorderState.metering + 60) * (100 / 60))
        )
      : 0;

  const reviewFieldsEditable =
    !isBusy && (activityId === null || isEditing);

  const savedActivityButtonsDisabled =
    isBusy || (activityId !== null && !isEditing);

async function handleDownloadPdf() {
  if (isGeneratingPdf) return;

  if (!recentActivities.length) {
    Alert.alert(
      "No activities",
      "Save at least one activity before generating a report."
    );
    return;
  }

  try {
    setIsGeneratingPdf(true);
    Keyboard.dismiss();

    const formatDate = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };

    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);

    const result = await generatePdfReport({
      start_date: formatDate(start),
      end_date: formatDate(end),
    });

    const filename = result.data?.pdf;

    if (typeof filename !== "string" || !filename.trim()) {
      throw new Error("The server did not return a PDF filename.");
    }

    const downloadUrl = getPdfDownloadUrl(filename);
    const cacheDirectory = FileSystem.cacheDirectory;

    if (!cacheDirectory) {
      throw new Error("The device's temporary storage is unavailable.");
    }

    const localUri =
      `${cacheDirectory}activity-report-${Date.now()}.pdf`;

    const download = await FileSystem.downloadAsync(
      downloadUrl,
      localUri
    );

    if (download.status < 200 || download.status >= 300) {
      throw new Error(
        `PDF download failed with status ${download.status}.`
      );
    }

    const sharingAvailable = await Sharing.isAvailableAsync();

    if (sharingAvailable) {
      await Sharing.shareAsync(download.uri, {
        mimeType: "application/pdf",
        dialogTitle: "Save or share activity report",
        UTI: "com.adobe.pdf",
      });
    } else {
      Alert.alert(
        "PDF downloaded",
        `The PDF is available at:\n${download.uri}`
      );
    }
  } catch (error) {
    console.error("PDF report error:", error);

    Alert.alert(
      "Report download failed",
      getErrorMessage(
        error,
        "Could not generate or download the PDF report."
      )
    );
  } finally {
    setIsGeneratingPdf(false);
  }
}
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor={COLORS.background}
      />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshingActivities}
            onRefresh={() => loadRecentActivities(true)}
            tintColor={COLORS.primary}
            colors={[COLORS.primary]}
          />
        }
      >
        <View style={styles.header}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>FA</Text>
          </View>
          <View style={styles.headerTextContainer}>
            <Text style={styles.brandName}>Field Activity</Text>
            <Text style={styles.brandSubtitle}>LOGGING SYSTEM</Text>
          </View>
        </View>

        <View style={styles.hero}>
          {/* <Text style={styles.eyebrow}>FIELD OPERATIONS</Text> */}
          <Text style={styles.heroTitle}>
            Capture your{"\t"}
            <Text style={styles.heroTitle}> activities.</Text>
          </Text>
          <Text style={styles.heroDescription}>
            Record field updates in Hindi and turn them into structured
            activity reports.
          </Text>
        </View>

        {/* 01 — Worker information */}
        <View style={styles.card}>
          <SectionHeading
            number="01"
            title="Worker information"
            subtitle="Identify who is submitting this report."
          />

          <Text style={styles.fieldLabel}>WORKER ID</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter worker ID"
            placeholderTextColor="#9BAAAF"
            value={workerId}
            onChangeText={setWorkerId}
            autoCapitalize="characters"
            editable={!isRecording && !isBusy && !isEditing}
            returnKeyType="done"
          />
          <Text style={styles.helperText}>
            Use the ID assigned to the field worker.
          </Text>

        </View>

        {/* 02 — Voice recording */}
        <View style={styles.card}>
          <SectionHeading
            number="02"
            title="Voice recording"
            subtitle="Record the activity in Hindi."
          />

          <View
            style={[
              styles.recordingPanel,
              isRecording && styles.recordingPanelActive,
            ]}
          >
            <View
              style={[
                styles.micCircle,
                isRecording && styles.micCircleActive,
              ]}
            >
              <Text style={styles.micIcon}>{isRecording ? "■" : "🎙"}</Text>
            </View>

            <Text style={styles.recordingTitle}>
              {isRecording ? "Recording in progress" : "Ready to record"}
            </Text>
            <Text style={styles.recordingDescription}>
              {isRecording
                ? "Speak clearly about today's field activity."
                : "Find a quiet place and describe the work completed."}
            </Text>

            {isRecording && (
              <View style={styles.meterContainer}>
                <View
                  style={[styles.meterFill, { width: `${meterValue}%` }]}
                />
              </View>
            )}

            <TouchableOpacity
              activeOpacity={0.85}
              style={[
                styles.recordButton,
                isRecording && styles.stopButton,
                (isBusy || isEditing) && styles.disabledButton,
              ]}
              onPress={handleRecording}
              disabled={isBusy || isEditing}
            >
              <Text style={styles.recordButtonText}>
                {isRecording ? "■   Stop recording" : "●   Start recording"}
              </Text>
            </TouchableOpacity>

            {isUploading && (
              <View style={styles.loadingRow}>
                <ActivityIndicator color={COLORS.primary} />
                <Text style={styles.loadingText}>
                  Processing your recording...
                </Text>
              </View>
            )}

            {!!debugMessage && (
              <Text style={styles.statusMessage}>{debugMessage}</Text>
            )}
          </View>
        </View>

        {/* 03 — Review activity */}
        <View style={styles.card}>
          <SectionHeading
            number="03"
            title={isEditing ? `Edit activity #${editingActivityId}` : "Review activity"}
            subtitle={
              isEditing
                ? "Update the details and save your changes."
                : "Check and correct the generated information."
            }
          />

          {!report ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>✎</Text>
              <Text style={styles.emptyStateTitle}>
                No activity to review yet
              </Text>
              <Text style={styles.emptyStateDescription}>
                Record an activity to generate a Hindi transcription and
                extract the report details.
              </Text>
            </View>
          ) : (
            <>
             

              <Text style={styles.fieldLabel}>HINDI TRANSCRIPTION</Text>
              <TextInput
                style={[styles.input, styles.multilineInput]}
                placeholder="Hindi transcription will appear here..."
                placeholderTextColor="#9BAAAF"
                value={transcription}
                onChangeText={setTranscription}
                multiline
                textAlignVertical="top"
                editable={reviewFieldsEditable}
              />
              <Text style={styles.helperText}>
                Correct the transcription if necessary, then process it again
                to regenerate the activity details.
              </Text>

              <TouchableOpacity
                style={[
                  styles.secondaryButton,
                  (isBusy || (activityId !== null && !isEditing)) &&
                    styles.disabledButton,
                ]}
                activeOpacity={0.85}
                onPress={handleProcessActivity}
                disabled={isBusy || (activityId !== null && !isEditing)}
              >
                {isReprocessing ? (
                  <ActivityIndicator color={COLORS.primaryDark} />
                ) : (
                  <Text style={styles.secondaryButtonText}>
                    ↻  Process Edited Transcription
                  </Text>
                )}
              </TouchableOpacity>

              <View style={styles.fieldDivider} />

              <Text style={styles.fieldLabel}>ENGLISH TRANSLATION</Text>
              <TextInput
                style={[styles.input, styles.multilineInput]}
                placeholder="English translation"
                placeholderTextColor="#9BAAAF"
                value={translatedText}
                onChangeText={setTranslatedText}
                multiline
                textAlignVertical="top"
                editable={reviewFieldsEditable}
              />

               {/* Worker details can be added or changed while reviewing/editing. */}
              <Text style={styles.fieldLabel}>SOCIAL WORKER NAME</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter social worker name"
                placeholderTextColor="#9BAAAF"
                value={workerName}
                onChangeText={setWorkerName}
                autoCapitalize="words"
                editable={reviewFieldsEditable}
              />

              <Text style={styles.fieldLabel}>ORGANIZATION</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter organization name"
                placeholderTextColor="#9BAAAF"
                value={organization}
                onChangeText={setOrganization}
                autoCapitalize="words"
                editable={reviewFieldsEditable}
              />

              <Text style={styles.fieldLabel}>DISTRICT</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter district"
                placeholderTextColor="#9BAAAF"
                value={district}
                onChangeText={setDistrict}
                autoCapitalize="words"
                editable={reviewFieldsEditable}
              />

              <Text style={styles.fieldLabel}>ACTIVITY</Text>
              <TextInput
                style={[styles.input, styles.multilineInput]}
                placeholder="Describe the activity"
                placeholderTextColor="#9BAAAF"
                value={activity}
                onChangeText={setActivity}
                multiline
                textAlignVertical="top"
                editable={reviewFieldsEditable}
              />

              <Text style={styles.fieldLabel}>BENEFICIARIES</Text>
              <TextInput
                style={styles.input}
                placeholder="Number or description of beneficiaries"
                placeholderTextColor="#9BAAAF"
                value={beneficiaries}
                onChangeText={setBeneficiaries}
                editable={reviewFieldsEditable}
              />

              <Text style={styles.fieldLabel}>LOCATION</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter activity location"
                placeholderTextColor="#9BAAAF"
                value={location}
                onChangeText={setLocation}
                editable={reviewFieldsEditable}
              />

              {/* Activity photo — placed inside the component's JSX return */}
              <View style={styles.photoSection}>
                <Text style={styles.sectionTitle}>Activity Photo</Text>
                <Text style={styles.helperText}>
                  Select a photo related to this field activity.
                </Text>

                <TouchableOpacity
                  style={styles.photoButton}
                  onPress={handleChooseImage}
                  disabled={isBusy || !reviewFieldsEditable}
                  activeOpacity={0.85}
                >
                  <Text style={styles.photoButtonText}>
                    {selectedPhotoUri ? "Choose Another Image" : "Choose Photo"}
                  </Text>
                </TouchableOpacity>

                {selectedPhotoUri ? (
                  <Image
                    source={{ uri: selectedPhotoUri }}
                    style={styles.photoPreview}
                    resizeMode="cover"
                  />
                ) : uploadedPhotoFile ? (
                  <View style={styles.uploadedPhotoNotice}>
                    <Text style={styles.uploadedPhotoText}>
                      ✓ A photo path is attached to this activity.
                    </Text>
                    <Text style={styles.helperText}>
                      Select a new photo to replace it.
                    </Text>
                  </View>
                ) : null}

                {!!selectedPhotoUri && (
                  <TouchableOpacity
                    style={[
                      styles.photoButton,
                      styles.photoUploadButton,
                      (isUploadingPhoto || !reviewFieldsEditable) &&
                        styles.disabledButton,
                    ]}
                    onPress={handleUploadImage}
                    disabled={isUploadingPhoto || !reviewFieldsEditable}
                    activeOpacity={0.85}
                  >
                    {isUploadingPhoto ? (
                      <View style={styles.saveButtonContent}>
                        <ActivityIndicator color={COLORS.white} />
                        <Text style={styles.photoButtonText}>Uploading...</Text>
                      </View>
                    ) : (
                      <Text style={styles.photoButtonText}>
                        {uploadedPhotoFile ? "Upload Again" : "Upload Selected Photo"}
                      </Text>
                    )}
                  </TouchableOpacity>
                )}

                {!!uploadedPhotoFile && (
                  <Text style={styles.photoUploadedLabel}>
                    ✓ Photo uploaded and ready to save
                  </Text>
                )}
              </View>

              <TouchableOpacity
                style={[
                  styles.saveButton,
                  savedActivityButtonsDisabled && styles.disabledButton,
                ]}
                activeOpacity={0.85}
                onPress={handleSaveActivity}
                disabled={savedActivityButtonsDisabled}
              >
                {isSaving || isUpdatingActivity ? (
                  <View style={styles.saveButtonContent}>
                    <ActivityIndicator color={COLORS.white} />
                    <Text style={styles.saveButtonText}>
                      {isUpdatingActivity
                        ? "Updating Activity..."
                        : "Saving Activity..."}
                    </Text>
                  </View>
                ) : isEditing ? (
                  <Text style={styles.saveButtonText}>Update Activity</Text>
                ) : activityId !== null ? (
                  <Text style={styles.saveButtonText}>✓ Activity Saved</Text>
                ) : (
                  <Text style={styles.saveButtonText}>Save Activity</Text>
                )}
              </TouchableOpacity>

              {isEditing && (
                <TouchableOpacity
                  style={styles.cancelEditButton}
                  activeOpacity={0.8}
                  onPress={handleCancelEdit}
                  disabled={isBusy}
                >
                  <Text style={styles.cancelEditButtonText}>
                    Cancel Editing
                  </Text>
                </TouchableOpacity>
              )}

              <View style={styles.reviewInfo}>
                <Text style={styles.reviewInfoTitle}>
                  Recording information
                </Text>
                <Text style={styles.reviewInfoText}>
                  Worker ID: {workerId || "Not provided"}
                </Text>
                <Text style={styles.reviewInfoText}>
                  Activity ID: {activityId ?? "Not assigned"}
                </Text>
                <Text style={styles.reviewInfoText}>
                  Audio file: {audioFile ?? "Not available"}
                </Text>
                <Text style={styles.reviewInfoText}>
                  Photo file: {uploadedPhotoFile ?? "Not uploaded"}
                </Text>
              </View>

              <View style={styles.reviewNotice}>
                <Text style={styles.reviewNoticeText}>
                  {isEditing
                    ? "You are editing a saved activity. Update Activity saves changes to that existing record."
                    : "Review all details before saving. Uploaded photos are attached to the activity when you save it."}
                </Text>
              </View>
            </>
          )}
        </View>

        {/* 04 — Recent activities */}
        <View style={styles.card}>
          <SectionHeading
            number="04"
            title="Recent activities"
            subtitle="View your latest saved field reports."
          />

          {isLoadingActivities && recentActivities.length === 0 ? (
            <View style={styles.historyLoading}>
              <ActivityIndicator color={COLORS.primary} />
              <Text style={styles.historyMessage}>
                Loading recent activities...
              </Text>
            </View>
          ) : activitiesError && recentActivities.length === 0 ? (
            <View style={styles.historyEmpty}>
              <Text style={styles.historyEmptyTitle}>
                Could not load activities
              </Text>
              <Text style={styles.historyMessage}>{activitiesError}</Text>
              <TouchableOpacity
                style={styles.historyRetryButton}
                onPress={() => loadRecentActivities()}
                activeOpacity={0.8}
              >
                <Text style={styles.historyRetryText}>Try again</Text>
              </TouchableOpacity>
            </View>
          ) : recentActivities.length === 0 ? (
            <View style={styles.historyEmpty}>
              <Text style={styles.comingSoonIcon}>▤</Text>
              <Text style={styles.historyEmptyTitle}>
                No saved activities yet
              </Text>
              <Text style={styles.historyMessage}>
                Your saved field reports will appear here.
              </Text>
            </View>
          ) : (
            <View style={styles.historyList}>
              {recentActivities.map((item, index) => (
                <View
                  key={String(item.id ?? `activity-${index}`)}
                  style={styles.historyItem}
                >
                  <View style={styles.historyItemTop}>
                    <View style={styles.historyItemIcon}>
                      <Text style={styles.historyItemIconText}>✓</Text>
                    </View>
                    <View style={styles.historyItemHeading}>
                      <Text style={styles.historyItemTitle}>
                        Activity #{item.id ?? "—"}
                      </Text>
                      <Text style={styles.historyWorker}>
                        Worker ID: {item.speaker_id || "—"}
                      </Text>
                      {!!item.worker_name && (
                        <Text style={styles.historyWorker}>
                          Social Worker: {item.worker_name}
                        </Text>
                      )}
                      {!!item.organization && (
                        <Text style={styles.historyWorker}>
                          Organization: {item.organization}
                        </Text>
                      )}
                      {!!item.district && (
                        <Text style={styles.historyWorker}>
                          District: {item.district}
                        </Text>
                      )}
                    </View>
                  </View>

                  <Text style={styles.historyLabel}>ACTIVITY</Text>
                  <Text style={styles.historyValue}>
                    {item.activity || "No activity description"}
                  </Text>

                  <View style={styles.historyDivider} />

                  <Text style={styles.historyLabel}>LOCATION</Text>
                  <Text style={styles.historyValue}>
                    {item.location || "Not specified"}
                  </Text>

                  <Text style={styles.historyLabel}>BENEFICIARIES</Text>
                  <Text style={styles.historyValue}>
                    {item.beneficiaries !== null &&
                    item.beneficiaries !== undefined &&
                    String(item.beneficiaries).trim() !== ""
                      ? String(item.beneficiaries)
                      : "Not specified"}
                  </Text>

                  {!!item.translated_text && (
                    <>
                      <Text style={styles.historyLabel}>
                        ENGLISH TRANSLATION
                      </Text>
                      <Text style={styles.historyValue}>
                        {item.translated_text}
                      </Text>
                    </>
                  )}

                  {!!item.hindi_text && (
                    <View style={styles.historyHindi}>
                      <Text style={styles.historyLabel}>
                        HINDI TRANSCRIPTION
                      </Text>
                      <Text style={styles.historyValue}>
                        {item.hindi_text}
                      </Text>
                    </View>
                  )}

                  {!!item.photo_file && (
                    <Text style={styles.photoUploadedLabel}>
                      ✓ Photo attached
                    </Text>
                  )}

                  <View style={styles.historyActions}>
                    <TouchableOpacity
                      style={[
                        styles.editButton,
                        (isBusy || isRecording || item.id == null) &&
                          styles.disabledButton,
                      ]}
                      activeOpacity={0.8}
                      disabled={isBusy || isRecording || item.id == null}
                      onPress={() => handleEditActivity(item)}
                    >
                      <Text style={styles.editButtonText}>✎ Edit</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[
                        styles.deleteButton,
                        (isBusy || isRecording || item.id == null) &&
                          styles.disabledButton,
                      ]}
                      activeOpacity={0.8}
                      disabled={isBusy || isRecording || item.id == null}
                      onPress={() => handleDeleteActivity(item)}
                    >
                      {String(deletingActivityId) === String(item.id) ? (
                        <ActivityIndicator
                          color={COLORS.danger}
                          size="small"
                        />
                      ) : (
                        <Text style={styles.deleteButtonText}>Delete</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </View>
          )}

          <TouchableOpacity
            style={[
              styles.historyRefreshButton,
              isRefreshingActivities && styles.disabledButton,
            ]}
            onPress={() => loadRecentActivities(true)}
            disabled={isRefreshingActivities}
            activeOpacity={0.8}
          >
            <Text style={styles.historyRefreshText}>
              ↻  Refresh activities
            </Text>
          </TouchableOpacity>
        </View>

        {/* 05 — Reports */}
<View style={styles.card}>
  <SectionHeading
    number="05"
    title="Reports"
    subtitle="Generate and download your field activity report."
  />

  <View style={styles.comingSoon}>
    <Text style={styles.comingSoonIcon}>⇩</Text>

    <View style={styles.comingSoonContent}>
      <Text style={styles.comingSoonTitle}>
        PDF Activity Report
      </Text>

      <Text style={styles.comingSoonDescription}>
        Generate a report containing all workers' records
        from the last 30 days.
      </Text>
    </View>
  </View>

  <TouchableOpacity
    style={[
      styles.saveButton,
      isGeneratingPdf && styles.disabledButton,
    ]}
    onPress={handleDownloadPdf}
    disabled={isGeneratingPdf}
    activeOpacity={0.85}
  >
    {isGeneratingPdf ? (
      <View style={styles.saveButtonContent}>
        <ActivityIndicator color={COLORS.white} />
        <Text style={styles.saveButtonText}>
          Generating PDF...
        </Text>
      </View>
    ) : (
      <Text style={styles.saveButtonText}>
        ↓  Download PDF Report
      </Text>
    )}
  </TouchableOpacity>
</View>

        <View style={styles.footer}>
          <Text style={styles.footerTitle}>
            FIELD ACTIVITY LOGGING SYSTEM
          </Text>
          <Text style={styles.footerDescription}>
            Structured reporting for field operations.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 40,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 28,
    marginTop: 20,
  },
  logo: {
    width: 45,
    height: 45,
    borderRadius: 14,
    backgroundColor: COLORS.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: {
    color: COLORS.white,
    fontSize: 17,
    fontWeight: "900",
  },
  headerTextContainer: {
    marginLeft: 11,
    flex: 1,
  },
  brandName: {
    color: COLORS.text,
    fontSize: 17,
    fontWeight: "800",
  },
  brandSubtitle: {
    marginTop: 3,
    color: COLORS.muted,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  hero: {
    marginBottom: 25,
  },
  eyebrow: {
    color: COLORS.primary,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 2,
    marginBottom: 12,
  },
  heroTitle: {
    color: COLORS.text,
    fontSize: 34,
    lineHeight: 42,
    fontWeight: "900",
    letterSpacing: -1,
  },
  heroTitleAccent: {
    color: COLORS.primary,
  },
  heroDescription: {
    marginTop: 12,
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 22,
    maxWidth: 330,
  },
  card: {
    padding: 18,
    backgroundColor: COLORS.white,
    borderRadius: 16,
    marginBottom: 17,
    borderWidth: 1,
    borderColor: "#E8EFF0",
    shadowColor: "#18363D",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.04,
    shadowRadius: 9,
    elevation: 2,
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 21,
  },
  sectionNumber: {
    width: 34,
    height: 34,
    borderRadius: 11,
    backgroundColor: COLORS.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 11,
  },
  sectionNumberText: {
    color: COLORS.primaryDark,
    fontSize: 11,
    fontWeight: "900",
  },
  sectionHeadingText: {
    flex: 1,
  },
  sectionTitle: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: "800",
  },
  sectionSubtitle: {
    marginTop: 5,
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 17,
  },
  fieldLabel: {
    color: COLORS.text,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1,
    marginBottom: 9,
    marginTop: 17,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 13,
    paddingVertical: 12,
    color: COLORS.text,
    backgroundColor: "#FCFDFD",
    fontSize: 13,
  },
  multilineInput: {
    minHeight: 95,
    paddingTop: 12,
    paddingBottom: 12,
    textAlignVertical: "top",
  },
  helperText: {
    color: COLORS.muted,
    fontSize: 10,
    lineHeight: 16,
    marginTop: 7,
  },
  recordingPanel: {
    padding: 20,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: "#FAFCFC",
    alignItems: "center",
  },
  recordingPanelActive: {
    borderColor: "#E8A5A5",
    backgroundColor: "#FFF9F9",
  },
  micCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: COLORS.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 15,
  },
  micCircleActive: {
    backgroundColor: "#FCE9E9",
  },
  micIcon: {
    fontSize: 25,
    color: COLORS.primaryDark,
  },
  recordingTitle: {
    color: COLORS.text,
    fontSize: 15,
    fontWeight: "800",
  },
  recordingDescription: {
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 18,
    textAlign: "center",
    marginTop: 7,
    marginBottom: 18,
  },
  meterContainer: {
    width: "100%",
    height: 5,
    borderRadius: 4,
    backgroundColor: "#F2DADA",
    overflow: "hidden",
    marginBottom: 17,
  },
  meterFill: {
    height: "100%",
    borderRadius: 4,
    backgroundColor: COLORS.danger,
  },
  recordButton: {
    width: "100%",
    minHeight: 49,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  stopButton: {
    backgroundColor: COLORS.danger,
  },
  disabledButton: {
    opacity: 0.55,
  },
  recordButtonText: {
    color: COLORS.white,
    fontSize: 13,
    fontWeight: "800",
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 15,
    gap: 9,
  },
  loadingText: {
    color: COLORS.muted,
    fontSize: 11,
  },
  statusMessage: {
    marginTop: 13,
    color: COLORS.muted,
    fontSize: 10,
    textAlign: "center",
    lineHeight: 16,
  },
  emptyState: {
    paddingHorizontal: 12,
    paddingVertical: 24,
    alignItems: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: COLORS.border,
    backgroundColor: "#FCFDFD",
  },
  emptyStateIcon: {
    fontSize: 30,
    color: COLORS.primary,
    marginBottom: 12,
  },
  emptyStateTitle: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: "800",
    textAlign: "center",
  },
  emptyStateDescription: {
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 18,
    textAlign: "center",
    marginTop: 7,
  },
  secondaryButton: {
    minHeight: 47,
    borderWidth: 1,
    borderColor: COLORS.primary,
    borderRadius: 10,
    backgroundColor: COLORS.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
    marginTop: 13,
  },
  secondaryButtonText: {
    color: COLORS.primaryDark,
    fontSize: 12,
    fontWeight: "800",
    textAlign: "center",
  },
  fieldDivider: {
    height: 1,
    backgroundColor: COLORS.border,
    marginTop: 23,
  },
  photoSection: {
    marginTop: 22,
    padding: 14,
    borderRadius: 12,
    backgroundColor: "#F5F9F9",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  photoButton: {
    backgroundColor: COLORS.primaryDark,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
    minHeight: 44,
  },
  photoUploadButton: {
    backgroundColor: COLORS.primary,
  },
  photoButtonText: {
    color: COLORS.white,
    fontSize: 12,
    fontWeight: "700",
  },
  photoPreview: {
    width: "100%",
    height: 200,
    borderRadius: 10,
    marginTop: 12,
    backgroundColor: COLORS.border,
  },
  uploadedPhotoNotice: {
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    backgroundColor: COLORS.white,
  },
  uploadedPhotoText: {
    color: COLORS.success,
    fontSize: 12,
    fontWeight: "700",
  },
  photoUploadedLabel: {
    marginTop: 10,
    color: COLORS.success,
    fontSize: 11,
    fontWeight: "700",
  },
  saveButton: {
    minHeight: 50,
    backgroundColor: COLORS.primary,
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
  },
  saveButtonContent: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  saveButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: "800",
    textAlign: "center",
  },
  cancelEditButton: {
    minHeight: 44,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.white,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
    paddingHorizontal: 12,
  },
  cancelEditButtonText: {
    color: COLORS.muted,
    fontSize: 12,
    fontWeight: "800",
  },
  reviewInfo: {
    marginTop: 21,
    padding: 13,
    backgroundColor: "#F5F9F9",
    borderRadius: 10,
    gap: 7,
  },
  reviewInfoTitle: {
    color: COLORS.text,
    fontSize: 12,
    fontWeight: "800",
    marginBottom: 3,
  },
  reviewInfoText: {
    color: COLORS.muted,
    fontSize: 10,
    lineHeight: 16,
  },
  reviewNotice: {
    marginTop: 12,
    padding: 12,
    borderRadius: 9,
    backgroundColor: "#EAF7F1",
  },
  reviewNoticeText: {
    color: "#21694D",
    fontSize: 10,
    lineHeight: 17,
  },
  historyLoading: {
    paddingVertical: 24,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  historyMessage: {
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 18,
    textAlign: "center",
    marginTop: 6,
  },
  historyEmpty: {
    padding: 20,
    alignItems: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: COLORS.border,
    backgroundColor: "#FCFDFD",
  },
  historyEmptyTitle: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: "800",
    textAlign: "center",
    marginTop: 8,
  },
  historyRetryButton: {
    marginTop: 14,
    backgroundColor: COLORS.primaryLight,
    borderRadius: 9,
    paddingVertical: 10,
    paddingHorizontal: 18,
  },
  historyRetryText: {
    color: COLORS.primaryDark,
    fontSize: 12,
    fontWeight: "800",
  },
  historyList: {
    gap: 13,
  },
  historyItem: {
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    backgroundColor: "#FCFDFD",
  },
  historyItemTop: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  historyItemIcon: {
    width: 35,
    height: 35,
    borderRadius: 11,
    backgroundColor: COLORS.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  historyItemIconText: {
    color: COLORS.primaryDark,
    fontSize: 16,
    fontWeight: "900",
  },
  historyItemHeading: {
    flex: 1,
  },
  historyItemTitle: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: "800",
  },
  historyWorker: {
    color: COLORS.muted,
    fontSize: 10,
    marginTop: 4,
  },
  historyLabel: {
    color: COLORS.primaryDark,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.8,
    marginTop: 10,
    marginBottom: 5,
  },
  historyValue: {
    color: COLORS.text,
    fontSize: 11,
    lineHeight: 18,
  },
  historyDivider: {
    height: 1,
    backgroundColor: COLORS.border,
    marginTop: 12,
  },
  historyHindi: {
    marginTop: 8,
    padding: 10,
    borderRadius: 8,
    backgroundColor: COLORS.primaryLight,
  },
  historyActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  editButton: {
    flex: 1,
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: COLORS.primaryLight,
    borderWidth: 1,
    borderColor: COLORS.primary,
    borderRadius: 9,
    paddingHorizontal: 12,
  },
  editButtonText: {
    color: COLORS.primaryDark,
    fontSize: 12,
    fontWeight: "800",
  },
  deleteButton: {
    flex: 1,
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFF1F1",
    borderWidth: 1,
    borderColor: "#F0CACA",
    borderRadius: 9,
    paddingHorizontal: 12,
  },
  deleteButtonText: {
    color: COLORS.danger,
    fontSize: 12,
    fontWeight: "800",
  },
  historyRefreshButton: {
    marginTop: 15,
    minHeight: 43,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: COLORS.primary,
    borderRadius: 10,
  },
  historyRefreshText: {
    color: COLORS.primaryDark,
    fontSize: 12,
    fontWeight: "800",
  },
  comingSoon: {
    flexDirection: "row",
    alignItems: "center",
    padding: 14,
    backgroundColor: "#F7FAFA",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#EAF0F1",
  },
  comingSoonIcon: {
    fontSize: 25,
    color: COLORS.primary,
    marginRight: 13,
  },
  comingSoonContent: {
    flex: 1,
  },
  comingSoonTitle: {
    color: COLORS.text,
    fontSize: 12,
    fontWeight: "800",
  },
  comingSoonDescription: {
    color: COLORS.muted,
    fontSize: 10,
    lineHeight: 17,
    marginTop: 5,
  },
  footer: {
    alignItems: "center",
    paddingTop: 10,
    paddingBottom: 0,
  },
  footerTitle: {
    color: COLORS.primaryDark,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  footerDescription: {
    color: COLORS.muted,
    fontSize: 10,
    marginTop: 3,
  },
});