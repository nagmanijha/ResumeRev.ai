// --- STATE AND CONSTANTS ---

/** @type {string|null} Stores the ID of the most recent analysis. */
let currentAnalysisId = null;

const UI = {
    uploadForm: document.getElementById('upload-form'),
    submitButton: document.querySelector('#upload-form button[type="submit"]'),
    downloadButton: null, // Will be assigned after rendering
    resultsSummary: document.getElementById('results-summary'),
    resultsDetails: document.getElementById('results-details')
};

// --- EVENT LISTENERS ---

document.addEventListener('DOMContentLoaded', () => {
    if (UI.uploadForm) {
        UI.uploadForm.addEventListener('submit', handleFormSubmit);
    }
    // Use event delegation for the download button, as it's created dynamically.
    document.addEventListener('click', (event) => {
        if (event.target && event.target.id === 'download-btn') {
            handleDownloadReport();
        }
    });
});


// --- CORE LOGIC ---

/**
 * Handles the form submission to start the analysis.
 * @param {Event} event - The form submission event.
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    setLoadingState(true);
    hideResults();

    const formData = new FormData(UI.uploadForm);

    try {
        const response = await fetch('/analyze/', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'An unknown error occurred during analysis.');
        }

        const data = await response.json();
        currentAnalysisId = data.analysis_id; // Store the ID for later use
        populateDashboard(data);

    } catch (error) {
        displayError(error.message);
    } finally {
        setLoadingState(false);
    }
}

/**
 * Populates the dashboard with analysis results.
 * @param {object} data - The analysis data from the API.
 */
function populateDashboard(data) {
    if (!UI.resultsSummary || !UI.resultsDetails) return;

    // Render sections and make them visible
    UI.resultsSummary.innerHTML = renderSummary(data);
    UI.resultsDetails.innerHTML = renderDetails(data);
    UI.resultsSummary.classList.remove('hidden');
    UI.resultsDetails.classList.remove('hidden');

    // Update the download button reference
    UI.downloadButton = document.getElementById('download-btn');
}

/**
 * Handles the PDF report download request.
 * This version is more efficient as it uses the analysis ID instead of re-uploading files.
 */
async function handleDownloadReport() {
    if (!currentAnalysisId) {
        alert("Please run an analysis before downloading a report.");
        return;
    }

    if (!UI.downloadButton) return;

    const originalButtonText = UI.downloadButton.innerHTML;
    UI.downloadButton.disabled = true;
    UI.downloadButton.innerHTML = '🔄 Generating...';

    try {
        const response = await fetch('/download-report/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analysis_id: currentAnalysisId })
        });

        if (!response.ok) {
            throw new Error('Failed to generate the report PDF.');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'Resume_Analysis_Report.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

    } catch (error) {
        alert(`Error downloading report: ${error.message}`);
    } finally {
        UI.downloadButton.disabled = false;
        UI.downloadButton.innerHTML = originalButtonText;
    }
}


// --- UI RENDERING FUNCTIONS ---

/**
 * Renders the top-level summary cards (ATS Score, Skill Match).
 * @param {object} data - The analysis data.
 * @returns {string} The HTML string for the summary section.
 */
function renderSummary({ ats_score }) {
    const score = ats_score?.total_score ?? 0;
    const skillMatchScore = ats_score?.breakdown?.skill_match ?? 0;
    const scoreColor = score > 85 ? 'text-green-400' : score > 70 ? 'text-yellow-400' : 'text-orange-400';
    const strokeDashoffset = 283 * (1 - score / 100);

    return `
        <div class="bg-slate-800 p-6 rounded-2xl shadow-lg flex flex-col items-center justify-center fade-in">
            <h2 class="text-lg font-semibold text-slate-400 mb-4">Overall ATS Score</h2>
            <div class="relative w-40 h-40">
                <svg class="w-full h-full" viewBox="0 0 100 100" style="transform: rotate(-90deg);">
                    <circle class="text-slate-700" stroke-width="10" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" />
                    <circle class="progress-animate ${scoreColor}" stroke-width="10" stroke-dasharray="283" stroke-dashoffset="${strokeDashoffset}" stroke-linecap="round" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" />
                </svg>
                <span class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-4xl font-bold text-white">${score}</span>
            </div>
        </div>
        <div class="bg-slate-800 p-6 rounded-2xl shadow-lg flex flex-col items-center justify-center fade-in" style="animation-delay: 0.1s;">
            <h2 class="text-lg font-semibold text-slate-400 mb-4">JD Skill Match</h2>
            <p class="text-5xl font-bold text-white mb-2">${skillMatchScore}%</p>
            <p class="text-slate-400">of required skills are present.</p>
        </div>
    `;
}

/**
 * Renders the detailed analysis sections by composing smaller render functions.
 * @param {object} data - The analysis data.
 * @returns {string} The HTML string for the details section.
 */
function renderDetails(data) {
    return `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            ${renderSuggestionsCard(data.suggestions)}
            ${renderSkillGapCard(data.ats_score?.skill_gap)}
            ${renderExperienceCard(data.parsed_data?.experience)}
            ${renderProjectsCard(data.parsed_data?.projects)}
        </div>
    `;
}

// --- COMPONENT RENDERERS (for renderDetails) ---

function renderSuggestionsCard(suggestions = []) {
    const suggestionsHTML = suggestions.length > 0
        ? suggestions.map(s => `<li class="mb-2">${s}</li>`).join('')
        : '<li>No specific suggestions available at this time.</li>';

    return `
        <div class="md:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.2s;">
            <h2 class="text-xl font-bold text-white mb-4">AI-Powered Suggestions</h2>
            <ul class="space-y-2 list-disc list-inside pl-5 text-slate-300">${suggestionsHTML}</ul>
            <div class="mt-6 text-center">
                <button id="download-btn" class="bg-sky-600 hover:bg-sky-500 text-white font-bold py-3 px-6 rounded-lg transition-transform transform hover:scale-105">
                    Download Summary (PDF)
                </button>
            </div>
        </div>`;
}

