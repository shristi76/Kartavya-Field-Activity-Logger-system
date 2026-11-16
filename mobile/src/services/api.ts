
import { File } from "expo-file-system";
import * as FileSystem from "expo-file-system/legacy";
import { fetch as expoFetch } from "expo/fetch";
import AsyncStorage from "@react-native-async-storage/async-storage";

// const API_BASE_URL = "http://10.0.2.2:5000";
const API_BASE_URL = "http://192.168.1.11:5000";

let accessToken: string | null = null;
export async function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) await AsyncStorage.setItem("field_access_token", token);
  else await AsyncStorage.removeItem("field_access_token");
}
async function authHeaders(headers: Record<string, string> = {}) {
  accessToken ||= await AsyncStorage.getItem("field_access_token");
  return accessToken ? { ...headers, Authorization: `Bearer ${accessToken}` } : headers;
}

// Common API response handler
async function handleResponse(response: Response) {
  if (response.status === 401) throw new Error("Please sign in to your account before continuing.");
  const responseText = await response.text();

  let result: any;

  try {
    result = JSON.parse(responseText);
  } catch {
    throw new Error(`Invalid server response: ${responseText}`);
  }

  if (!response.ok || result.success === false) {
    throw new Error(
      result.error || `Server error: ${response.status}`
    );
  }

  return result;
}

// 1. Upload audio and generate a report
export async function uploadAudio(
  audioUri: string,
  speakerId: string
) {
  const formData = new FormData();

  formData.append("audio", new File(audioUri));
  formData.append("speaker_id", speakerId);

  const response = await expoFetch(`${API_BASE_URL}/api/report`, {
    method: "POST",
    headers: await authHeaders({
      Accept: "application/json",
    }),
    body: formData,
  });

  return handleResponse(response);
}

// 2. Process edited Hindi transcription
export async function processActivity(hindiText: string) {
  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: "POST",
    headers: await authHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      hindi_text: hindiText,
    }),
  });

  return handleResponse(response);
}

// 3. Save reviewed activity

export async function saveActivity(data: {
  speaker_id: string;
  worker_name: string;
  organization: string;
  district: string;
  hindi_text: string;
  translated_text: string;
  activity: string;
  beneficiaries: string;
  location: string;
  audio_file?: string | null;
  photo_file?: string | null;
}) {
  const response = await fetch(`${API_BASE_URL}/api/activities`, {
    method: "POST",
    headers: await authHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(data),
  });

  return handleResponse(response);
}


// 4. Upload activity photo
export async function uploadPhoto(photoUri: string) {
  const formData = new FormData();

  formData.append("photo", new File(photoUri));

  const response = await expoFetch(`${API_BASE_URL}/api/uploads/photo`, {
    method: "POST",
    headers: await authHeaders({
      Accept: "application/json",
    }),
    body: formData,
  });

  return handleResponse(response);
}

// 5. Get recent activities
export async function getRecentActivities(limit = 20) {
  const response = await fetch(
    `${API_BASE_URL}/api/activities?limit=${limit}`,
    {
      headers: await authHeaders({
        Accept: "application/json",
      }),
    }
  );

  return handleResponse(response);
}

export async function getAdminActivities() {
  const response = await fetch(`${API_BASE_URL}/api/admin/activities`, { headers: await authHeaders({ Accept: "application/json" }) });
  return handleResponse(response);
}

export async function getAdminWorkers() {
  const response = await fetch(`${API_BASE_URL}/api/admin/workers`, { headers: await authHeaders({ Accept: "application/json" }) });
  return handleResponse(response);
}

export async function createAdminActivity(data: {
  speaker_id: string;
  hindi_text: string;
  translated_text?: string;
  activity?: string;
  beneficiaries?: string;
  location?: string;
  district?: string;
}) {
  const response = await fetch(`${API_BASE_URL}/api/admin/activities`, {
    method: "POST",
    headers: await authHeaders({ Accept: "application/json", "Content-Type": "application/json" }),
    body: JSON.stringify(data),
  });
  return handleResponse(response);
}


export async function updateActivity(
  activityId: number,
  data: {
    speaker_id: string;
    worker_name: string;
    organization: string;
    district: string;
    hindi_text: string;
    translated_text: string;
    activity: string;
    beneficiaries: string;
    location: string;
    audio_file?: string | null;
    photo_file?: string | null;
  }
) {
  const response = await fetch(
    `${API_BASE_URL}/api/activities/${activityId}`,
    {
      method: "PUT",
      headers: await authHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(data),
    }
  );

  return handleResponse(response);
}


export async function deleteActivity(activityId: number) {
  const response = await fetch(
    `${API_BASE_URL}/api/activities/${activityId}`,
    {
      method: "DELETE",
      headers: await authHeaders({
        Accept: "application/json",
      }),
    }
  );

  return handleResponse(response);
}



export async function generatePdfReport(data: {
  start_date: string;
  end_date: string;
  speaker_id?: string;
  log_id?: number;
}) {
  const response = await fetch(`${API_BASE_URL}/api/reports`, {
    method: "POST",
    headers: await authHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(data),
  });

  return handleResponse(response);
}


export function getPdfDownloadUrl(filename: string): string {
  return `${API_BASE_URL}/api/reports/pdf/${encodeURIComponent(filename)}`;
}

export async function downloadPdfReport(filename: string, destination: string) {
  accessToken ||= await AsyncStorage.getItem("field_access_token");
  const response = await FileSystem.downloadAsync(getPdfDownloadUrl(filename), destination, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  return response;
}

export async function login(worker_id: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ worker_id, password }),
  });
  const result = await handleResponse(response);
  await setAccessToken(result.access_token);
  return result.data;
}

export async function register(data: { name: string; worker_id: string; password: string; organization: string }) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  const result = await handleResponse(response);
  return result.data;
}

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, { headers: await authHeaders({ Accept: "application/json" }) });
  return handleResponse(response);
}
