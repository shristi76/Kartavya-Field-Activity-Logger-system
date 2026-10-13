
import React, { useEffect, useState } from "react";
import {
  Alert,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { router } from "expo-router";
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import { Colors } from "../constants/colors";
import { uploadAudio } from "../services/api";
import { saveReport } from "../services/storage";

export default function RecordScreen() {
  // AUDIO RECORDER
  const recorder = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
    android: {
      ...RecordingPresets.HIGH_QUALITY.android,
      audioSource: "mic",
    },
  });

  // Update recording status every 500 ms
  const recorderState = useAudioRecorderState(recorder, 500);

  const [processing, setProcessing] = useState(false);

  // MICROPHONE SETUP
  useEffect(() => {
    async function setupAudio() {
      try {
        const permission =
          await AudioModule.requestRecordingPermissionsAsync();

        if (!permission.granted) {
          Alert.alert(
            "Microphone Permission",
            "Please allow microphone access to record your field activity."
          );
          return;
        }

        await setAudioModeAsync({
          playsInSilentMode: true,
          allowsRecording: true,
        });

        console.log("Microphone permission granted");
        console.log("Audio mode configured");
      } catch (error) {
        console.error("Audio setup error:", error);
        Alert.alert("Audio Error", "Could not configure the microphone.");
      }
    }

    setupAudio();
  }, []);

  // START RECORDING
  async function startRecording() {
    try {
      const permission =
        await AudioModule.requestRecordingPermissionsAsync();

      if (!permission.granted) {
        Alert.alert(
          "Permission Required",
          "Please allow microphone access to record."
        );
        return;
      }

      await setAudioModeAsync({
        playsInSilentMode: true,
        allowsRecording: true,
      });

      await recorder.prepareToRecordAsync();
      recorder.record();

      console.log("Recording started");
    } catch (error) {
      console.error("Start recording error:", error);
      Alert.alert("Recording Error", "Could not start recording.");
    }
  }

  // STOP RECORDING
  async function stopRecording() {
    try {
      console.log("Stopping recording...");
      await recorder.stop();

      const uri = recorder.uri;

      if (!uri) {
        Alert.alert("Error", "Recording file was not created.");
        return;
      }

      console.log("Recording URI:", uri);
      console.log(
        "Recording duration:",
        recorderState.durationMillis,
        "ms"
      );

      await setAudioModeAsync({
        playsInSilentMode: true,
        allowsRecording: false,
      });

      await processRecording(uri);
    } catch (error) {
      console.error("Stop recording error:", error);
      Alert.alert("Recording Error", "Could not stop recording.");
    }
  }

  // PROCESS AND UPLOAD AUDIO
  async function processRecording(uri: string) {
    try {
      setProcessing(true);

      console.log("Uploading recording...");

      const result = await uploadAudio(uri, "mobile_worker");

      console.log("Upload result:", result);

      if (!result?.success) {
        throw new Error(
          result?.message || "Could not generate report."
        );
      }

      await saveReport(result.report);

      router.replace({
        pathname: "/report",
        params: {
          report: JSON.stringify(result.report),
          pdfUrl: result.pdf_url || "",
        },
      });
    } catch (error: any) {
      console.error("Processing error:", error);

      Alert.alert(
        "Processing Failed",
        error?.message || "Could not process your voice recording."
      );
    } finally {
      setProcessing(false);
    }
  }

  // RECORDING STATUS
  const isRecording = recorderState.isRecording;
  const duration = Math.floor(
    recorderState.durationMillis / 1000
  );

  const minutes = Math.floor(duration / 60)
    .toString()
    .padStart(2, "0");

  const seconds = (duration % 60)
    .toString()
    .padStart(2, "0");

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.back}
        >
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>

        <View style={styles.header}>
          <Text style={styles.title}>Field Visit</Text>
          <Text style={styles.description}>
            Speak naturally. You can speak in Hindi or Hinglish.
          </Text>
        </View>

        <View style={styles.example}>
          <Text style={styles.exampleTitle}>Example</Text>
          <Text style={styles.exampleText}>
            “मेरा नाम सृष्टि है, आज मैं आसनसोल के एक हेल्थ सेंटर में गई थी।
            मैंने 20 मरीजों की जांच की, 5 मरीजों को बुखार था।
            दो मरीजों का ब्लड प्रेशर ज्यादा था। मैंने उन्हें डॉक्टर से
            मिलने की सलाह दी।”
          </Text>
        </View>

        <View style={styles.recordArea}>
          <Text style={styles.status}>
            {processing
              ? "AI is creating your report..."
              : isRecording
              ? "Listening..."
              : "Tap the microphone to speak"}
          </Text>

          <Text style={styles.timer}>
            {minutes}:{seconds}
          </Text>

          {isRecording && (
            <Text style={styles.micLevel}>
              Mic level:{" "}
              {recorderState.metering == null
                ? "Unavailable"
                : `${Math.round(recorderState.metering)} dB`}
            </Text>
          )}

          <TouchableOpacity
            activeOpacity={0.8}
            disabled={processing}
            onPress={isRecording ? stopRecording : startRecording}
            style={[
              styles.micButton,
              isRecording && styles.recordingButton,
              processing && styles.disabledButton,
            ]}
          >
            <Text style={styles.micIcon}>
              {isRecording ? "■" : "🎤"}
            </Text>
          </TouchableOpacity>

          <Text style={styles.bottomText}>
            {processing
              ? "Understanding your field activity..."
              : isRecording
              ? "Tap again when you are finished"
              : "Your complete statement can be up to 2 minutes"}
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  container: {
    flex: 1,
    padding: 22,
  },
  back: {
    paddingVertical: 8,
  },
  backText: {
    color: Colors.primary,
    fontSize: 15,
    fontWeight: "700",
  },
  header: {
    marginTop: 18,
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
    color: Colors.primary,
  },
  description: {
    marginTop: 8,
    color: Colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
  },
  example: {
    marginTop: 22,
    padding: 16,
    backgroundColor: Colors.primaryLight,
    borderRadius: 16,
  },
  exampleTitle: {
    fontSize: 12,
    fontWeight: "800",
    color: Colors.primary,
    marginBottom: 8,
    textTransform: "uppercase",
  },
  exampleText: {
    fontSize: 13,
    lineHeight: 20,
    color: Colors.text,
  },
  recordArea: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  status: {
    color: Colors.textSecondary,
    fontSize: 15,
    fontWeight: "600",
    textAlign: "center",
  },
  timer: {
    fontSize: 36,
    fontWeight: "800",
    color: Colors.primary,
    marginTop: 12,
  },
  micLevel: {
    marginTop: 8,
    color: Colors.textSecondary,
    fontSize: 13,
  },
  micButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 30,
    shadowOpacity: 0.15,
    shadowRadius: 15,
    shadowOffset: {
      width: 0,
      height: 8,
    },
  },
  recordingButton: {
    backgroundColor: Colors.recording,
  },
  disabledButton: {
    opacity: 0.6,
  },
  micIcon: {
    fontSize: 42,
    color: Colors.white,
  },
  bottomText: {
    marginTop: 22,
    color: Colors.textSecondary,
    fontSize: 13,
    textAlign: "center",
  },
});

