
import {
  Linking,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Alert,
} from "react-native";

import {
  router,
  useLocalSearchParams,
} from "expo-router";

import { Colors } from "../constants/colors";
import ReportCard from "../components/ReportCard";
import { FieldReport } from "../types/report";
import { getPdfUrl } from "../services/api";

export default function ReportScreen() {
  const params = useLocalSearchParams<{
    report?: string;
    pdfUrl?: string;
  }>();

  let report: FieldReport | null = null;

  try {
    const reportParam = params.report;

    if (typeof reportParam === "string") {
      report = JSON.parse(reportParam) as FieldReport;
    }
  } catch {
    report = null;
  }

  async function openPdf() {
    if (!params.pdfUrl || typeof params.pdfUrl !== "string") {
      Alert.alert(
        "PDF unavailable",
        "No PDF report is available for this record."
      );
      return;
    }

    try {
      const url = getPdfUrl(params.pdfUrl);
      await Linking.openURL(url);
    } catch {
      Alert.alert(
        "Unable to open PDF",
        "Please check your internet connection and try again."
      );
    }
  }

  if (!report) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>
            Report unavailable
          </Text>

          <Text style={styles.emptySubtitle}>
            Please generate your report again.
          </Text>

          <TouchableOpacity
            onPress={() => router.replace("/")}
            style={styles.homeButton}
          >
            <Text style={styles.link}>
              Go Home
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <TouchableOpacity
          onPress={() => router.replace("/")}
          style={styles.back}
        >
          <Text style={styles.backText}>
            ← Home
          </Text>
        </TouchableOpacity>

        <Text style={styles.title}>
          Your Field Report
        </Text>

        <Text style={styles.subtitle}>
          Generated from your voice recording
        </Text>

        <View style={styles.report}>
          <ReportCard report={report} />
        </View>

        {typeof params.pdfUrl === "string" &&
        params.pdfUrl.length > 0 ? (
          <TouchableOpacity
            style={styles.pdfButton}
            onPress={openPdf}
            accessibilityRole="button"
            accessibilityLabel="Open PDF field report"
          >
            <Text style={styles.pdfText}>
              📄  Open PDF Report
            </Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          style={styles.newButton}
          onPress={() => router.replace("/record")}
          accessibilityRole="button"
          accessibilityLabel="Create another field report"
        >
          <Text style={styles.newButtonText}>
            🎤  Create Another Report
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.background,
  },

  container: {
    padding: 22,
    paddingBottom: 40,
  },

  back: {
    paddingVertical: 8,
    marginBottom: 20,
  },

  backText: {
    color: Colors.primary,
    fontWeight: "700",
  },

  title: {
    fontSize: 30,
    fontWeight: "800",
    color: Colors.primary,
  },

  subtitle: {
    color: Colors.textSecondary,
    marginTop: 6,
    marginBottom: 22,
  },

  report: {
    marginBottom: 16,
  },

  pdfButton: {
    minHeight: 54,
    borderRadius: 15,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },

  pdfText: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: "700",
  },

  newButton: {
    minHeight: 54,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 12,
    paddingHorizontal: 16,
  },

  newButtonText: {
    color: Colors.primary,
    fontSize: 15,
    fontWeight: "700",
  },

  empty: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },

  emptyTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.text,
  },

  emptySubtitle: {
    marginTop: 8,
    color: Colors.textSecondary,
    textAlign: "center",
  },

  homeButton: {
    padding: 8,
  },

  link: {
    color: Colors.primary,
    marginTop: 12,
    fontWeight: "700",
  },
});
