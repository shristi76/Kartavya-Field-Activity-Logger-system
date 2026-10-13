import AsyncStorage from "@react-native-async-storage/async-storage";
import { FieldReport } from "../types/report";

const HISTORY_KEY = "field_reports";

export async function saveReport(
  report: FieldReport
) {
  const existing = await getReports();

  const newReport = {
    id: Date.now().toString(),
    createdAt: new Date().toISOString(),
    report,
  };

  const updated = [
    newReport,
    ...existing,
  ];

  await AsyncStorage.setItem(
    HISTORY_KEY,
    JSON.stringify(updated)
  );
}

export async function getReports() {
  const data =
    await AsyncStorage.getItem(HISTORY_KEY);

  if (!data) {
    return [];
  }

  return JSON.parse(data);
}

export async function clearReports() {
  await AsyncStorage.removeItem(HISTORY_KEY);
}