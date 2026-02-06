/**
 * Tıp & Yapay Zeka Tez Detay Sistemi
 * Frontend JavaScript
 */

const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const thesisForm = document.getElementById('thesisForm');
const thesisNumberInput = document.getElementById('thesisNumber');
const loadingIndicator = document.getElementById('loadingIndicator');
const thesisDetails = document.getElementById('thesisDetails');
const detailsContainer = document.getElementById('detailsContainer');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Tıp & Yapay Zeka Tez Detay Sistemi başlatıldı');

    // Form submit event
    thesisForm.addEventListener('submit', handleFormSubmit);
});

/**
 * Handle form submission
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
    loadThesisDetails(thesisId);
}

/**
 * Load thesis details from API
 */
async function loadThesisDetails(thesisId) {
    try {
        // Hide previous results and errors
        hideError();
        thesisDetails.classList.add('hidden');

        // Show loading
        loadingIndicator.classList.remove('hidden');

        // Fetch thesis details
        const response = await fetch(`${API_BASE_URL}/api/thesis/${thesisId}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: Tez detayları alınamadı`);
        }

        const data = await response.json();

        // Check if thesis was actually found
        if (data.title === "Detaylar yüklenemedi" || data.author === "Bilinmiyor") {
            loadingIndicator.classList.add('hidden');
            showError(`
                <strong>Tez bulunamadı: ${thesisId}</strong><br><br>
                Bu tez numarası YÖK sisteminde bulunamadı.<br><br>
                <strong>Olası nedenler:</strong><br>
                • Tez numarası yanlış yazılmış olabilir<br>
                • Tez henüz YÖK sistemine kayıt edilmemiş olabilir<br>
                • Tez gizli/erişime kapalı olabilir<br><br>
                <strong>Örnek tez numaraları:</strong><br>
                <button onclick="quickLoadThesis('962889')" class="text-purple-600 underline hover:text-purple-800">962889</button>,
                <button onclick="quickLoadThesis('981536')" class="text-purple-600 underline hover:text-purple-800">981536</button>,
                <button onclick="quickLoadThesis('976617')" class="text-purple-600 underline hover:text-purple-800">976617</button>,
                <button onclick="quickLoadThesis('979219')" class="text-purple-600 underline hover:text-purple-800">979219</button>
            `);
            return;
        }

        // Display thesis details
        displayThesisDetails(data);

        // Hide loading
        loadingIndicator.classList.add('hidden');

        // Scroll to results
        thesisDetails.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Tez detayları yüklenirken hata:', error);
        loadingIndicator.classList.add('hidden');
        showError(`Tez detayları yüklenirken hata oluştu: ${error.message}`);
    }
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
                // Abstract in its own section
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
                // Highlighted title
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
                // Keywords as tags
                const keywords = field.value.split(',').map(k => k.trim()).filter(k => k);
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
                // Regular field
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

    // Add action buttons
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

/**
 * Print thesis details
 */
function printThesis() {
    window.print();
}

/**
 * Show error message
 */
function showError(message) {
    errorText.innerHTML = message;  // Changed to innerHTML to support HTML
    errorMessage.classList.remove('hidden');
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.classList.add('hidden');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        'bg-blue-500'
    } text-white font-semibold`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Global functions for onclick handlers
window.quickLoadThesis = quickLoadThesis;
window.printThesis = printThesis;