function renderSkillGapCard(skillGap = { matched: [], missing: [] }) {
    const matchedSkillsHTML = skillGap.matched?.length > 0
        ? skillGap.matched.map(skill => `<li class="text-green-300">${skill}</li>`).join('')
        : '<li class="text-slate-500">No skills matched</li>';
    const missingSkillsHTML = skillGap.missing?.length > 0
        ? skillGap.missing.map(skill => `<li class="text-red-300">${skill}</li>`).join('')
        : '<li class="text-slate-500">No skills missing - perfect match!</li>';

    return `
        <div class="md:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.3s;">
            <h2 class="text-xl font-bold text-white mb-4">Comprehensive Skill Gap Analysis</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h3 class="text-lg font-semibold text-green-400 mb-3">✅ Matched Skills</h3>
                    <ul class="space-y-1">${matchedSkillsHTML}</ul>
                </div>
                <div>
                    <h3 class="text-lg font-semibold text-red-400 mb-3">❌ Missing Skills</h3>
                    <ul class="space-y-1">${missingSkillsHTML}</ul>
                </div>
            </div>
        </div>`;
}

// function renderProficiencyCard(skillLevels = {}) {
//     const proficiencyHTML = Object.keys(skillLevels).length > 0
//         ? Object.entries(skillLevels).map(([skill, level]) =>
//             `<li class="flex justify-between"><span>${skill}</span><span class="font-semibold ${getProficiencyColor(level)}">${level}</span></li>`
//         ).join('')
//         : '<li class="text-slate-500">No skill proficiency data available</li>';

//     return `
//         <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.4s;">
//             <h2 class="text-xl font-bold text-white mb-4">Rated Skill Proficiency</h2>
//             <ul class="space-y-2">${proficiencyHTML}</ul>
//         </div>`;
// }

function renderExperienceCard(experience = []) {
    const experienceHTML = experience.length > 0
        ? experience.map(exp => `
            <div class="p-4 rounded-lg bg-slate-700/50 mb-3">
                <p class="font-bold text-white">${exp.title || 'Untitled Role'} <span class="font-normal text-slate-400">at ${exp.company || 'Unknown Company'}</span></p>
                <p class="text-sm text-slate-400 mt-1">${(exp.description || "").substring(0, 200)}...</p>
            </div>`).join('')
        : '<p class="text-slate-500 text-sm">No structured work experience was parsed.</p>';

    return `
        <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.5s;">
            <h2 class="text-xl font-bold text-white mb-4">Work Experience</h2>
            <div class="space-y-3">${experienceHTML}</div>
        </div>`;
}

function renderProjectsCard(projects = []) {
    const projectsHTML = projects.length > 0
        ? projects.map(p => `
            <div class="p-4 rounded-lg bg-slate-700/50 mb-3">
                <div class="flex justify-between items-center">
                    <p class="font-bold text-white">${p.title || 'Untitled Project'}</p>
                    <span class="text-sm font-semibold px-3 py-1 rounded-full ${getRelevanceColor(p.relevance_score)}">Relevance: ${p.relevance_score || 0}%</span>
                </div>
                <div class="flex flex-wrap gap-2 mt-2">
                    ${(p.technologies || []).map(t => `<span class="text-xs px-2 py-0.5 rounded-full bg-slate-600">${t}</span>`).join('')}
                </div>
            </div>`).join('')
        : '<p class="text-slate-500 text-sm">No structured projects were parsed.</p>';

    return `
        <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.6s;">
            <h2 class="text-xl font-bold text-white mb-4">Projects</h2>
            <div class="space-y-3">${projectsHTML}</div>
        </div>`;
}


// --- UI HELPER FUNCTIONS ---

/**
 * Sets the loading state for the submit button.
 * @param {boolean} isLoading - Whether the application is in a loading state.
 */
function setLoadingState(isLoading) {
    if (!UI.submitButton) return;
    if (isLoading) {
        UI.submitButton.disabled = true;
        UI.submitButton.innerHTML = `
            <svg class="animate-spin h-5 w-5 mr-3 inline-block" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Analyzing...`;
    } else {
        UI.submitButton.disabled = false;
        UI.submitButton.innerHTML = '🚀 Analyze Resume';
    }
}

/** Hides the results containers. */
function hideResults() {
    if (UI.resultsSummary) UI.resultsSummary.classList.add('hidden');
    if (UI.resultsDetails) UI.resultsDetails.classList.add('hidden');
}

/**
 * Displays an error message in the summary area.
 * @param {string} message - The error message to display.
 */
function displayError(message) {
    if (UI.resultsSummary) {
        UI.resultsSummary.classList.remove('hidden');
        UI.resultsSummary.innerHTML = `
            <div class="lg:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg text-red-400">
                <h2 class="text-xl font-bold mb-2">Analysis Failed</h2>
                <p>${message}</p>
            </div>`;
    }
}


// --- FORMATTING HELPERS ---

function getProficiencyColor(level) {
    switch (level?.toLowerCase()) {
        case 'expert': return 'text-purple-400';
        case 'advanced': return 'text-blue-400';
        case 'intermediate': return 'text-green-400';
        default: return 'text-yellow-400';
    }
}

function getRelevanceColor(score = 0) {
    if (score >= 80) return 'bg-green-500/20 text-green-300';
    if (score >= 60) return 'bg-blue-500/20 text-blue-300';
    if (score >= 40) return 'bg-yellow-500/20 text-yellow-300';
    return 'bg-red-500/20 text-red-300';
}