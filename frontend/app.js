/**
 * Tıp & Yapay Zeka Tez Detay Sistemi
 * Frontend JavaScript
 */

const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const thesisForm = document.getElementById('thesisForm');
const thesisNumberInput = document.getElementById('thesisNumber');
const advancedSearchForm = document.getElementById('advancedSearchForm');
const loadingIndicator = document.getElementById('loadingIndicator');
const loadingText = document.getElementById('loadingText');
const thesisDetails = document.getElementById('thesisDetails');
const detailsContainer = document.getElementById('detailsContainer');
const searchResults = document.getElementById('searchResults');
const resultsTableBody = document.getElementById('resultsTableBody');
const resultCount = document.getElementById('resultCount');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

// Pagination state
let allResults = [];
let totalFound = 0;
let currentPage = 1;
let pageSize = 50;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Tıp & Yapay Zeka Tez Detay Sistemi başlatıldı');

    thesisForm.addEventListener('submit', handleFormSubmit);
    advancedSearchForm.addEventListener('submit', handleAdvancedSearch);

    populateYearSelects();
});

/**
 * Populate year select dropdowns (2026 to 1980)
 */
function populateYearSelects() {
    const yearFrom = document.getElementById('yearFrom');
    const yearTo = document.getElementById('yearTo');
    const currentYear = new Date().getFullYear();

    for (let y = currentYear; y >= 1980; y--) {
        yearFrom.add(new Option(y, y));
        yearTo.add(new Option(y, y));
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    document.getElementById(`tab-${tabName}`).classList.add('active');

    const buttons = document.querySelectorAll('.tab-btn');
    if (tabName === 'tezNo') {
        buttons[0].classList.add('active');
    } else {
        buttons[1].classList.add('active');
    }

    hideError();
    searchResults.classList.add('hidden');
    thesisDetails.classList.add('hidden');
}

/**
 * Handle thesis number form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    const thesisNumber = thesisNumberInput.value.trim();

    if (!thesisNumber) {
        showError('Lütfen bir tez numarası giriniz');
        return;
    }

    await loadThesisDetails(thesisNumber);
}

/**
 * Quick load thesis from example buttons
 */
function quickLoadThesis(thesisId) {
    thesisNumberInput.value = thesisId;
    switchTab('tezNo');
    loadThesisDetails(thesisId);
}

/**
 * Load thesis details from API
 */
async function loadThesisDetails(thesisId) {
    try {
        hideError();
        thesisDetails.classList.add('hidden');
        searchResults.classList.add('hidden');

        loadingText.textContent = 'Tez detayları getiriliyor...';
        loadingIndicator.classList.remove('hidden');

        const response = await fetch(`${API_BASE_URL}/api/thesis/${thesisId}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: Tez detayları alınamadı`);
        }

        const data = await response.json();

        if (data.title === "Detaylar yüklenemedi" || data.author === "Bilinmiyor") {
            loadingIndicator.classList.add('hidden');
            showError(`
                <strong>Tez bulunamadı: ${thesisId}</strong><br><br>
                Bu tez numarası YÖK sisteminde bulunamadı.<br><br>
                <strong>Olası nedenler:</strong><br>
                &bull; Tez numarası yanlış yazılmış olabilir<br>
                &bull; Tez henüz YÖK sistemine kayıt edilmemiş olabilir
            `);
            return;
        }

        displayThesisDetails(data);
        loadingIndicator.classList.add('hidden');
        thesisDetails.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Tez detayları yüklenirken hata:', error);
        loadingIndicator.classList.add('hidden');
        showError(`Tez detayları yüklenirken hata oluştu: ${error.message}`);
    }
}

/**
 * Handle advanced search form submission
 */
