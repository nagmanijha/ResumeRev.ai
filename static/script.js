let currentAnalysisId = null;

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }
});

async function handleFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button');
    const formData = new FormData(form);

    button.disabled = true;
    button.innerHTML = `
        <svg class="animate-spin h-5 w-5 mr-3 inline-block" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Analyzing...
    `;
    
    const resultsSummary = document.getElementById('results-summary');
    const resultsDetails = document.getElementById('results-details');
    if (resultsSummary) resultsSummary.classList.add('hidden');
    if (resultsDetails) resultsDetails.classList.add('hidden');

    try {
        const response = await fetch('/analyze/', { method: 'POST', body: formData });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Analysis failed.');
        }
        const data = await response.json();
        currentAnalysisId = data.analysis_id;
        populateDashboard(data);
    } catch (error) {
        if (resultsSummary) {
            resultsSummary.classList.remove('hidden');
            resultsSummary.innerHTML = `<div class="lg:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg text-red-400"><h2 class="text-xl font-bold mb-2">Analysis Failed</h2><p>${error.message}</p></div>`;
        }
    } finally {
        button.disabled = false;
        button.innerHTML = '🚀 Analyze Resume';
    }
}

function populateDashboard(data) {
    console.log("Received data from backend:", data);

    const summaryContainer = document.getElementById('results-summary');
    const detailsContainer = document.getElementById('results-details');
    if (!summaryContainer || !detailsContainer) return;

    summaryContainer.classList.remove('hidden');
    detailsContainer.classList.remove('hidden');

    summaryContainer.innerHTML = renderSummary(data);
    detailsContainer.innerHTML = renderDetails(data);

    const downloadBtn = document.getElementById('download-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadReport);
    }
}

