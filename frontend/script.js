// --- CONFIG ---
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : ''; // Relative path for production (same origin)

// --- STATE ---
let currentMode = 'applicant';
let batchFiles = [];
let leaderboardResults = []; // Global state for leaderboard
let stopRanking = false;
let currentSort = 'score_desc';
let currentSearch = '';
let currentPage = 1;
const itemsPerPage = 10;
let filteredState = [];

// --- DOM ---
const UI = {
    modeToggle: document.getElementById('mode-toggle'),
    applicantView: document.getElementById('applicant-view'),
    recruiterView: document.getElementById('recruiter-view'),
    // Applicant
    jobDescription: document.getElementById('job-description'),
    fileBtn: document.getElementById('file-btn'),
    fileInput: document.getElementById('resume-file'),
    fileName: document.getElementById('file-name'),
    fileSelected: document.getElementById('file-selected'),
    analyzeBtn: document.getElementById('analyze-btn'),
    btnText: document.getElementById('btn-text'),
    btnSpinner: document.getElementById('btn-spinner'),
    scoreRow: document.getElementById('score-row'),
    scoreNumber: document.getElementById('score-number'),
    scoreRing: document.getElementById('score-ring'),
    scoreContext: document.getElementById('score-context'),
    skillMatchValue: document.getElementById('skill-match-value'),
    skillMatchLabel: document.getElementById('skill-match-label'),
    skillMatchBar: document.getElementById('skill-match-bar'),
    suggestionsCard: document.getElementById('suggestions-card'),
    suggestionsList: document.getElementById('suggestions-list'),
    skillsCard: document.getElementById('skills-card'),
    matchedSkills: document.getElementById('matched-skills'),
    missingSkills: document.getElementById('missing-skills'),
    expRow: document.getElementById('exp-row'),
    experienceList: document.getElementById('experience-list'),
    projectsList: document.getElementById('projects-list'),
    downloadBtn: document.getElementById('download-btn'),
    // Recruiter
    recruiterJd: document.getElementById('recruiter-jd'),
    batchDropZone: document.getElementById('batch-drop-zone'),
    batchUploadInput: document.getElementById('batch-upload-input'),
    fileCount: document.getElementById('file-count'),
    rankBtn: document.getElementById('rank-btn'),
    rankBtnText: document.getElementById('rank-btn-text'),
    rankSpinner: document.getElementById('rank-spinner'),
    leaderboardBody: document.getElementById('leaderboard-body'),
    toastContainer: document.getElementById('toast-container'),
    searchCandidates: document.getElementById('search-candidates'),
    stopBtn: document.getElementById('stop-btn'),
    sortSelect: document.getElementById('sort-candidates'),
    saveJdBtn: document.getElementById('save-jd-btn'),
    headerRole: document.getElementById('header-role'),
    headerId: document.getElementById('header-id'),
    inputRole: document.getElementById('input-role'),
    inputId: document.getElementById('input-id'),
    prevBtn: document.getElementById('prev-btn'),
    nextBtn: document.getElementById('next-btn'),
    pageDisplay: document.getElementById('page-display'),
};

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    initModeToggle();
    initApplicantForm();
    initRecruiterForm();
});