async function handleAdvancedSearch(e) {
    e.preventDefault();

    const params = {
        keyword1: document.getElementById('keyword1').value.trim(),
        searchField1: document.getElementById('searchField1').value,
        searchType1: document.getElementById('searchType1').value,
        operator2: document.getElementById('operator2').value,
        keyword2: document.getElementById('keyword2').value.trim(),
        searchField2: document.getElementById('searchField2').value,
        searchType2: document.getElementById('searchType2').value,
        operator3: document.getElementById('operator3').value,
        keyword3: document.getElementById('keyword3').value.trim(),
        searchField3: document.getElementById('searchField3').value,
        searchType3: document.getElementById('searchType3').value,
        yearFrom: document.getElementById('yearFrom').value,
        yearTo: document.getElementById('yearTo').value,
        thesisType: document.getElementById('thesisType').value,
        permissionStatus: document.getElementById('permissionStatus').value,
        groupType: document.getElementById('groupType').value,
        language: document.getElementById('language').value,
        status: document.getElementById('status').value,
        university: document.getElementById('university').value.trim(),
        institute: document.getElementById('institute').value.trim(),
    };

    if (!params.keyword1 && !params.yearFrom && !params.thesisType && !params.university) {
        showError('Lütfen en az bir arama kriteri giriniz (anahtar kelime, yıl, tez türü veya üniversite)');
        return;
    }

    try {
        hideError();
        thesisDetails.classList.add('hidden');
        searchResults.classList.add('hidden');

        loadingText.textContent = 'Gelişmiş arama yapılıyor...';
        loadingIndicator.classList.remove('hidden');

        const response = await fetch(`${API_BASE_URL}/api/advanced-search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: Arama yapılamadı`);
        }

        const data = await response.json();
        loadingIndicator.classList.add('hidden');

        if (data.results && data.results.length > 0) {
            allResults = data.results;
            totalFound = data.total_found || data.results.length;
            currentPage = 1;
            pageSize = parseInt(document.getElementById('pageSize').value);
            renderResults();
        } else {
            showError('Arama kriterlerine uygun sonuç bulunamadı. Lütfen farklı kriterlerle deneyin.');
        }

    } catch (error) {
        console.error('Gelişmiş arama hatası:', error);
        loadingIndicator.classList.add('hidden');
        showError(`Arama sırasında hata oluştu: ${error.message}`);
    }
}

/**
 * Render current page of results + pagination controls
 */