function renderSummary(data) {
    const { ats_score } = data;
    const score = ats_score.total_score;
    const skillMatchScore = ats_score.breakdown.skill_match;
    let scoreColor = score > 85 ? 'text-green-400' : score > 70 ? 'text-yellow-400' : 'text-orange-400';

    return `
        <div class="bg-slate-800 p-6 rounded-2xl shadow-lg flex flex-col items-center justify-center fade-in">
            <h2 class="text-lg font-semibold text-slate-400 mb-4">Overall ATS Score</h2>
            <div class="relative w-40 h-40">
                <svg class="w-full h-full" viewBox="0 0 100 100" style="transform: rotate(-90deg);">
                    <circle class="text-slate-700" stroke-width="10" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" />
                    <circle class="progress-animate ${scoreColor}" stroke-width="10" stroke-dasharray="283" stroke-dashoffset="${283 * (1 - score / 100)}" stroke-linecap="round" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" />
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

function renderDetails(data) {
    const { suggestions, ats_score, skill_levels, parsed_data } = data;
    const { matched, missing } = ats_score.skill_gap || { matched: [], missing: [] };
    
    // Generate AI suggestions HTML
    const suggestionsHTML = suggestions && suggestions.length > 0 
        ? suggestions.map(s => `<li class="mb-2">${s}</li>`).join('')
        : '<li>No specific suggestions available at this time.</li>';

    // Generate skill gap analysis HTML
    const matchedSkillsHTML = matched && matched.length > 0 
        ? matched.map(skill => `<li class="text-green-300">${skill}</li>`).join('')
        : '<li class="text-slate-500">No skills matched</li>';
        
    const missingSkillsHTML = missing && missing.length > 0 
        ? missing.map(skill => `<li class="text-red-300">${skill}</li>`).join('')
        : '<li class="text-slate-500">No skills missing - perfect match!</li>';

    // Generate skill proficiency HTML
    let proficiencyHTML = '';
    if (skill_levels && Object.keys(skill_levels).length > 0) {
        proficiencyHTML = Object.entries(skill_levels).map(([skill, level]) => 
            `<li class="flex justify-between"><span>${skill}</span><span class="font-semibold ${getProficiencyColor(level)}">${level}</span></li>`
        ).join('');
    } else {
        proficiencyHTML = '<li class="text-slate-500">No skill proficiency data available</li>';
    }

    // Generate experience HTML
    const experienceHTML = (parsed_data?.experience ?? []).length > 0
        ? parsed_data.experience.map(exp => `
            <div class="p-4 rounded-lg bg-slate-700/50 mb-3">
                <p class="font-bold text-white">${exp.title || 'Untitled Role'} <span class="font-normal text-slate-400">at ${exp.company || 'Unknown Company'}</span></p>
                <p class="text-sm text-slate-400 mt-1">${(exp.description || "").substring(0, 200)}...</p>
            </div>`).join('')
        : '<p class="text-slate-500 text-sm">No structured work experience was parsed.</p>';

    // Generate projects HTML
    const projectsHTML = (parsed_data?.projects ?? []).length > 0
        ? parsed_data.projects.map(p => `
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
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- AI Suggestions and Download -->
            <div class="md:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.2s;">
                <h2 class="text-xl font-bold text-white mb-4">AI-Powered Suggestions</h2>
                <ul class="space-y-2 list-disc list-inside pl-5 text-slate-300">
                    ${suggestionsHTML}
                </ul>
                <div class="mt-6 text-center">
                    <button id="download-btn" class="bg-sky-600 hover:bg-sky-500 text-white font-bold py-3 px-6 rounded-lg transition-transform transform hover:scale-105">
                        Download Summary (PDF)
                    </button>
                </div>
            </div>

            <!-- Skill Gap Analysis -->
            <div class="md:col-span-2 bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.3s;">
                <h2 class="text-xl font-bold text-white mb-4">Comprehensive Skill Gap Analysis</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h3 class="text-lg font-semibold text-green-400 mb-3">✅ Matched Skills</h3>
                        <ul class="space-y-1">
                            ${matchedSkillsHTML}
                        </ul>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-red-400 mb-3">❌ Missing Skills</h3>
                        <ul class="space-y-1">
                            ${missingSkillsHTML}
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Skill Proficiency -->
            <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.4s;">
                <h2 class="text-xl font-bold text-white mb-4">Rated Skill Proficiency</h2>
                <ul class="space-y-2">
                    ${proficiencyHTML}
                </ul>
            </div>

            <!-- Experience -->
            <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.5s;">
                <h2 class="text-xl font-bold text-white mb-4">Work Experience</h2>
                <div class="space-y-3">
                    ${experienceHTML}
                </div>
            </div>

            <!-- Projects -->
            <div class="bg-slate-800 p-6 rounded-2xl shadow-lg fade-in" style="animation-delay: 0.6s;">
                <h2 class="text-xl font-bold text-white mb-4">Projects</h2>
                <div class="space-y-3">
                    ${projectsHTML}
                </div>
            </div>
        </div>
    `;
}

// Helper functions
function getProficiencyColor(level) {
    switch(level.toLowerCase()) {
        case 'expert': return 'text-purple-400';
        case 'advanced': return 'text-blue-400';
        case 'intermediate': return 'text-green-400';
        default: return 'text-yellow-400';
    }
}

function getRelevanceColor(score) {
    if (score >= 80) return 'bg-green-500/20 text-green-300';
    if (score >= 60) return 'bg-blue-500/20 text-blue-300';
    if (score >= 40) return 'bg-yellow-500/20 text-yellow-300';
    return 'bg-red-500/20 text-red-300';
}

async function downloadReport() {
    const form = document.getElementById('upload-form');
    if (!form.checkValidity()) {
        alert("Please provide both a resume and job description to download a report.");
        return;
    }
    const formData = new FormData(form);
    
    const button = document.getElementById('download-btn');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = 'Generating...';

    try {
        const response = await fetch('/download-report/', { method: 'POST', body: formData });
        if (!response.ok) throw new Error('Failed to generate report.');
        
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
        button.disabled = false;
        button.innerHTML = originalText;
    }
}