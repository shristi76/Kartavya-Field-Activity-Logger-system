
import { File } from "expo-file-system";

// const API_BASE_URL = "http://10.0.2.2:5000";
const API_BASE_URL = "http://192.168.1.11:5000";

// Common API response handler
async function handleResponse(response: Response) {
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
  const audioFile = new File(audioUri);
  const formData = new FormData();

  formData.append("audio", audioFile);
  formData.append("speaker_id", speakerId);

  const response = await fetch(`${API_BASE_URL}/api/report`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
    body: formData,
  });

  return handleResponse(response);
}

// 2. Process edited Hindi transcription
export async function processActivity(hindiText: string) {
  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
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
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return handleResponse(response);
}


// 4. Upload activity photo
export async function uploadPhoto(photoUri: string) {
  const photoFile = new File(photoUri);
  const formData = new FormData();

  formData.append("photo", photoFile);

  const response = await fetch(`${API_BASE_URL}/api/uploads/photo`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
    body: formData,
  });

  return handleResponse(response);
}

// 5. Get recent activities
export async function getRecentActivities(limit = 20) {
  const response = await fetch(
    `${API_BASE_URL}/api/activities?limit=${limit}`,
    {
      headers: {
        Accept: "application/json",
      },
    }
  );

  return handleResponse(response);
}


export async function updateActivity(
  activityId: number,
  data: {
    speaker_id: string;
    hindi_text: string;
    translated_text: string;
    activity: string;
    beneficiaries: string;
    location: string;
  }
) {
  const response = await fetch(
    `${API_BASE_URL}/api/activities/${activityId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
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
      headers: {
        Accept: "application/json",
      },
    }
  );

  return handleResponse(response);
}



export async function generatePdfReport(data: {
  start_date: string;
  end_date: string;
  speaker_id?: string;
}) {
  const response = await fetch(`${API_BASE_URL}/api/reports`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return handleResponse(response);
}


export function getPdfDownloadUrl(filename: string): string {
  return `${API_BASE_URL}/api/reports/pdf/${encodeURIComponent(filename)}`;
}