function renderResults() {
    const totalPages = Math.ceil(allResults.length / pageSize);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * pageSize;
    const end = Math.min(start + pageSize, allResults.length);
    const pageResults = allResults.slice(start, end);

    // Update header count
    if (totalFound > allResults.length) {
        resultCount.textContent = `${allResults.length} / ${totalFound} sonuç`;
    } else {
        resultCount.textContent = `${allResults.length} sonuç`;
    }

    // Render table rows
    let html = '';
    pageResults.forEach((r, idx) => {
        const globalIdx = start + idx + 1;
        html += `
            <tr>
                <td>${globalIdx}</td>
                <td>
                    <span class="thesis-id-link" onclick="loadThesisDetails('${escapeHtml(r.thesis_id)}')">${escapeHtml(r.thesis_id)}</span>
                </td>
                <td>${escapeHtml(r.author || '')}</td>
                <td>${escapeHtml(r.year || '')}</td>
                <td>
                    ${escapeHtml(r.title || '')}
                    ${r.title_tr ? '<br><span class="text-gray-500 italic text-xs">' + escapeHtml(r.title_tr) + '</span>' : ''}
                </td>
                <td>${escapeHtml(r.thesis_type || '')}</td>
                <td class="text-xs">${escapeHtml(r.subject || '')}</td>
            </tr>
        `;
    });
    resultsTableBody.innerHTML = html;

    // Page info
    document.getElementById('pageInfo').textContent =
        `${start + 1}-${end} arası gösteriliyor (toplam ${allResults.length})`;

    // Render pagination buttons
    renderPagination(totalPages);

    searchResults.classList.remove('hidden');
    searchResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Render pagination buttons
 */
function renderPagination(totalPages) {
    const container = document.getElementById('pageButtons');

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    // Previous
    html += `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
        <i class="fas fa-chevron-left text-xs"></i>
    </button>`;

    // Page numbers with ellipsis
    const pages = getPageNumbers(currentPage, totalPages);
    pages.forEach(p => {
        if (p === '...') {
            html += `<span class="px-1 text-gray-400">...</span>`;
        } else {
            html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
        }
    });

    // Next
    html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
        <i class="fas fa-chevron-right text-xs"></i>
    </button>`;

    container.innerHTML = html;
}

/**
 * Get page numbers to display with ellipsis
 */
function getPageNumbers(current, total) {
    if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages = [];

    // Always show first page
    pages.push(1);

    if (current > 3) {
        pages.push('...');
    }

    // Pages around current
    const rangeStart = Math.max(2, current - 1);
    const rangeEnd = Math.min(total - 1, current + 1);

    for (let i = rangeStart; i <= rangeEnd; i++) {
        pages.push(i);
    }

    if (current < total - 2) {
        pages.push('...');
    }

    // Always show last page
    if (total > 1) {
        pages.push(total);
    }

    return pages;
}

/**
 * Navigate to a specific page
 */
function goToPage(page) {
    const totalPages = Math.ceil(allResults.length / pageSize);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderResults();
}

/**
 * Handle page size change
 */
function changePageSize() {
    pageSize = parseInt(document.getElementById('pageSize').value);
    currentPage = 1;
    renderResults();
}

/**
 * Close thesis details and show results again
 */
function closeThesisDetails() {
    thesisDetails.classList.add('hidden');
    if (!searchResults.classList.contains('hidden')) {
        searchResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Clear advanced search form
 */
function clearAdvancedSearch() {
    advancedSearchForm.reset();
    hideError();
    searchResults.classList.add('hidden');
    thesisDetails.classList.add('hidden');
    allResults = [];
    totalFound = 0;
    currentPage = 1;
}

/**
 * Display thesis details
 */
function displayThesisDetails(thesis) {
    const fields = [
        { label: 'Tez No', value: thesis.thesis_id, icon: 'fa-hashtag' },
        { label: 'Tez Adı', value: thesis.title, icon: 'fa-file-alt', highlight: true },
        { label: 'Yazar', value: thesis.author, icon: 'fa-user' },
        { label: 'Danışman', value: thesis.advisor, icon: 'fa-user-tie' },
        { label: 'Eş Danışman', value: thesis.co_advisor, icon: 'fa-user-friends' },
        { label: 'Yıl', value: thesis.year, icon: 'fa-calendar' },
        { label: 'Üniversite', value: thesis.university, icon: 'fa-university' },
        { label: 'Enstitü', value: thesis.institute, icon: 'fa-building' },
        { label: 'Anabilim Dalı', value: thesis.department, icon: 'fa-graduation-cap' },
        { label: 'Tez Türü', value: thesis.thesis_type, icon: 'fa-book' },
        { label: 'Dil', value: thesis.language, icon: 'fa-language' },
        { label: 'Sayfa Sayısı', value: thesis.page_count, icon: 'fa-file' },
        { label: 'Anahtar Kelimeler', value: thesis.keywords, icon: 'fa-tags', keywords: true },
        { label: 'Özet', value: thesis.abstract, icon: 'fa-align-left', isAbstract: true }
    ];

    let html = '<div class="space-y-6">';

    fields.forEach(field => {
        if (field.value) {
            if (field.isAbstract) {
                html += `
                    <div class="border-t pt-6">
                        <h4 class="text-lg font-bold text-gray-800 mb-4 flex items-center">
                            <i class="fas ${field.icon} mr-2 text-purple-600"></i>
                            ${field.label}
                        </h4>
                        <div class="bg-gray-50 rounded-lg p-6 text-gray-700 leading-relaxed whitespace-pre-wrap">
                            ${escapeHtml(field.value)}
                        </div>
                    </div>
                `;
            } else if (field.highlight) {
                html += `
                    <div class="bg-purple-50 rounded-lg p-6 border-l-4 border-purple-600">
                        <div class="flex items-start">
                            <i class="fas ${field.icon} text-purple-600 text-xl mr-4 mt-1"></i>
                            <div class="flex-1">
                                <div class="text-sm font-semibold text-purple-800 mb-2">${field.label}</div>
                                <div class="text-lg font-bold text-gray-800">${escapeHtml(field.value)}</div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (field.keywords) {
                const keywords = field.value.split(';').map(k => k.trim()).filter(k => k);
                html += `
                    <div class="flex items-start">
                        <div class="detail-label flex items-center">
                            <i class="fas ${field.icon} mr-2 text-purple-600"></i>
                            ${field.label}
                        </div>
                        <div class="flex-1 flex flex-wrap gap-2">
                            ${keywords.map(keyword => `
                                <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                                    ${escapeHtml(keyword)}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else {
                html += `
                    <div class="flex items-start">
                        <div class="detail-label flex items-center">
                            <i class="fas ${field.icon} mr-2 text-purple-600"></i>
                            ${field.label}
                        </div>
                        <div class="flex-1 detail-value">${escapeHtml(field.value)}</div>
                    </div>
                `;
            }
        }
    });

    html += '</div>';

    html += `
        <div class="mt-8 pt-6 border-t flex flex-wrap gap-4">
            <a href="https://tez.yok.gov.tr/UlusalTezMerkezi/tezDetay.jsp?id=${thesis.thesis_id}"
               target="_blank"
               class="flex-1 bg-purple-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-purple-700 transition text-center">
                <i class="fas fa-external-link-alt mr-2"></i>
                YÖK'te Görüntüle
            </a>
            <button onclick="printThesis()"
                    class="flex-1 bg-gray-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-700 transition">
                <i class="fas fa-print mr-2"></i>
                Yazdır
            </button>
        </div>
    `;

    detailsContainer.innerHTML = html;
    thesisDetails.classList.remove('hidden');
}

function printThesis() { window.print(); }

function showError(message) {
    errorText.innerHTML = message;
    errorMessage.classList.remove('hidden');
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Global functions for onclick handlers
window.quickLoadThesis = quickLoadThesis;
window.printThesis = printThesis;
window.switchTab = switchTab;
window.clearAdvancedSearch = clearAdvancedSearch;
window.closeThesisDetails = closeThesisDetails;
window.loadThesisDetails = loadThesisDetails;
window.goToPage = goToPage;
window.changePageSize = changePageSize;
