import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";

import { router } from "expo-router";

import { Colors } from "../constants/colors";
import { getRecentActivities } from "../services/api";

export default function HistoryScreen() {
  const [reports, setReports] =
    useState<any[]>([]);

  async function loadReports() {
    try {
      const result = await getRecentActivities(100);
      setReports(result.data || []);
    } catch {
      setReports([]);
    }
  }

  useFocusEffect(
    useCallback(() => {
      loadReports();
    }, [])
  );

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
      >

        <TouchableOpacity
          onPress={() =>
            router.replace("/")
          }
        >
          <Text style={styles.back}>
            ← Home
          </Text>
        </TouchableOpacity>

        <View style={styles.header}>
          <View>
            <Text style={styles.title}>
              Report History
            </Text>

            <Text style={styles.subtitle}>
              {reports.length} saved report
              {reports.length !== 1
                ? "s"
                : ""}
            </Text>
          </View>

        </View>

        {reports.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>
              📋
            </Text>

            <Text style={styles.emptyTitle}>
              No reports yet
            </Text>

            <Text style={styles.emptyText}>
              Your generated field reports
              will appear here.
            </Text>

            <TouchableOpacity
              style={styles.createButton}
              onPress={() =>
                router.push("/record")
              }
            >
              <Text style={styles.createText}>
                Create Report
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          reports.map((item) => (
            <View
              key={item.id}
              style={styles.card}
            >
              <View style={styles.cardHeader}>
                <Text style={styles.worker}>
                  {item.worker_name ||
                    "Field Worker"}
                </Text>

                <Text style={styles.date}>
                  {formatDate(
                    item.created_at
                  )}
                </Text>
              </View>

              <Text style={styles.location}>
                📍{" "}
                {item.location ||
                  "Location not mentioned"}
              </Text>

              <Text style={styles.activity}>
                {item.activity ||
                  "Field activity"}
              </Text>

              {item.beneficiaries !==
                null &&
                item.beneficiaries !==
                  undefined && (
                  <Text
                    style={styles.patients}
                  >
                    Beneficiaries:{" "}
                    {item.beneficiaries}
                  </Text>
                )}
            </View>
          ))
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString(
    "en-IN",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
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
    color: Colors.primary,
    fontWeight: "700",
    fontSize: 15,
    marginBottom: 24,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },

  title: {
    fontSize: 29,
    fontWeight: "800",
    color: Colors.primary,
  },

  subtitle: {
    marginTop: 5,
    color: Colors.textSecondary,
  },

  delete: {
    color: Colors.danger,
    fontWeight: "700",
  },

  card: {
    backgroundColor: Colors.white,
    borderRadius: 18,
    padding: 18,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  worker: {
    fontSize: 16,
    fontWeight: "800",
    color: Colors.text,
  },

  date: {
    color: Colors.textSecondary,
    fontSize: 12,
  },

  location: {
    color: Colors.primary,
    fontWeight: "600",
    marginTop: 12,
  },

  activity: {
    color: Colors.textSecondary,
    marginTop: 8,
    lineHeight: 20,
  },

  patients: {
    color: Colors.text,
    marginTop: 10,
    fontWeight: "600",
  },

  empty: {
    backgroundColor: Colors.white,
    borderRadius: 20,
    padding: 30,
    alignItems: "center",
    marginTop: 20,
  },

  emptyIcon: {
    fontSize: 40,
  },

  emptyTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: Colors.text,
    marginTop: 15,
  },

  emptyText: {
    color: Colors.textSecondary,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 20,
  },

  createButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 25,
    paddingVertical: 14,
    borderRadius: 13,
    marginTop: 20,
  },

  createText: {
    color: Colors.white,
    fontWeight: "700",
  },
});
