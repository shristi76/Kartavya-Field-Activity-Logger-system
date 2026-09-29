let currentResult = null;
let currentAudioFile = null;
let currentPhotoFile = null;


// ------------------------------------------------------------
// DOM elements
// ------------------------------------------------------------

const speakerIdInput =
    document.getElementById("speakerId");

const hindiTextInput =
    document.getElementById("hindiText");

const processButton =
    document.getElementById("processButton");

const saveButton =
    document.getElementById("saveButton");

const resultSection =
    document.getElementById("extractedSection");

const recordButton =
    document.getElementById("recordButton");

const recordStatus =
    document.getElementById("recordingIndicator");

const logsTable =
    document.getElementById("activitiesTableBody");

const refreshButton =
    document.getElementById("refreshButton");

const reportButton =
    document.getElementById("generateReportButton");

const reportResult =
    document.getElementById("reportResult");

const message =
    document.getElementById("statusMessage");

const activityPhotoInput =
    document.getElementById("activityPhoto");

const activityPhotoPreview =
    document.getElementById("activityPhotoPreview");


activityPhotoInput.addEventListener(
    "change",
    async () => {

        const photo = activityPhotoInput.files[0];

        currentPhotoFile = null;
        activityPhotoPreview.style.display = "none";

        if (!photo) {
            return;
        }

        activityPhotoPreview.src = URL.createObjectURL(photo);
        activityPhotoPreview.style.display = "block";
        showMessage("Uploading photo...");

        const formData = new FormData();
        formData.append("photo", photo);

        try {
            const response = await fetch(
                "/api/uploads/photo",
                {
                    method: "POST",
                    body: formData
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error);
            }

            currentPhotoFile = result.data.filename;
            showMessage("Photo uploaded successfully.");
        } catch (error) {
            activityPhotoInput.value = "";
            activityPhotoPreview.style.display = "none";
            showMessage(error.message);
        }
    }
);


// ------------------------------------------------------------
// Show message
// ------------------------------------------------------------

function showMessage(text) {

    message.textContent = text;

    message.style.display = "block";

    message.className = "status-message error";

    if (text.includes("completed") || text.includes("successfully")) {
        message.className = "status-message success";
    }

    setTimeout(() => {

        message.style.display = "none";

    }, 3000);
}


// ------------------------------------------------------------
// Process Hindi text
// ------------------------------------------------------------

processButton.addEventListener(
    "click",
    async () => {

        const hindiText =
            hindiTextInput.value.trim();


        if (!hindiText) {

            showMessage(
                "Please enter or record Hindi speech."
            );

            return;
        }


        processButton.disabled = true;

        processButton.textContent =
            "Processing...";

        showMessage("Gemini is processing your recording...");


        try {

            const response =
                await fetch(
                    "/api/process",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            hindi_text: hindiText
                        })
                    }
                );


            const result =
                await response.json();


            if (!result.success) {

                throw new Error(
                    result.error
                );
            }


            currentResult =
                result.data;


            document.getElementById(
                "translatedText"
            ).value =
                currentResult.translated_text;


            document.getElementById(
                "activityText"
            ).value =
                currentResult.activity;


            document.getElementById(
                "beneficiariesText"
            ).value =
                currentResult.beneficiaries;


            document.getElementById(
                "locationText"
            ).value =
                currentResult.location;


            resultSection.style.display = "block";


            showMessage(
                "AI processing completed."
            );

        } catch (error) {

            showMessage(
                error.message
            );

        } finally {

            processButton.disabled = false;

            processButton.textContent =
                "Process with Gemini";
        }
    }
);


// ------------------------------------------------------------
// Save activity
// ------------------------------------------------------------

