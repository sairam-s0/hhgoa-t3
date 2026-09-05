document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const dropContent = document.getElementById("dropContent");
    const previewContainer = document.getElementById("previewContainer");
    const imagePreview = document.getElementById("imagePreview");
    const removeFileBtn = document.getElementById("removeFileBtn");
    const verifyForm = document.getElementById("verifyForm");
    const submitBtn = document.getElementById("submitBtn");
    const btnSpinner = document.getElementById("btnSpinner");
    const thresholdInput = document.getElementById("thresholdInput");

    const idleState = document.getElementById("idleState");
    const loadingState = document.getElementById("loadingState");
    const resultState = document.getElementById("resultState");

    const candCountBadge = document.getElementById("candCountBadge");
    const candidatesList = document.getElementById("candidatesList");

    // Click to upload
    dropZone.addEventListener("click", () => fileInput.click());

    // File change
    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            showPreview(e.target.files[0]);
        }
    });

    // Drag & drop
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            showPreview(e.dataTransfer.files[0]);
        }
    });

    removeFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.value = "";
        previewContainer.classList.add("hidden");
        dropContent.classList.remove("hidden");
    });

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            dropContent.classList.add("hidden");
            previewContainer.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    // Submit form
    verifyForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!fileInput.files || !fileInput.files[0]) {
            alert("Please select or drop an image file first.");
            return;
        }

        const formData = new FormData(verifyForm);
        const currentThreshold = parseFloat(thresholdInput.value) || 0.72;

        // UI Loading
        idleState.classList.add("hidden");
        resultState.classList.add("hidden");
        loadingState.classList.remove("hidden");
        submitBtn.disabled = true;
        btnSpinner.classList.remove("hidden");

        // Clear previous candidate list
        candCountBadge.textContent = "Searching...";
        candidatesList.innerHTML = `
            <div class="empty-candidates">
                <div class="spinner" style="margin:0 auto 1rem auto; width:24px; height:24px;"></div>
                <p>Fetching visual candidates from SerpApi Google Lens...</p>
            </div>
        `;

        // Simulate step indicator movement
        const steps = [
            document.getElementById("step1"),
            document.getElementById("step2"),
            document.getElementById("step3"),
            document.getElementById("step4")
        ];

        let stepIndex = 0;
        const interval = setInterval(() => {
            steps.forEach(s => s.classList.remove("active"));
            if (stepIndex < steps.length) {
                steps[stepIndex].classList.add("active");
                stepIndex++;
            }
        }, 1200);

        try {
            const resp = await fetch("/api/verify", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            clearInterval(interval);

            loadingState.classList.add("hidden");
            resultState.classList.remove("hidden");
            submitBtn.disabled = false;
            btnSpinner.classList.add("hidden");

            renderResults(data, currentThreshold);

        } catch (err) {
            clearInterval(interval);
            loadingState.classList.add("hidden");
            submitBtn.disabled = false;
            btnSpinner.classList.add("hidden");
            alert("Error connecting to server: " + err.message);
        }
    });

    function renderResults(data, threshold) {
        const banner = document.getElementById("statusBanner");
        const icon = document.getElementById("statusIcon");
        const title = document.getElementById("statusTitle");
        const desc = document.getElementById("statusDesc");

        if (data.success && data.status === "VERIFIED") {
            banner.className = "status-banner success";
            icon.textContent = "✓";
            title.textContent = "VERIFIED MATCH";
            desc.textContent = "Face similarity confirmed & canonical evidence anchored on Hardhat blockchain.";

            document.getElementById("metricSim").textContent = (data.similarity || 0).toFixed(4);
            document.getElementById("metricFaces").textContent = data.face_count || 1;
            document.getElementById("matchedUrl").textContent = data.matched_post_url || "N/A";
            document.getElementById("matchedUrl").href = data.matched_post_url || "#";
            document.getElementById("evidenceHash").textContent = "SHA256: " + data.evidence_hash;
            document.getElementById("evidenceJson").textContent = JSON.stringify(data.evidence_record, null, 2);

            const bc = data.blockchain || {};
            document.getElementById("txHash").textContent = bc.tx_hash || "N/A";
            document.getElementById("blockNum").textContent = bc.block_number || "42";
            document.getElementById("contractAddr").textContent = bc.contract_address || "0x...";
        } else {
            banner.className = "status-banner failed";
            icon.textContent = "✕";
            title.textContent = "REJECTED / UNVERIFIED";
            desc.textContent = data.error || "No match passed face verification or candidate threshold.";

            document.getElementById("metricSim").textContent = (data.best_similarity || 0).toFixed(4);
            document.getElementById("metricFaces").textContent = "1";
            document.getElementById("matchedUrl").textContent = "N/A";
            document.getElementById("evidenceHash").textContent = "N/A";
            document.getElementById("evidenceJson").textContent = JSON.stringify({ error: data.error }, null, 2);
            document.getElementById("txHash").textContent = "N/A";
            document.getElementById("blockNum").textContent = "N/A";
            document.getElementById("contractAddr").textContent = "N/A";
        }

        // Render Candidates Gallery
        renderCandidatesGallery(data.candidates || [], data.success, threshold);
    }

    function renderCandidatesGallery(candidates, isVerified, threshold) {
        candCountBadge.textContent = `${candidates.length} Discovered`;

        if (!candidates || candidates.length === 0) {
            candidatesList.innerHTML = `
                <div class="empty-candidates">
                    <div class="gallery-icon">🖼️</div>
                    <p>No candidate visual matches found.</p>
                </div>
            `;
            return;
        }

        candidatesList.innerHTML = "";

        candidates.forEach((cand, idx) => {
            const isBestMatch = (idx === 0) && isVerified;
            const simVal = cand.similarity || 0;
            const simClass = simVal >= threshold ? "high-sim" : "low-sim";
            const imgUrl = cand.image_url || "";

            const card = document.createElement("div");
            card.className = `candidate-card ${isBestMatch ? 'best-match' : ''}`;
            card.innerHTML = `
                ${isBestMatch ? '<span class="best-match-tag">MATCHED ✓</span>' : ''}
                <div class="cand-thumb-wrapper">
                    <span class="rank-badge">#${idx + 1}</span>
                    ${imgUrl ? `<img src="${imgUrl}" alt="Candidate preview" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` : ''}
                    <div class="cand-thumb-placeholder" style="${imgUrl ? 'display:none;' : 'display:flex;'} flex-direction:column; align-items:center; justify-content:center; width:100%; height:120px; background:#1e293b; color:#94a3b8; font-size:11px; text-align:center; padding:8px;">
                        <span>📷 Image Unavailable</span>
                    </div>
                </div>
                <div class="cand-info">
                    <div class="cand-title" title="${escapeHtml(cand.title)}">${escapeHtml(cand.title)}</div>
                    <div class="cand-scores">
                        <span class="sim-score-badge ${simClass}">Sim: ${simVal.toFixed(4)}</span>
                    </div>
                    <a href="${cand.page_url}" target="_blank" class="cand-link-btn">
                        <span>View Source Page</span> ↗
                    </a>
                </div>
            `;
            candidatesList.appendChild(card);

        });
    }

    function escapeHtml(str) {
        if (!str) return "Candidate Match";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
});