// --- MODE TOGGLE ---
function initModeToggle() {
    const buttons = UI.modeToggle.querySelectorAll('.mode-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            switchMode(mode);
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

function switchMode(mode) {
    currentMode = mode;
    UI.applicantView.classList.toggle('hidden', mode !== 'applicant');
    UI.recruiterView.classList.toggle('hidden', mode !== 'recruiter');
}

// --- APPLICANT ---
function initApplicantForm() {
    UI.fileBtn.addEventListener('click', () => UI.fileInput.click());
    UI.fileInput.addEventListener('change', () => {
        const file = UI.fileInput.files[0];
        UI.fileName.textContent = file ? file.name : 'No file chosen';
        if (UI.fileSelected) UI.fileSelected.textContent = file ? `Selected: ${file.name}` : '';
    });
    UI.analyzeBtn.addEventListener('click', handleAnalyze);
    UI.downloadBtn.addEventListener('click', handleDownload);
}

async function handleAnalyze() {
    const jd = UI.jobDescription.value;
    const file = UI.fileInput.files[0];
    if (!jd || jd.length < 20) { showToast('Please enter a job description', 'error'); return; }
    if (!file) { showToast('Please upload a resume file', 'error'); return; }

    setLoading(true);

    try {
        const formData = new FormData();
        formData.append('job_description', jd);
        formData.append('file', file);
        const res = await fetch(`${API_BASE_URL}/analyze/`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Analysis failed');
        const data = await res.json();
        renderResults(data);
        showToast('Analysis complete!', 'success');
    } catch (err) {
        showToast(`Error: ${err.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function setLoading(loading) {
    UI.analyzeBtn.disabled = loading;
    UI.btnText.textContent = loading ? 'Analyzing...' : 'Analyze Resume';
    UI.btnSpinner.classList.toggle('hidden', !loading);
}

function renderResults(data) {
    const score = data.ats_score?.total_score || 0;
    const skillMatch = data.ats_score?.breakdown?.skill_match || 0;
    const matched = data.ats_score?.skill_gap?.matched || [];
    const missing = data.ats_score?.skill_gap?.missing || [];
    const context = data.ats_score?.context || {};
    const breakdown = data.ats_score?.breakdown || {};
    const suggestions = data.suggestions || [];
    const experience = data.parsed_data?.experience || [];
    const projects = data.parsed_data?.projects || [];

    // Show sections
    UI.scoreRow.style.display = 'grid';
    UI.suggestionsCard.style.display = 'block';
    UI.skillsCard.style.display = 'block';
    UI.expRow.style.display = 'grid';

    // Score circle
    UI.scoreNumber.textContent = score;
    const circumference = 2 * Math.PI * 58;
    UI.scoreRing.style.strokeDasharray = circumference;
    UI.scoreRing.style.strokeDashoffset = circumference * (1 - score / 100);

    // Score context - show breakdown factors
    if (UI.scoreContext) {
        const factors = [];
        if (breakdown.semantic_match < 50) factors.push(`Content: ${breakdown.semantic_match}%`);
        if (breakdown.experience_match < 50) factors.push(`Exp: ${breakdown.experience_match}%`);
        if (breakdown.project_match < 50) factors.push(`Projects: ${breakdown.project_match}%`);
        UI.scoreContext.innerHTML = factors.length > 0
            ? `<span class="score-hint">Low: ${factors.join(', ')}</span>`
            : '';
    }

    // Skill match with dynamic label
    UI.skillMatchValue.textContent = skillMatch + '%';
    UI.skillMatchBar.style.width = skillMatch + '%';
    if (UI.skillMatchLabel) {
        const skillsMatched = context.skills_matched || matched.length;
        const skillsRequired = context.skills_required || (matched.length + missing.length);
        UI.skillMatchLabel.textContent = skillsRequired > 0
            ? `Matched ${skillsMatched}/${skillsRequired} required skills`
            : 'of required skills present';
    }

    // Suggestions
    UI.suggestionsList.innerHTML = suggestions.map(s => `<li>${s}</li>`).join('') || '<li>No suggestions available.</li>';

    // Skills - improved missing skills display
    UI.matchedSkills.innerHTML = matched.length
        ? matched.map(s => `<span class="chip chip-success">${s}</span>`).join('')
        : '<span style="color:var(--text-muted)">None detected</span>';

    // Hide missing section header or show success message when no missing skills
    const missingColumn = UI.missingSkills?.closest('.skills-column');
    if (missing.length === 0) {
        if (missingColumn) {
            missingColumn.innerHTML = `
                <h4 class="success"><span class="material-symbols-outlined">verified</span> All Skills Present</h4>
                <div class="chip-list"><span class="chip chip-success">✓ No missing critical skills</span></div>
            `;
        }
    } else {
        UI.missingSkills.innerHTML = missing.map(s => `<span class="chip chip-danger">${s}</span>`).join('');
    }

    // Experience
    UI.experienceList.innerHTML = experience.length ? experience.map(e => `
    <div class="exp-item">
      <div class="exp-header">
        <div>
          <div class="exp-title">${e.title || 'Role'}</div>
          <div class="exp-company">${e.company || ''}</div>
        </div>
        <div class="exp-date">${e.dates || ''}</div>
      </div>
      <div class="exp-desc">${e.description || ''}</div>
    </div>
  `).join('') : '<p style="color:var(--text-muted)">No experience found</p>';

    // Projects
    UI.projectsList.innerHTML = projects.length ? projects.map(p => `
    <div class="project-item">
      <div class="project-header">
        <div class="project-title">${p.title || 'Project'}</div>
        ${p.relevance_score ? `<span class="project-relevance">Relevance: ${p.relevance_score}%</span>` : ''}
      </div>
      <div class="project-tech">${(p.technologies || []).map(t => `<span class="chip">${t}</span>`).join('')}</div>
    </div>
  `).join('') : '<p style="color:var(--text-muted)">No projects found</p>';
}

async function handleDownload() {
    if (!UI.fileInput.files[0]) { showToast('No resume to download report for', 'error'); return; }
    try {
        const formData = new FormData();
        formData.append('job_description', UI.jobDescription.value);
        formData.append('file', UI.fileInput.files[0]);
        const res = await fetch(`${API_BASE_URL}/download-report/`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Download failed');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'Resume_Analysis.pdf';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        showToast('Report downloaded!', 'success');
    } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
}

// --- RECRUITER ---
function initRecruiterForm() {
    if (!UI.batchDropZone || !UI.batchUploadInput) {
        console.warn('Recruiter elements not found');
        return;
    }

    UI.batchDropZone.addEventListener('click', () => UI.batchUploadInput.click());
    UI.batchUploadInput.addEventListener('change', handleFileSelect);

    ['dragenter', 'dragover'].forEach(e => {
        UI.batchDropZone.addEventListener(e, ev => {
            ev.preventDefault();
            ev.stopPropagation();
            UI.batchDropZone.style.borderColor = 'var(--accent)';
        });
    });

    ['dragleave', 'drop'].forEach(e => {
        UI.batchDropZone.addEventListener(e, ev => {
            ev.preventDefault();
            ev.stopPropagation();
            UI.batchDropZone.style.borderColor = '';
        });
    });

    UI.batchDropZone.addEventListener('drop', ev => {
        ev.preventDefault();
        const files = ev.dataTransfer.files;
        if (files.length > 0) {
            // Create a new DataTransfer to set files
            const dt = new DataTransfer();
            for (let i = 0; i < files.length; i++) {
                dt.items.add(files[i]);
            }
            UI.batchUploadInput.files = dt.files;
            handleFileSelect();
        }
    });

    UI.rankBtn.addEventListener('click', handleRank);

    const shareBtn = document.getElementById('share-btn');
    if (shareBtn) shareBtn.addEventListener('click', handleShare);

    const rerunBtn = document.getElementById('rerun-btn');
    if (rerunBtn) rerunBtn.addEventListener('click', handleRerun);

    if (UI.searchCandidates) {
        UI.searchCandidates.addEventListener('input', debounce((e) => {
            handleSearch(e.target.value);
        }, 300));
    }

    if (UI.stopBtn) {
        UI.stopBtn.addEventListener('click', handleStopRanking);
    }

    if (UI.sortSelect) {
        UI.sortSelect.addEventListener('change', (e) => {
            handleSort(e.target.value);
        });
    }

    if (UI.saveJdBtn) {
        UI.saveJdBtn.addEventListener('click', handleSaveJD);
    }

    if (UI.prevBtn) UI.prevBtn.addEventListener('click', () => changePage(-1));
    if (UI.nextBtn) UI.nextBtn.addEventListener('click', () => changePage(1));
}

// --- HELPERS ---
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

function handleSearch(query) {
    currentSearch = query;
    applyFilters();
}

function handleSort(sortType) {
    currentSort = sortType;
    applyFilters();
}

function changePage(delta) {
    const totalPages = Math.ceil(filteredState.length / itemsPerPage);
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderPage();
    }
}

function applyFilters() {
    if (!leaderboardResults) return;
    let results = [...leaderboardResults];

    // Filter
    if (currentSearch) {
        const lower = currentSearch.toLowerCase();
        results = results.filter(r =>
            r.name.toLowerCase().includes(lower) ||
            r.role.toLowerCase().includes(lower)
        );
    }

    // Sort
    results.sort((a, b) => {
        if (currentSort === 'score_desc') return b.score - a.score;
        if (currentSort === 'score_asc') return a.score - b.score;
        if (currentSort === 'match_desc') return b.match - a.match;
        if (currentSort === 'name_asc') return a.name.localeCompare(b.name);
        return 0;
    });

    filteredState = results;
    currentPage = 1;
    renderPage();
}

function renderPage() {
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const slice = filteredState.slice(start, end);

    renderLeaderboard(slice);
    updatePaginationUI();
}

function updatePaginationUI() {
    const total = filteredState.length;
    const totalPages = Math.ceil(total / itemsPerPage) || 1;
    const start = (currentPage - 1) * itemsPerPage + 1;
    const end = Math.min(start + itemsPerPage - 1, total);

    if (UI.pageDisplay) UI.pageDisplay.textContent = currentPage;

    const info = document.getElementById('pagination-info');
    if (info) info.textContent = total > 0
        ? `Showing ${start} to ${end} of ${total} candidates`
        : 'No candidates found';

    if (UI.prevBtn) UI.prevBtn.disabled = currentPage === 1;
    if (UI.nextBtn) UI.nextBtn.disabled = currentPage >= totalPages;

    const pagination = document.getElementById('pagination');
    if (pagination) pagination.style.display = total > 0 ? 'flex' : 'none';
}

function handleShare() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        showToast('Report link copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy link', 'error');
    });
}

function handleRerun() {
    if (batchFiles.length === 0) {
        showToast('No candidates to analyze', 'error');
        return;
    }

    const btn = document.getElementById('rerun-btn');
    if (btn) {
        btn.animate([
            { transform: 'rotate(0deg)' },
            { transform: 'rotate(360deg)' }
        ], {
            duration: 800,
            iterations: 1
        });
    }

    handleRank();
}

function handleFileSelect() {
    batchFiles = Array.from(UI.batchUploadInput.files);
    const progressSection = document.getElementById('progress-section');
    if (progressSection && batchFiles.length > 0) {
        progressSection.style.display = 'none';
    }

    // Update file count display
    if (UI.fileCount) {
        UI.fileCount.textContent = batchFiles.length > 0
            ? `${batchFiles.length} file(s) selected`
            : '';
    }

    UI.rankBtn.disabled = batchFiles.length === 0;

    // Update rank button icon (lock when disabled, leaderboard when enabled)
    const rankIcon = document.getElementById('rank-icon');
    if (rankIcon) {
        rankIcon.textContent = batchFiles.length > 0 ? 'leaderboard' : 'lock';
    }

    if (UI.rankBtnText) {
        UI.rankBtnText.textContent = batchFiles.length > 0
            ? `Rank ${batchFiles.length} Candidate${batchFiles.length > 1 ? 's' : ''}`
            : 'Rank Candidates';
    }

    // Show file queue with file names
    const fileQueueEl = document.getElementById('file-queue');
    if (fileQueueEl && batchFiles.length > 0) {
        fileQueueEl.style.display = 'block';
        fileQueueEl.innerHTML = batchFiles.slice(0, 10).map(f => `
            <div class="file-queue-item">
                <span class="material-symbols-outlined">description</span>
                <span>${f.name}</span>
            </div>
        `).join('');
        if (batchFiles.length > 10) {
            fileQueueEl.innerHTML += `<div class="file-queue-item" style="color:var(--text-muted)">...and ${batchFiles.length - 10} more</div>`;
        }
    } else if (fileQueueEl) {
        fileQueueEl.style.display = 'none';
    }
}

function handleSaveJD() {
    const role = UI.inputRole.value.trim();
    const id = UI.inputId.value.trim();

    if (role) UI.headerRole.textContent = role;
    if (id) UI.headerId.textContent = id.startsWith('#') ? id : `#${id}`;

    const jd = UI.recruiterJd.value;
    if (!jd || jd.length < 10) {
        showToast('Please enter description', 'warning');
        return;
    }

    // Show the job info bar
    const jobInfoBar = document.getElementById('job-info-bar');
    if (jobInfoBar && (role || id)) {
        jobInfoBar.style.display = 'flex';
    }

    showToast('Job requirements saved!', 'success');
}

async function handleRank() {
    const jd = UI.recruiterJd.value;
    if (!jd || jd.length < 20) { showToast('Please enter a job description', 'error'); return; }
    if (batchFiles.length === 0) { showToast('Please upload resumes', 'error'); return; }

    UI.rankBtn.classList.add('hidden'); // Hide rank button
    if (UI.stopBtn) UI.stopBtn.style.display = 'flex'; // Show stop button

    stopRanking = false;

    // Original Disabled State (might not be needed if hidden, but good safety)
    UI.rankBtn.disabled = true;
    if (UI.rankBtnText) UI.rankBtnText.textContent = 'Processing...';
    if (UI.rankSpinner) UI.rankSpinner.classList.remove('hidden');

    const progressSection = document.getElementById('progress-section');
    const progressText = document.getElementById('progress-text');
    const progressPct = document.getElementById('progress-pct');
    const progressFill = document.getElementById('progress-fill');

    if (progressSection) progressSection.style.display = 'block';

    const results = [];
    for (let i = 0; i < batchFiles.length; i++) {
        // Check for stop signal
        if (stopRanking) {
            showToast('Ranking stopped by user.', 'warning');
            break;
        }

        const pct = Math.round(((i + 1) / batchFiles.length) * 100);
        if (progressText) progressText.textContent = `Analyzing ${i + 1} of ${batchFiles.length}...`;
        if (progressPct) progressPct.textContent = `${pct}%`;
        if (progressFill) progressFill.style.width = `${pct}%`;

        try {
            const formData = new FormData();
            formData.append('job_description', jd);
            formData.append('file', batchFiles[i]);
            const res = await fetch(`${API_BASE_URL}/analyze/`, { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                const exp = data.parsed_data?.experience || [];
                results.push({
                    name: data.parsed_data?.name || batchFiles[i].name.replace(/\.(pdf|docx)$/i, ''),
                    role: exp.length > 0 ? exp[0].title || 'Candidate' : 'Candidate',
                    score: data.ats_score?.total_score || 0,
                    match: data.ats_score?.breakdown?.skill_match || 0,
                    missing: data.ats_score?.skill_gap?.missing || [],
                    fileObj: batchFiles[i],
                    status: 'neutral'
                });
            } else {
                results.push({ name: batchFiles[i].name, score: 0, error: true });
            }
        } catch (e) {
            console.error('Error analyzing:', batchFiles[i].name, e);
            results.push({ name: batchFiles[i].name, score: 0, error: true });
        }
    }

    results.sort((a, b) => b.score - a.score);
    leaderboardResults = results; // Store globally
    renderLeaderboard(results);

    // Reset Buttons
    UI.rankBtn.classList.remove('hidden');
    if (UI.stopBtn) UI.stopBtn.style.display = 'none';

    UI.rankBtn.disabled = false;
    if (UI.rankBtnText) UI.rankBtnText.textContent = 'Rank Candidates';
    if (UI.rankSpinner) UI.rankSpinner.classList.add('hidden');
    if (progressSection) progressSection.style.display = 'none';

    // Pagination handled by applyFilters
    applyFilters();
}

function handleStopRanking() {
    stopRanking = true;
}

// --- ACTIONS ---
// --- ACTIONS ---
function handleView(index) {
    const absIndex = (currentPage - 1) * itemsPerPage + index;
    const candidate = filteredState[absIndex];
    if (candidate && candidate.fileObj) {
        const url = URL.createObjectURL(candidate.fileObj);
        window.open(url, '_blank');
    } else {
        showToast('File not available', 'error');
    }
}

function handleApprove(index) {
    const row = document.getElementById(`row-${index}`);
    const absIndex = (currentPage - 1) * itemsPerPage + index;
    const candidate = filteredState[absIndex];

    if (row && candidate) {
        // Toggle approval
        if (row.classList.contains('row-approved')) {
            row.classList.remove('row-approved');
            candidate.status = 'neutral';
        } else {
            row.classList.remove('row-rejected'); // Remove reject if present
            row.classList.add('row-approved');
            candidate.status = 'approved';
        }
    }
}

function handleReject(index) {
    const row = document.getElementById(`row-${index}`);
    const absIndex = (currentPage - 1) * itemsPerPage + index;
    const candidate = filteredState[absIndex];

    if (row && candidate) {
        // Toggle rejection
        if (row.classList.contains('row-rejected')) {
            row.classList.remove('row-rejected');
            candidate.status = 'neutral';
        } else {
            row.classList.remove('row-approved'); // Remove approve if present
            row.classList.add('row-rejected');
            candidate.status = 'rejected';
        }
    }
}

function renderLeaderboard(results) {
    if (results.length === 0) {
        UI.leaderboardBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="6">
                    <div class="empty-state-lg">
                        <span class="material-symbols-outlined empty-icon-lg">people_outline</span>
                        <div class="empty-title">No candidates yet</div>
                        <div class="empty-hint">Complete Steps 1 & 2 to start ranking resumes</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    UI.leaderboardBody.innerHTML = results.map((r, i) => {
        const rank = (currentPage - 1) * itemsPerPage + i + 1;
        const initials = r.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'NA';
        const isGold = rank === 1;
        const avatarColors = ['#8b5cf6', '#06b6d4', '#f97316', '#10b981', '#ec4899'];
        const avatarBg = avatarColors[i % avatarColors.length];

        let rowClass = 'table-row-item';
        if (r.status === 'approved') rowClass += ' row-approved';
        if (r.status === 'rejected') rowClass += ' row-rejected';

        // Score indicator dot
        let dotColor = 'red';
        if (r.score >= 80) dotColor = 'green';
        else if (r.score >= 60) dotColor = 'orange';

        return `
            <tr id="row-${i}" class="${rowClass}">
                <td>
                    <span class="rank-badge ${isGold ? 'gold' : ''}">
                        ${isGold ? '<span class="material-symbols-outlined" style="font-size:14px;color:#fbbf24;margin-right:2px">emoji_events</span>' : ''} 
                        ${String(rank).padStart(2, '0')}
                    </span>
                </td>
                <td>
                    <div class="candidate-cell">
                        <div class="candidate-avatar" style="background:${avatarBg}">${initials}</div>
                        <div>
                            <div class="candidate-name">${r.name}</div>
                            <div class="candidate-role" style="font-size:11px;color:var(--text-muted)">${r.role}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="score-indicator">
                        <div class="score-dot ${dotColor}"></div>
                        <span class="score-cell">${r.score}/100</span>
                    </div>
                </td>
                <td><span class="match-cell" style="color:${r.match >= 80 ? 'var(--success)' : (r.match >= 50 ? 'var(--warning)' : 'var(--danger)')}">${r.match || 0}%</span></td>
                <td>
                    <div style="display:flex;gap:4px;flex-wrap:wrap">
                        ${r.error
                ? '<span class="chip chip-danger" style="padding:2px 6px;font-size:10px">Analysis Failed</span>'
                : (r.missing || []).slice(0, 2).map(s => `<span class="chip chip-danger" style="padding:2px 6px;font-size:10px">${s}</span>`).join('') || '<span class="chip chip-success" style="padding:2px 6px;font-size:10px">All Matched</span>'}
                        ${(r.missing || []).length > 2 ? `<span style="font-size:10px;color:var(--text-muted)">+${r.missing.length - 2}</span>` : ''}
                    </div>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn" title="View" onclick="handleView(${i})"><span class="material-symbols-outlined">visibility</span></button>
                        <button class="action-btn approve" title="Shortlist" onclick="handleApprove(${i})"><span class="material-symbols-outlined">check_circle</span></button>
                        <button class="action-btn reject" title="Reject" onclick="handleReject(${i})"><span class="material-symbols-outlined">cancel</span></button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}


// --- TOAST ---
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type} `;
    toast.textContent = message;
    UI.toastContainer.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
}