saveButton.addEventListener(
    "click",
    async () => {

        const speakerId =
            speakerIdInput.value.trim();


        const hindiText =
            hindiTextInput.value.trim();


        if (!speakerId) {

            showMessage(
                "Please enter Speaker ID."
            );

            return;
        }


        if (!hindiText) {

            showMessage(
                "Hindi text is required."
            );

            return;
        }


        if (!currentResult) {

            showMessage(
                "Please process the activity first."
            );

            return;
        }


        saveButton.disabled = true;

        saveButton.textContent =
            "Saving...";


        try {

            const response =
                await fetch(
                    "/api/activities",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            speaker_id:
                                speakerId,

                            hindi_text:
                                hindiText,

                            audio_file:
                                currentAudioFile,

                            translated_text:
                                document.getElementById(
                                    "translatedText"
                                ).value.trim(),

                            activity:
                                document.getElementById(
                                    "activityText"
                                ).value.trim(),

                            beneficiaries:
                                document.getElementById(
                                    "beneficiariesText"
                                ).value.trim(),

                            location:
                                document.getElementById(
                                    "locationText"
                                ).value.trim(),

                            photo_file:
                                currentPhotoFile

                        })
                    }
                );


            const result =
                await response.json();


            if (!result.success) {

                throw new Error(
                    result.error
                );
            }


            showMessage(
                "Activity saved successfully."
            );


            hindiTextInput.value = "";

            currentAudioFile = null;
            currentPhotoFile = null;
            activityPhotoInput.value = "";
            activityPhotoPreview.style.display = "none";

            resultSection.style.display = "none";

            currentResult = null;


            await loadLogs();

        } catch (error) {

            showMessage(
                error.message
            );

        } finally {

            saveButton.disabled = false;

            saveButton.textContent =
                "Save Reviewed Activity";
        }
    }
);


// ------------------------------------------------------------
// Load recent logs
// ------------------------------------------------------------

async function loadLogs() {

    try {

        const response =
            await fetch(
                "/api/activities?limit=20"
            );


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error
            );
        }


        logsTable.innerHTML = "";


        if (
            result.data.length === 0
        ) {

            logsTable.innerHTML = `
                <tr>
                    <td colspan="6">
                        No activities found.
                    </td>
                </tr>
            `;

            return;
        }


        result.data.forEach(
            log => {

                const row =
                    document.createElement(
                        "tr"
                    );


                row.innerHTML = `

                    <td>
                        ${escapeHtml(
                            log.id
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            log.created_at
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            log.speaker_id
                        )}
                    </td>

                    <td>
                        ${log.audio_file ? `
                            <audio
                                class="table-audio"
                                controls
                                src="/api/audio/${encodeURIComponent(
                                    log.audio_file
                                )}"
                            ></audio>
                        ` : "No recording"}
                    </td>

                    <td>
                        ${escapeHtml(
                            log.activity
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            log.beneficiaries
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            log.location
                        )}
                    </td>

                    <td>

                        <button
                            class="small-button"
                            onclick="deleteActivity(
                                ${log.id}
                            )"
                        >
                            Delete
                        </button>

                    </td>
                `;


                logsTable.appendChild(
                    row
                );
            }
        );

    } catch (error) {

        showMessage(
            error.message
        );
    }
}


// ------------------------------------------------------------
// Delete activity
// ------------------------------------------------------------

async function deleteActivity(
    id
) {

    const confirmed =
        confirm(
            "Delete this activity?"
        );


    if (!confirmed) {

        return;
    }


    try {

        const response =
            await fetch(
                `/api/activities/${id}`,
                {
                    method: "DELETE"
                }
            );


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error
            );
        }


        showMessage(
            "Activity deleted."
        );


        await loadLogs();

    } catch (error) {

        showMessage(
            error.message
        );
    }
}


// ------------------------------------------------------------
// Generate reports
// ------------------------------------------------------------

reportButton.addEventListener(
    "click",
    async () => {

        const speakerId = "";

        const reportType =
            document.getElementById("reportType").value;

        let startDate = "";
        let endDate = "";

        if (reportType === "custom") {
            startDate = document.getElementById("startDate").value;
            endDate = document.getElementById("endDate").value;
        } else if (reportType === "monthly") {
            const month = document.getElementById("reportMonth").value;

            if (month) {
                const [year, monthNumber] = month.split("-");
                startDate = `${year}-${monthNumber}-01`;
                endDate = new Date(
                    Number(year),
                    Number(monthNumber),
                    0
                ).toISOString().slice(0, 10);
            }
        } else {
            const year = document.getElementById("reportYear").value;

            if (year) {
                startDate = `${year}-01-01`;
                endDate = `${year}-12-31`;
            }
        }


        if (!startDate || !endDate) {

            showMessage(
                "Please select both dates."
            );

            return;
        }


        reportButton.disabled = true;

        reportButton.textContent =
            "Generating...";


        try {

            const response =
                await fetch(
                    "/api/reports",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            speaker_id:
                                speakerId,

                            start_date:
                                startDate,

                            end_date:
                                endDate

                        })
                    }
                );


            const result =
                await response.json();


            if (!result.success) {

                throw new Error(
                    result.error
                );
            }


            const pdfFile =
                result.data.pdf;

            const excelFile =
                result.data.excel;


            reportResult.innerHTML = `

                <strong>
                    Reports generated successfully.
                </strong>

                <br>
                Generated at: ${escapeHtml(result.data.generated_at)}

                <br><br>

                <a
                    href="/api/reports/pdf/${encodeURIComponent(
                        pdfFile
                    )}"
                >
                    📄 Download PDF
                </a>

                <br><br>

                <a
                    href="/api/reports/excel/${encodeURIComponent(
                        excelFile
                    )}"
                >
                    📊 Download Excel
                </a>
            `;


            reportResult.style.display = "block";


            showMessage(
                "Reports generated."
            );

        } catch (error) {

            showMessage(
                error.message
            );

        } finally {

            reportButton.disabled = false;

            reportButton.textContent =
                "Generate PDF + Excel";
        }
    }
);


// ------------------------------------------------------------
// Refresh logs
// ------------------------------------------------------------

refreshButton.addEventListener(
    "click",
    loadLogs
);


// ------------------------------------------------------------
// Simple HTML escaping
// ------------------------------------------------------------

function escapeHtml(value) {

    if (value === null ||
        value === undefined) {

        return "";
    }


    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function showStatus(text) {
    showMessage(text);
}


// ------------------------------------------------------------
// Browser microphone recording
// ------------------------------------------------------------

let mediaRecorder = null;

let audioChunks = [];


recordButton.addEventListener(
    "click",
    async () => {

        if (
            mediaRecorder &&
            mediaRecorder.state === "recording"
        ) {

            mediaRecorder.stop();

            return;
        }


        try {

            const stream =
                await navigator.mediaDevices
                    .getUserMedia({
                        audio: true
                    });


            mediaRecorder =
                new MediaRecorder(
                    stream
                );


            audioChunks = [];


            mediaRecorder.addEventListener(
                "dataavailable",
                event => {

                    if (
                        event.data.size > 0
                    ) {

                        audioChunks.push(
                            event.data
                        );
                    }
                }
            );


            mediaRecorder.addEventListener(
                "start",
                () => {

                    recordButton.textContent =
                        "⏹ Stop Recording";

                    recordButton.classList.add(
                        "recording"
                    );

                    recordStatus.textContent =
                        "Listening... Speak in Hindi.";
                    recordStatus.style.display = "block";
                }
            );


            mediaRecorder.addEventListener(
                "stop",
                async () => {

                    recordButton.textContent =
                        "🎙 Start Recording";

                    recordButton.classList.remove(
                        "recording"
                    );

                    recordStatus.textContent =
                        "Recording finished.";

                    stream
                        .getTracks()
                        .forEach(
                            track =>
                                track.stop()
                        );


                    const audioBlob =
                        new Blob(
                            audioChunks,
                            {
                                type:
                                    "audio/webm"
                            }
                        );


                    await sendAudioToServer(
                        audioBlob
                    );
                }
            );


            mediaRecorder.start();

        } catch (error) {

            console.error(
                error
            );

            showMessage(
                "Could not access microphone."
            );
        }
    }
);


// ------------------------------------------------------------
// Send audio to backend
// ------------------------------------------------------------
async function sendAudioToServer(audioBlob) {
    try {
        const formData = new FormData();

        // Send the recorded audio file
        formData.append("audio", audioBlob, "recording.webm");

        showStatus("Uploading voice...", "info");

        const response = await fetch("/api/process-audio", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Failed to process audio");
        }

        // Put transcription into the Hindi text box
        document.getElementById("hindiText").value = data.transcription;
        currentAudioFile = data.audio_file;

        const audioPlayer = document.getElementById("audioPlayer");
        audioPlayer.src = `/api/audio/${encodeURIComponent(data.audio_file)}`;
        document.getElementById("audioPreview").style.display = "block";

        // Show transcription
        showStatus("Voice converted to text successfully.", "success");

    } catch (error) {
        console.error("Audio upload error:", error);
        showStatus("Voice processing failed: " + error.message, "error");
    }
}
// ------------------------------------------------------------
// Initial page load
// ------------------------------------------------------------

loadLogs();