/**
 * 3D Print Calc Pro - Main Application Controller
 */

const state = {
    user: null,
    printers: [],
    filaments: [],
    projects: [],
    currentProject: null,
    currentPlates: [],
    currentBOM: [],
    activeView: 'dashboard',
    dashboardStats: null,
    projectSortField: 'id',
    projectSortAsc: false,
    charts: {
        statusFunnel: null,
        financialTimeline: null,
        costBreakdown: null,
        topProjects: null,
    },
};

// ================= UTILITIES & HELPERS =================

// Auto-select text on focus (Tab navigation or click) for all inputs and textareas
document.addEventListener('focus', (e) => {
    const el = e.target;
    if (el.tagName === 'INPUT' && el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'color') {
        requestAnimationFrame(() => el.select());
    } else if (el.tagName === 'TEXTAREA') {
        requestAnimationFrame(() => el.select());
    }
}, true);

// Syncs the native `title` tooltip of a <select> with its currently selected option text.
function syncSelectTitle(sel) {
    const opt = sel.options[sel.selectedIndex];
    sel.title = opt ? opt.text.trim() : '';
}

/**
 * Cleans slicer profile names by removing embedded project/file references,
 * e.g. "3D Prime PLA Basic(patolino-kratos.3mf)" -> "3D Prime PLA Basic"
 */
function cleanFilamentProfileName(profile, fileName = '') {
    if (!profile || typeof profile !== 'string') return '';
    let cleaned = profile.trim().replace(/^["']|["']$/g, '');
    cleaned = cleaned.replace(/\s*[\(\[][^()\[\]]*\.[a-z0-9_-]{2,6}\s*[\)\]]/gi, '');
    if (fileName && typeof fileName === 'string') {
        const base = fileName.replace(/^.*[\\\/]/, '').replace(/\.(?:gcode\.3mf|3mf|gcode|stl|step|stp|obj)$/i, '').trim();
        if (base && base.length >= 2) {
            const escaped = base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            cleaned = cleaned.replace(new RegExp(`\\s*[\\(\\[]\\s*${escaped}(?:\\.[^()\\[\\]]+)?\\s*[\\)\\]]`, 'gi'), '');
        }
    }
    cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
    return cleaned;
}

// Map filament color name or hex code to a native colored circle emoji
function getFilamentColorDot(colorHex, colorName = '') {
    const hex = (colorHex || '').toLowerCase();
    const name = (colorName || '').toLowerCase();

    if (name.includes('preto') || name.includes('black') || hex === '#000000' || hex === '#0f172a' || hex === '#1e293b') return '⬛';
    if (name.includes('branco') || name.includes('white') || hex === '#ffffff' || hex === '#f8fafc') return '⚪';
    if (name.includes('vermelho') || name.includes('red') || hex.startsWith('#ef') || hex.startsWith('#f871') || hex.startsWith('#dc')) return '🔴';
    if (name.includes('verde') || name.includes('green') || hex.startsWith('#10') || hex.startsWith('#22') || hex.startsWith('#05')) return '🟢';
    if (name.includes('azul') || name.includes('blue') || hex.startsWith('#3b') || hex.startsWith('#25') || hex.startsWith('#02') || hex.startsWith('#028')) return '🔵';
    if (name.includes('amarelo') || name.includes('dourado') || name.includes('yellow') || name.includes('gold') || hex.startsWith('#ea') || hex.startsWith('#f5') || hex.startsWith('#eab')) return '🟡';
    if (name.includes('roxo') || name.includes('purple') || name.includes('violet') || hex.startsWith('#a8') || hex.startsWith('#8b') || hex.startsWith('#7c')) return '🟣';
    if (name.includes('rosa') || name.includes('pink') || hex.startsWith('#ec') || hex.startsWith('#f4') || hex.startsWith('#db')) return '🩷';
    if (name.includes('laranja') || name.includes('orange') || hex.startsWith('#f9') || hex.startsWith('#ea5')) return '🟧';
    if (name.includes('marrom') || name.includes('brown') || name.includes('bege') || hex.startsWith('#78') || hex.startsWith('#92')) return '🟤';

    return '🟢'; // default fallback
}

// Find best matching inventory filament for a plate based on profile, material, color, and name
function findBestMatchingFilament(filaments, plateName = '', slicerProfile = '', filamentType = '', hexColor = '') {
    if (!filaments || filaments.length === 0) return null;

    const norm = (s) => (s ? String(s).toLowerCase().replace(/[^a-z0-9]/g, '') : '');
    const profNorm = norm(slicerProfile);
    const nameNorm = norm(plateName);
    const typeNorm = norm(filamentType);
    const hexNorm = norm(hexColor);

    const colorMatches = (fColor) => {
        if (!fColor) return false;
        const cNorm = norm(fColor);
        if (cNorm && (cNorm.includes(nameNorm) || nameNorm.includes(cNorm))) return true;
        const parts = String(fColor).toLowerCase().split(/[\s\-_]+/).map(p => norm(p)).filter(p => p.length >= 3);
        return parts.some(p => nameNorm.includes(p));
    };

    // 1. Highest priority: Brand match + Material match + Color match (from plate name or hex)
    for (const f of filaments) {
        const fBrand = norm(f.brand);
        const fMat = norm(f.material);
        if (fBrand && fMat && (profNorm.includes(fBrand) || fBrand.includes(profNorm)) && (profNorm.includes(fMat) || typeNorm.includes(fMat))) {
            if (colorMatches(f.color) || (hexNorm && norm(f.color_hex) === hexNorm)) {
                return f;
            }
        }
    }

    // 2. Material + Color match (e.g. if brand in slicer doesn't match catalog brand, but material & color match)
    for (const f of filaments) {
        const fMat = norm(f.material);
        if (fMat && (profNorm.includes(fMat) || typeNorm.includes(fMat))) {
            if (colorMatches(f.color) || (hexNorm && norm(f.color_hex) === hexNorm)) {
                return f;
            }
        }
    }

    // 3. Brand + Material match
    for (const f of filaments) {
        const fBrand = norm(f.brand);
        const fMat = norm(f.material);
        if (fBrand && fMat && (profNorm.includes(fBrand) || fBrand.includes(profNorm)) && (profNorm.includes(fMat) || typeNorm.includes(fMat))) {
            return f;
        }
    }

    // 4. Full profile name matches filament name or vice versa
    for (const f of filaments) {
        const fName = norm(f.name);
        if (fName && (profNorm.includes(fName) || fName.includes(profNorm))) {
            return f;
        }
    }

    // 5. Material match
    if (typeNorm) {
        const types = filamentType.split(',').map(s => norm(s)).filter(Boolean);
        for (const f of filaments) {
            const fMat = norm(f.material);
            if (fMat && types.includes(fMat)) {
                return f;
            }
        }
    }

    // Fallback: no match found
    return null;
}


// Wrap all <select> elements with .select-wrap so the CSS fade gradient works.
// Skips selects already inside .select-wrap or .relative (filament dot wrapper).
function wrapSelectsWithFade(root = document) {
    root.querySelectorAll('select').forEach(sel => {
        const parent = sel.parentElement;
        // Always keep the title in sync (covers re-runs after dynamic renders)
        syncSelectTitle(sel);
        if (!parent || parent.classList.contains('select-wrap')) return;
        // The filament selector already sits inside a `relative` div — add the class there
        if (parent.classList.contains('relative')) {
            parent.classList.add('select-wrap');
            return;
        }
        // Wrap bare selects
        const wrapper = document.createElement('div');
        wrapper.className = 'select-wrap';
        parent.insertBefore(wrapper, sel);
        wrapper.appendChild(sel);
    });
}

// Run once on DOM ready, then watch for dynamically added selects
document.addEventListener('DOMContentLoaded', () => wrapSelectsWithFade());

// Keep title in sync whenever the user picks a new option
document.addEventListener('change', (e) => {
    if (e.target.tagName === 'SELECT') syncSelectTitle(e.target);
}, true);

// MutationObserver: re-wrap whenever new nodes are injected (e.g. plate cards)
if (typeof MutationObserver !== 'undefined' && typeof document !== 'undefined' && document.body) {
    new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.addedNodes.length) wrapSelectsWithFade(document);
        }
    }).observe(document.body, { childList: true, subtree: true });
}


function formatCurrency(val) {
    const num = Number(val) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDisplayHours(hours) {
    const h = parseFloat(hours) || 0;
    if (h <= 0) return '0.0 h';
    if (h < 0.1) {
        const mins = Math.round(h * 60);
        return mins < 1 ? `<1 min (~${Math.max(1, Math.round(h * 3600))}s)` : `${mins} min`;
    }
    return `${h.toFixed(1)} h`;
}
window.formatDisplayHours = formatDisplayHours;

function parseLocaleFloat(val, fallback = 0) {
    if (val === null || val === undefined || val === '') return fallback;
    if (typeof val === 'number') return isNaN(val) ? fallback : val;

    let str = String(val).trim();
    // Strip non-numeric prefixes like R$, $, etc.
    str = str.replace(/^[^\d\-+]+/, '');
    if (!str) return fallback;

    const lastDot = str.lastIndexOf('.');
    const lastComma = str.lastIndexOf(',');
    if (lastDot !== -1 && lastComma !== -1) {
        if (lastComma > lastDot) {
            // Brazilian format: 1.234,56 -> remove dots, replace comma with dot
            str = str.replace(/\./g, '').replace(',', '.');
        } else {
            // US format: 1,234.56 -> remove commas
            str = str.replace(/,/g, '');
        }
    } else if (lastComma !== -1) {
        // Comma only (e.g. 56,50)
        str = str.replace(',', '.');
    }

    const num = parseFloat(str);
    return isNaN(num) ? fallback : num;
}

function normalizeSearchText(str) {
    return (str || '')
        .toString()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

function matchesSearch(text, term) {
    const normTerm = normalizeSearchText(term);
    if (!normTerm) return true;
    const normText = normalizeSearchText(text);
    if (normText.includes(normTerm)) return true;
    const words = normTerm.split(/\s+/).filter(Boolean);
    return words.every(word => normText.includes(word));
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
window.escapeHtml = escapeHtml;

// Issue #27 & #31: Dynamic phone masking for commercial phones and WhatsApp (with +55/55 DDI sanitization)
function formatPhoneInput(value) {
    if (!value) return '';
    let digits = String(value).replace(/\D/g, '');
    if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) {
        digits = digits.slice(2);
    }
    digits = digits.slice(0, 11);
    if (digits.length <= 2) {
        return digits.length > 0 ? `(${digits}` : '';
    }
    if (digits.length <= 6) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    }
    if (digits.length <= 10) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7, 11)}`;
}
window.formatPhoneInput = formatPhoneInput;

function attachPhoneMask(inputEl) {
    if (!inputEl) return;
    inputEl.addEventListener('input', (e) => {
        const val = e.target.value;
        const formatted = formatPhoneInput(val);
        if (formatted !== val) {
            e.target.value = formatted;
        }
    });
}
window.attachPhoneMask = attachPhoneMask;

// Global enhancement for numeric inputs: allows seamless decimal input with comma or dot across all browser locales
// Avoids HTML5 value sanitization wiping out trailing-dot values (e.g. '56.')
document.addEventListener('focusin', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && target.type === 'number') {
        target.dataset.originalType = 'number';
        target.type = 'text';
        target.inputMode = 'decimal';
    }
});

document.addEventListener('focusout', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && target.dataset.originalType === 'number') {
        if (target.value && target.value.trim() !== '') {
            const parsed = parseLocaleFloat(target.value, null);
            if (parsed !== null && !isNaN(parsed)) {
                target.value = parsed;
            }
        }
        target.type = 'number';
        delete target.dataset.originalType;
        target.dispatchEvent(new Event('change', { bubbles: true }));
    }
});

document.addEventListener('beforeinput', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && (target.type === 'number' || target.dataset.originalType === 'number')) {
        if (e.data === ',') {
            if (target.type === 'number') {
                target.dataset.originalType = 'number';
                target.type = 'text';
                target.inputMode = 'decimal';
            }
            if ((target.value.includes(',') || target.value.includes('.')) && !window.getSelection()?.toString()) {
                e.preventDefault();
            }
        }
    }
});

document.addEventListener('keydown', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && (target.type === 'number' || target.dataset.originalType === 'number')) {
        if (e.key === ',' || e.key === 'Decimal') {
            if (target.type === 'number') {
                target.dataset.originalType = 'number';
                target.type = 'text';
                target.inputMode = 'decimal';
            }
            if ((target.value.includes(',') || target.value.includes('.')) && !window.getSelection()?.toString()) {
                e.preventDefault();
            }
        }
    }
});

document.addEventListener('paste', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && (target.type === 'number' || target.dataset.originalType === 'number')) {
        const text = (e.clipboardData || window.clipboardData)?.getData('text');
        if (text && (text.includes(',') || text.includes('R$') || text.includes('.'))) {
            const val = parseLocaleFloat(text, null);
            if (val !== null && !isNaN(val)) {
                e.preventDefault();
                target.value = val;
                target.dispatchEvent(new Event('input', { bubbles: true }));
                target.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    }
});

function normalizeNumericInputs() {
    document.querySelectorAll('input[data-original-type="number"]').forEach(inp => {
        if (inp.value && inp.value.trim() !== '') {
            const parsed = parseLocaleFloat(inp.value, null);
            if (parsed !== null && !isNaN(parsed)) inp.value = parsed;
        }
        inp.type = 'number';
        delete inp.dataset.originalType;
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-600 text-white border-emerald-500',
        error: 'bg-red-600 text-white border-red-500',
        info: 'bg-blue-600 text-white border-blue-500',
    };

    const toast = document.createElement('div');
    toast.className = `p-3 rounded-lg border shadow-lg text-xs font-semibold flex items-center gap-2 pointer-events-auto transition-all transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    const textSpan = document.createElement('span');
    textSpan.textContent = String(message ?? '');
    toast.appendChild(textSpan);
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// ================= ROUTING & NAVIGATION =================

function getRouteFromHash() {
    if (typeof window === 'undefined' || !window.location || typeof window.location.hash !== 'string') {
        return { view: 'dashboard', params: {} };
    }
    const hashStr = window.location.hash.replace(/^#\/?/, '').trim();
    if (!hashStr) {
        return { view: 'dashboard', params: {} };
    }
    const [viewPart, queryPart] = hashStr.split('?');
    const view = viewPart.toLowerCase();
    const validViews = ['dashboard', 'projects', 'project-editor', 'printers', 'filaments', 'settings'];
    const params = {};
    if (queryPart) {
        const searchParams = new URLSearchParams(queryPart);
        for (const [k, v] of searchParams.entries()) {
            params[k] = v;
        }
    }
    return {
        view: validViews.includes(view) ? view : 'dashboard',
        params
    };
}

async function applyRoute(route) {
    if (route.view === 'project-editor') {
        if (route.params.id) {
            const projId = parseInt(route.params.id, 10);
            if (!isNaN(projId)) {
                if (!state.currentProject || state.currentProject.id !== projId) {
                    await editProject(projId);
                    return;
                }
            }
        } else if (!state.currentProject && (!state.currentPlates || state.currentPlates.length === 0)) {
            openNewProject();
            return;
        }
    }
    navigateTo(route.view);
}

function navigateTo(viewName) {
    state.activeView = viewName;

    const views = ['dashboard', 'projects', 'project-editor', 'printers', 'filaments', 'settings'];
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.add('hidden');

        const navBtn = document.getElementById(`nav-${v}`);
        if (navBtn) {
            navBtn.classList.remove('bg-blue-600', 'text-white');
            navBtn.classList.add('text-slate-300');
        }
    });

    const activeEl = document.getElementById(`view-${viewName}`);
    if (activeEl) activeEl.classList.remove('hidden');

    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) {
        activeNav.classList.remove('text-slate-300');
        activeNav.classList.add('bg-blue-600', 'text-white');
    }

    const titles = {
        'dashboard': 'Visão Geral',
        'projects': 'Projetos & Orçamentos',
        'project-editor': 'Editar Orçamento',
        'printers': 'Minhas Impressoras',
        'filaments': 'Meus Filamentos',
        'settings': 'Configurações & Taxas',
    };
    const titleEl = document.getElementById('view-title');
    if (titleEl) titleEl.textContent = titles[viewName] || 'Painel';

    const defaultTopTitle = document.getElementById('topbar-default-title');
    const editorTopTitle = document.getElementById('topbar-editor-title');
    if (defaultTopTitle && editorTopTitle) {
        if (viewName === 'project-editor') {
            defaultTopTitle.classList.add('hidden');
            editorTopTitle.classList.remove('hidden');
            editorTopTitle.classList.add('flex');
            if (typeof refreshIcons === 'function') refreshIcons();
        } else {
            defaultTopTitle.classList.remove('hidden');
            editorTopTitle.classList.add('hidden');
            editorTopTitle.classList.remove('flex');
        }
    }

    // Reload views if needed
    if (viewName === 'dashboard') {
        loadDashboard();
    } else {
        destroyDashboardCharts();
    }
    if (viewName === 'projects') renderProjectsTable();
    if (viewName === 'printers') {
        const inp = document.getElementById('printer-search-input');
        if (inp) inp.value = '';
        const st = document.getElementById('printer-status-filter');
        if (st) st.value = 'all';
        renderPrintersGrid();
    }
    if (viewName === 'filaments') {
        const inp = document.getElementById('filament-search-input');
        if (inp) inp.value = '';
        const mat = document.getElementById('filament-material-filter');
        if (mat) mat.value = '';
        const st = document.getElementById('filament-status-filter');
        if (st) st.value = 'all';
        renderFilamentsGrid();
    }
    if (viewName === 'settings') populateSettingsForm();
    if (viewName === 'project-editor') {
        if (typeof requestAnimationFrame !== 'undefined') {
            requestAnimationFrame(() => updateSummaryPanelHeight());
        } else {
            updateSummaryPanelHeight();
        }
    }

    if (typeof initSmoothScroll === 'function') {
        initSmoothScroll();
    }
    const mainEl = typeof document.querySelector === 'function' ? document.querySelector('main') : null;
    if (mainEl && typeof mainEl.scrollTo === 'function') {
        mainEl.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Sync URL hash
    if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
        let targetHash = `#/${viewName}`;
        if (viewName === 'project-editor' && state.currentProject && state.currentProject.id) {
            targetHash = `#/${viewName}?id=${state.currentProject.id}`;
        }
        const currentRoute = getRouteFromHash();
        const currentId = currentRoute.params.id ? parseInt(currentRoute.params.id, 10) : null;
        const targetId = (viewName === 'project-editor' && state.currentProject?.id) ? state.currentProject.id : null;
        if (currentRoute.view !== viewName || currentId !== targetId) {
            window.location.hash = targetHash;
        }
    }

    refreshIcons();
}

if (typeof window !== 'undefined' && window.addEventListener) {
    window.addEventListener('hashchange', async () => {
        if (!state.user) return;
        const route = getRouteFromHash();
        const curId = route.params.id ? parseInt(route.params.id, 10) : null;
        const activeId = (state.activeView === 'project-editor' && state.currentProject?.id) ? state.currentProject.id : null;

        if (route.view !== state.activeView || (route.view === 'project-editor' && curId !== activeId)) {
            await applyRoute(route);
        }
    });
}

// ================= AUTH FLOWS =================

function switchAuthTab(tab) {
    const loginForm = document.getElementById('form-login');
    const regForm = document.getElementById('form-register');
    const loginBtn = document.getElementById('tab-login-btn');
    const regBtn = document.getElementById('tab-register-btn');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
        loginBtn.classList.add('border-blue-500', 'text-blue-400');
        loginBtn.classList.remove('border-transparent', 'text-slate-400');
        regBtn.classList.remove('border-blue-500', 'text-blue-400');
        regBtn.classList.add('border-transparent', 'text-slate-400');
    } else {
        loginForm.classList.add('hidden');
        regForm.classList.remove('hidden');
        regBtn.classList.add('border-blue-500', 'text-blue-400');
        regBtn.classList.remove('border-transparent', 'text-slate-400');
        loginBtn.classList.remove('border-blue-500', 'text-blue-400');
        loginBtn.classList.add('border-transparent', 'text-slate-400');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await API.auth.login(email, password);
        state.user = res.user;
        document.getElementById('auth-modal').classList.add('hidden');
        showToast('Login realizado com sucesso!', 'success');
        updateUserUI();
        await loadAllData();
        const route = getRouteFromHash();
        await applyRoute(route);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const company = document.getElementById('reg-company').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;

    try {
        const res = await API.auth.register(email, password, name, company);
        state.user = res.user;
        document.getElementById('auth-modal').classList.add('hidden');
        showToast('Conta criada com sucesso! Sua conta inicia 100% limpa.', 'success');
        updateUserUI();
        await loadAllData();
        navigateTo('dashboard');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function updateUserUI() {
    const nameEl = document.getElementById('user-display-name');
    const compEl = document.getElementById('user-display-company');
    const avatarEl = document.getElementById('user-avatar');

    if (!state.user) {
        if (nameEl) nameEl.textContent = '';
        if (compEl) compEl.textContent = '';
        if (avatarEl) avatarEl.textContent = '';
        return;
    }

    const displayName = state.user.full_name || state.user.email.split('@')[0];
    if (nameEl) nameEl.textContent = displayName;
    if (compEl) compEl.textContent = state.user.company_name || 'Profissional Autônomo';
    if (avatarEl) avatarEl.textContent = displayName.charAt(0).toUpperCase();
}

// ================= DATA LOADING =================

async function loadAllData() {
    try {
        const [printers, filaments, projects] = await Promise.all([
            API.printers.list(),
            API.filaments.list(),
            API.projects.list(),
        ]);
        state.printers = printers || [];
        state.filaments = filaments || [];
        state.projects = projects || [];
    } catch (err) {
        console.error("Erro carregando dados:", err);
    }
}

// ================= DASHBOARD & METRICS =================

async function loadDashboard() {
    await loadAllData();
    try {
        state.dashboardStats = await API.projects.getDashboardStats();
    } catch (e) {
        console.warn("Erro ao buscar dashboard stats:", e);
        state.dashboardStats = null;
    }
    renderDashboard();
}

function destroyDashboardCharts() {
    if (state.charts) {
        for (const key of Object.keys(state.charts)) {
            if (state.charts[key]) {
                try {
                    state.charts[key].destroy();
                } catch (e) {
                    console.warn("Erro destruindo gráfico:", e);
                }
                state.charts[key] = null;
            }
        }
    }
}

function clearUserData() {
    state.user = null;
    state.projects = [];
    state.printers = [];
    state.filaments = [];
    state.currentProject = null;
    state.currentPlates = [];
    state.currentBOM = [];
    state.dashboardStats = null;

    if (typeof destroyDashboardCharts === 'function') {
        destroyDashboardCharts();
    }

    updateUserUI();

    const projContainer = document.getElementById('projects-table-container');
    if (projContainer) projContainer.innerHTML = '';
    const recentTable = document.querySelector('#view-dashboard table tbody');
    if (recentTable) recentTable.innerHTML = '';
    const recentProjects = document.getElementById('dashboard-recent-projects');
    if (recentProjects) recentProjects.innerHTML = '';
    const printersGrid = document.getElementById('printers-grid');
    if (printersGrid) printersGrid.innerHTML = '';
    const filamentsGrid = document.getElementById('filaments-grid');
    if (filamentsGrid) filamentsGrid.innerHTML = '';

    if (typeof renderDashboard === 'function') {
        renderDashboard();
    }
}
window.clearUserData = clearUserData;

function renderDashboard() {
    const stats = state.dashboardStats;

    // 1. Update Operational Stat Counters
    const statProjects = document.getElementById('stat-projects-count');
    const statPrinters = document.getElementById('stat-printers-count');
    const statFilaments = document.getElementById('stat-filaments-count');
    const statActive = document.getElementById('stat-active-quotes');

    const totalProjects = stats ? stats.total_projects : (state.projects ? state.projects.length : 0);
    const totalPrinters = stats ? stats.total_printers : (state.printers ? state.printers.length : 0);
    const totalFilaments = stats ? stats.total_filaments : (state.filaments ? state.filaments.length : 0);
    const activeQuotes = stats ? stats.active_quotes : (state.projects 
        ? state.projects.filter(p => ['draft', 'quoted', 'approved', 'in_production'].includes(p.status)).length 
        : 0);

    if (statProjects) statProjects.textContent = totalProjects;
    if (statPrinters) statPrinters.textContent = totalPrinters;
    if (statFilaments) statFilaments.textContent = totalFilaments;
    if (statActive) statActive.textContent = activeQuotes;

    // 2. Update Financial KPI Highlights
    const revApprovedEl = document.getElementById('stat-revenue-approved');
    const revPipelineEl = document.getElementById('stat-revenue-pipeline');
    const netProfitEl = document.getElementById('stat-net-profit');
    const marginLabelEl = document.getElementById('stat-profit-margin-label');
    const printHoursEl = document.getElementById('stat-total-print-hours');
    const filamentLabelEl = document.getElementById('stat-filament-kg-label');

    if (revApprovedEl) revApprovedEl.textContent = formatCurrency(stats ? stats.total_revenue_approved : 0);
    if (revPipelineEl) revPipelineEl.textContent = formatCurrency(stats ? stats.pipeline_revenue : 0);
    if (netProfitEl) netProfitEl.textContent = formatCurrency(stats ? stats.total_net_profit : 0);
    if (marginLabelEl) {
        const margin = stats ? stats.avg_profit_margin_percent : 0;
        marginLabelEl.innerHTML = `<i data-lucide="percent" class="w-3 h-3 text-teal-400"></i> Margem média: ${margin.toFixed(1)}%`;
    }
    if (printHoursEl) {
        const hrs = stats ? stats.total_print_hours : 0;
        printHoursEl.textContent = `${hrs.toFixed(1)} h`;
    }
    if (filamentLabelEl) {
        const kg = stats ? stats.total_filament_kg : 0;
        filamentLabelEl.innerHTML = `<i data-lucide="cylinder" class="w-3 h-3 text-amber-400"></i> Filamento: ${kg.toFixed(2)} kg`;
    }

    // 3. Toggle Empty Account Onboarding Banner
    const emptyBanner = document.getElementById('dashboard-empty-banner');
    if (emptyBanner) {
        const isEmptyAccount = totalProjects === 0 && totalPrinters === 0 && totalFilaments === 0;
        if (isEmptyAccount) {
            emptyBanner.classList.remove('hidden');
        } else {
            emptyBanner.classList.add('hidden');
        }
    }

    // 4. Render Visual Analytics Charts
    renderDashboardCharts(stats);

    // 5. Render Recent Projects Table
    renderRecentProjects();

    refreshIcons();
}

function renderDashboardCharts(stats) {
    if (!window.Chart) {
        console.warn("Chart.js ainda não carregado.");
        return;
    }

    // Set standard Chart.js Dark Mode Themes
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
    Chart.defaults.font.size = 11;
    if (Chart.defaults.plugins?.tooltip) {
        Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
        Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
        Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
        Chart.defaults.plugins.tooltip.borderColor = '#334155';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
    }

    destroyDashboardCharts();

    const hasProjects = stats && stats.total_projects > 0;

    // --- Chart 1: Pipeline de Orçamentos (Status) ---
    const funnelCanvas = document.getElementById('chart-status-funnel');
    const funnelEmpty = document.getElementById('chart-status-funnel-empty');
    const funnelBadge = document.getElementById('chart-status-total-badge');

    if (funnelBadge) {
        funnelBadge.textContent = `${stats ? stats.total_projects : 0} orçamentos`;
    }

    if (funnelCanvas && funnelEmpty) {
        if (!hasProjects) {
            funnelCanvas.classList.add('hidden');
            funnelEmpty.classList.remove('hidden');
        } else {
            funnelCanvas.classList.remove('hidden');
            funnelEmpty.classList.add('hidden');

            const statusKeys = ['draft', 'quoted', 'approved', 'in_production', 'completed', 'cancelled'];
            const statusLabels = ['Rascunho', 'Orçado', 'Aprovado', 'Em Produção', 'Concluído', 'Cancelado'];
            const statusColors = ['#64748b', '#3b82f6', '#10b981', '#8b5cf6', '#06b6d4', '#ef4444'];
            const counts = statusKeys.map(k => (stats.status_counts && stats.status_counts[k]) || 0);

            state.charts.statusFunnel = new Chart(funnelCanvas, {
                type: 'doughnut',
                data: {
                    labels: statusLabels,
                    datasets: [{
                        data: counts,
                        backgroundColor: statusColors,
                        borderColor: '#151d2e',
                        borderWidth: 3,
                        hoverOffset: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '68%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: 8,
                                padding: 12,
                                font: { size: 11, weight: '500' }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const key = statusKeys[ctx.dataIndex];
                                    const val = stats.status_values ? (stats.status_values[key] || 0) : 0;
                                    return ` ${ctx.label}: ${ctx.raw} un (${formatCurrency(val)})`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // --- Chart 2: Faturamento & Lucratividade Temporal ---
    const timelineCanvas = document.getElementById('chart-financial-timeline');
    const timelineEmpty = document.getElementById('chart-financial-timeline-empty');

    if (timelineCanvas && timelineEmpty) {
        const timeline = stats ? stats.monthly_timeline : [];
        const hasTimelineData = timeline.length > 0 && timeline.some(t => t.revenue > 0 || t.base_cost > 0);

        if (!hasTimelineData) {
            timelineCanvas.classList.add('hidden');
            timelineEmpty.classList.remove('hidden');
        } else {
            timelineCanvas.classList.remove('hidden');
            timelineEmpty.classList.add('hidden');

            state.charts.financialTimeline = new Chart(timelineCanvas, {
                type: 'bar',
                data: {
                    labels: timeline.map(t => t.month_label),
                    datasets: [
                        {
                            label: 'Faturamento',
                            data: timeline.map(t => t.revenue),
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            hoverBackgroundColor: '#3b82f6',
                            borderRadius: 6,
                            order: 2,
                        },
                        {
                            label: 'Custo Base',
                            data: timeline.map(t => t.base_cost),
                            backgroundColor: 'rgba(245, 158, 11, 0.75)',
                            hoverBackgroundColor: '#f59e0b',
                            borderRadius: 6,
                            order: 3,
                        },
                        {
                            label: 'Lucro Líquido',
                            type: 'line',
                            data: timeline.map(t => t.net_profit),
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.12)',
                            fill: true,
                            tension: 0.35,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#10b981',
                            order: 1,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8', font: { size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(51, 65, 85, 0.35)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { family: "'JetBrains Mono', monospace", size: 10 },
                                callback: (v) => formatCurrency(v)
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: 8,
                                padding: 12,
                                font: { size: 11, weight: '500' }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`
                            }
                        }
                    }
                }
            });
        }
    }

    // --- Chart 3: Estrutura de Custos & Lucro da Oficina ---
    const costCanvas = document.getElementById('chart-cost-breakdown');
    const costEmpty = document.getElementById('chart-cost-breakdown-empty');

    if (costCanvas && costEmpty) {
        const cb = stats ? stats.cost_breakdown : null;
        const cbValues = cb ? [
            cb.material_cost || 0,
            cb.machine_energy_cost || 0,
            cb.labor_cost || 0,
            cb.bom_cost || 0,
            cb.overhead_cost || 0,
            cb.net_profit || 0
        ] : [0, 0, 0, 0, 0, 0];

        const hasCostData = cbValues.some(v => v > 0);

        if (!hasCostData) {
            costCanvas.classList.add('hidden');
            costEmpty.classList.remove('hidden');
        } else {
            costCanvas.classList.remove('hidden');
            costEmpty.classList.add('hidden');

            const cbLabels = ['Filamento', 'Máquina & Energia', 'Mão de Obra', 'Insumos BOM', 'Custos Indiretos (Overhead)', 'Lucro Líquido'];
            const cbColors = ['#8b5cf6', '#3b82f6', '#f59e0b', '#64748b', '#ec4899', '#10b981'];

            state.charts.costBreakdown = new Chart(costCanvas, {
                type: 'doughnut',
                data: {
                    labels: cbLabels,
                    datasets: [{
                        data: cbValues,
                        backgroundColor: cbColors,
                        borderColor: '#151d2e',
                        borderWidth: 3,
                        hoverOffset: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: 8,
                                padding: 12,
                                font: { size: 11, weight: '500' }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => ` ${ctx.label}: ${formatCurrency(ctx.raw)}`
                            }
                        }
                    }
                }
            });
        }
    }

    // --- Chart 4: Top Projetos por Faturamento & Horas ---
    const topCanvas = document.getElementById('chart-top-projects');
    const topEmpty = document.getElementById('chart-top-projects-empty');

    if (topCanvas && topEmpty) {
        const topProjects = (stats && stats.top_projects) || [];

        if (topProjects.length === 0) {
            topCanvas.classList.add('hidden');
            topEmpty.classList.remove('hidden');
        } else {
            topCanvas.classList.remove('hidden');
            topEmpty.classList.add('hidden');

            const projLabels = topProjects.map(p => {
                const name = p.name || 'Sem título';
                return name.length > 18 ? name.substring(0, 16) + '...' : name;
            });

            state.charts.topProjects = new Chart(topCanvas, {
                type: 'bar',
                data: {
                    labels: projLabels,
                    datasets: [
                        {
                            label: 'Faturamento',
                            data: topProjects.map(p => p.final_price),
                            backgroundColor: 'rgba(59, 130, 246, 0.85)',
                            hoverBackgroundColor: '#3b82f6',
                            borderRadius: 4,
                        },
                        {
                            label: 'Lucro Líquido',
                            data: topProjects.map(p => p.net_profit),
                            backgroundColor: 'rgba(16, 185, 129, 0.85)',
                            hoverBackgroundColor: '#10b981',
                            borderRadius: 4,
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: { color: 'rgba(51, 65, 85, 0.35)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { family: "'JetBrains Mono', monospace", size: 10 },
                                callback: (v) => formatCurrency(v)
                            }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#e2e8f0', font: { size: 11, weight: '500' } }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: 8,
                                padding: 12,
                                font: { size: 11, weight: '500' }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`,
                                afterLabel: (ctx) => {
                                    const p = topProjects[ctx.dataIndex];
                                    return p ? `Horas de impressão: ${p.print_hours.toFixed(1)} h` : '';
                                }
                            }
                        }
                    }
                }
            });
        }
    }
}

function renderRecentProjects() {
    const recentContainer = document.getElementById('dashboard-recent-projects');
    if (!recentContainer) return;

    const projects = state.projects || [];
    if (projects.length === 0) {
        recentContainer.innerHTML = `
            <div class="text-center py-10 px-4">
                <div class="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center mx-auto mb-3 shadow-inner">
                    <i data-lucide="inbox" class="w-6 h-6"></i>
                </div>
                <h4 class="text-sm font-semibold text-white">Nenhum orçamento cadastrado ainda</h4>
                <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    Crie seu primeiro projeto para visualizar métricas em tempo real e gerar propostas comerciais em PDF.
                </p>
                <button onclick="openNewProject()" class="btn-primary mt-4 py-2 px-4 text-xs font-semibold rounded-lg shadow-md shadow-blue-600/20 inline-flex items-center gap-1.5 transition-all">
                    <i data-lucide="plus" class="w-3.5 h-3.5"></i> Criar seu primeiro orçamento
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    const recent = projects.slice(0, 5);
    recentContainer.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                    <th class="py-3 px-3">Projeto</th>
                    <th class="py-3 px-3">Cliente</th>
                    <th class="py-3 px-3 text-center">Placas</th>
                    <th class="py-3 px-3">Tempo Est.</th>
                    <th class="py-3 px-3">Valor Final</th>
                    <th class="py-3 px-3 text-center">Status</th>
                    <th class="py-3 px-3 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
                ${recent.map(p => `
                    <tr class="hover:bg-slate-800/40 transition-colors group">
                        <td class="py-3 px-3">
                            <div class="flex items-center gap-2">
                                <div class="w-7 h-7 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20 flex items-center justify-center shrink-0">
                                    <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                                </div>
                                <span class="font-semibold text-white group-hover:text-blue-400 transition-colors">${escapeHtml(p.name)}</span>
                            </div>
                        </td>
                        <td class="py-3 px-3 text-slate-300">
                            ${p.client_name ? `<span class="flex items-center gap-1.5"><i data-lucide="user" class="w-3 h-3 text-slate-500"></i>${escapeHtml(p.client_name)}</span>` : '<span class="text-slate-500">—</span>'}
                        </td>
                        <td class="py-3 px-3 text-center">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                ${p.plates_count} un
                            </span>
                        </td>
                        <td class="py-3 px-3 font-mono text-slate-300">${formatDisplayHours(p.total_time_hours)}</td>
                        <td class="py-3 px-3 font-mono font-bold text-blue-400">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3 px-3 text-center">
                            <span class="badge-${escapeHtml(p.status || 'draft')}">
                                ${escapeHtml(formatStatus(p.status))}
                            </span>
                        </td>
                        <td class="py-3 px-3 text-right">
                            <div class="flex items-center justify-end gap-1">
                                <button onclick="editProject(${p.id})" class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors" title="Editar Orçamento">
                                    <i data-lucide="edit-3" class="w-4 h-4"></i>
                                </button>
                                <button onclick="duplicateProject(${p.id})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-slate-800 rounded-md transition-colors" title="Duplicar">
                                    <i data-lucide="copy" class="w-4 h-4"></i>
                                </button>
                                <button onclick="API.pdf.preview(${p.id}, 'client')" class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-md transition-colors" title="Visualizar Orçamento PDF">
                                    <i data-lucide="eye" class="w-4 h-4"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    refreshIcons();
}

function formatStatus(status) {
    const map = {
        'draft': 'Rascunho',
        'quoted': 'Orçado',
        'approved': 'Aprovado',
        'in_production': 'Em Produção',
        'completed': 'Concluído',
        'cancelled': 'Cancelado',
    };
    return map[status] || status;
}

// ================= PROJECTS VIEW =================

function renderProjectsTable(filterText = null, statusFilter = '') {
    const container = document.getElementById('projects-table-container');
    if (!container) return;

    let items = state.projects || [];

    // Search query filter (matches project name or client name with accent insensitivity)
    const term = (filterText !== null && filterText !== undefined ? filterText : (document.getElementById('project-search-input')?.value || '')).trim();
    if (term) {
        items = items.filter(p => 
            matchesSearch(`${p.name || ''} ${p.client_name || ''}`, term)
        );
    }

    // Status filter
    const activeStatus = statusFilter || state.projectStatusFilter || 'all';
    if (activeStatus !== 'all') {
        items = items.filter(p => p.status === activeStatus);
    }

    // Empty state
    if (items.length === 0) {
        const hasFilters = term !== '' || activeStatus !== 'all';
        container.innerHTML = `
            <div class="text-center py-12 px-4 text-slate-400">
                <div class="w-14 h-14 rounded-2xl bg-slate-800/80 text-slate-500 border border-slate-700/60 flex items-center justify-center mx-auto mb-3 shadow-inner">
                    <i data-lucide="${hasFilters ? 'search-x' : 'folder-plus'}" class="w-7 h-7"></i>
                </div>
                <h4 class="text-sm font-semibold text-white">
                    ${hasFilters ? 'Nenhum projeto encontrado' : 'Nenhum projeto cadastrado'}
                </h4>
                <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    ${hasFilters 
                        ? (term ? `Nenhum projeto encontrado para "<strong class="text-white">${escapeHtml(term)}</strong>". Tente buscar por outros termos ou limpar os filtros.` : 'Não encontramos resultados para os filtros selecionados. Tente buscar por outros termos ou limpar os filtros.')
                        : 'Comece criando seu primeiro orçamento profissional com cálculo automático de custos e margem.'}
                </p>
                <div class="mt-4 flex items-center justify-center gap-2">
                    ${hasFilters ? `
                        <button onclick="clearProjectFilters()" class="btn-secondary py-2 px-3.5 text-xs font-semibold rounded-lg transition-all">
                            Limpar Filtros
                        </button>
                    ` : ''}
                    <button onclick="openNewProject()" class="btn-primary py-2 px-3.5 text-xs font-semibold rounded-lg shadow-md shadow-blue-600/20 inline-flex items-center gap-1.5 transition-all">
                        <i data-lucide="plus" class="w-3.5 h-3.5"></i> Criar Novo Orçamento
                    </button>
                </div>
            </div>
        `;
        refreshIcons();
        return;
    }

    // Sort items
    const sortField = state.projectSortField || 'id';
    const sortAsc = state.projectSortAsc ?? false;

    items = [...items].sort((a, b) => {
        let valA, valB;
        switch (sortField) {
            case 'name':
                valA = (a.name || '').toLowerCase();
                valB = (b.name || '').toLowerCase();
                break;
            case 'client_name':
                valA = (a.client_name || '').toLowerCase();
                valB = (b.client_name || '').toLowerCase();
                break;
            case 'plates_count':
                valA = a.plates_count || 0;
                valB = b.plates_count || 0;
                break;
            case 'total_time_hours':
                valA = a.total_time_hours || 0;
                valB = b.total_time_hours || 0;
                break;
            case 'base_cost':
                valA = a.base_cost || 0;
                valB = b.base_cost || 0;
                break;
            case 'final_price_to_client':
                valA = a.final_price_to_client || 0;
                valB = b.final_price_to_client || 0;
                break;
            case 'status':
                valA = (a.status || '').toLowerCase();
                valB = (b.status || '').toLowerCase();
                break;
            case 'id':
            default:
                valA = a.id || 0;
                valB = b.id || 0;
                break;
        }

        if (typeof valA === 'string') {
            const cmp = valA.localeCompare(valB, 'pt-BR');
            return sortAsc ? cmp : -cmp;
        } else {
            return sortAsc ? (valA - valB) : (valB - valA);
        }
    });

    function getSortIcon(field) {
        if (state.projectSortField !== field) {
            return '<i data-lucide="arrow-up-down" class="w-3 h-3 text-slate-500 opacity-60 group-hover:opacity-100 transition-opacity"></i>';
        }
        return state.projectSortAsc
            ? '<i data-lucide="arrow-up" class="w-3 h-3 text-blue-400"></i>'
            : '<i data-lucide="arrow-down" class="w-3 h-3 text-blue-400"></i>';
    }

    // Render modern SaaS Dark Mode Table
    container.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-800 bg-slate-900/70 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                    <th class="py-3 px-4 cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('name')" title="Ordenar por Nome">
                        <div class="flex items-center gap-1.5">
                            <span>Projeto & Referência</span>
                            ${getSortIcon('name')}
                        </div>
                    </th>
                    <th class="py-3 px-4 cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('client_name')" title="Ordenar por Cliente">
                        <div class="flex items-center gap-1.5">
                            <span>Cliente</span>
                            ${getSortIcon('client_name')}
                        </div>
                    </th>
                    <th class="py-3 px-4 text-center cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('plates_count')" title="Ordenar por Placas">
                        <div class="flex items-center justify-center gap-1.5">
                            <span>Placas</span>
                            ${getSortIcon('plates_count')}
                        </div>
                    </th>
                    <th class="py-3 px-4 cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('total_time_hours')" title="Ordenar por Tempo Total">
                        <div class="flex items-center gap-1.5">
                            <span>Tempo Total</span>
                            ${getSortIcon('total_time_hours')}
                        </div>
                    </th>
                    <th class="py-3 px-4 cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('base_cost')" title="Ordenar por Custo Base">
                        <div class="flex items-center gap-1.5">
                            <span>Custo Base</span>
                            ${getSortIcon('base_cost')}
                        </div>
                    </th>
                    <th class="py-3 px-4 cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('final_price_to_client')" title="Ordenar por Preço de Venda">
                        <div class="flex items-center gap-1.5">
                            <span>Preço de Venda</span>
                            ${getSortIcon('final_price_to_client')}
                        </div>
                    </th>
                    <th class="py-3 px-4 text-center cursor-pointer select-none hover:text-white transition-colors group" onclick="setProjectSort('status')" title="Ordenar por Status">
                        <div class="flex items-center justify-center gap-1.5">
                            <span>Status</span>
                            ${getSortIcon('status')}
                        </div>
                    </th>
                    <th class="py-3 px-4 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
                ${items.map(p => `
                    <tr class="hover:bg-slate-800/40 transition-colors group">
                        <td class="py-3.5 px-4 font-semibold text-white">
                            <div class="flex items-center gap-2.5">
                                <div class="w-8 h-8 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                                    <i data-lucide="box" class="w-4 h-4"></i>
                                </div>
                                <div class="min-w-0">
                                    <p class="font-bold text-white group-hover:text-blue-400 transition-colors truncate">${escapeHtml(p.name)}</p>
                                    <p class="text-[10px] text-slate-500 font-mono">#${p.id.toString().padStart(4, '0')}</p>
                                </div>
                            </div>
                        </td>
                        <td class="py-3.5 px-4 text-slate-300">
                            ${p.client_name ? `
                                <div class="flex items-center gap-1.5">
                                    <i data-lucide="user" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
                                    <span class="truncate">${escapeHtml(p.client_name)}</span>
                                </div>
                            ` : '<span class="text-slate-500">—</span>'}
                        </td>
                        <td class="py-3.5 px-4 text-center">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                ${p.plates_count} un
                            </span>
                        </td>
                        <td class="py-3.5 px-4 font-mono text-slate-300">${formatDisplayHours(p.total_time_hours)}</td>
                        <td class="py-3.5 px-4 font-mono text-slate-400">${formatCurrency(p.base_cost)}</td>
                        <td class="py-3.5 px-4 font-mono font-bold text-blue-400 text-sm">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3.5 px-4 text-center">
                            <span class="badge-${escapeHtml(p.status || 'draft')}">
                                ${escapeHtml(formatStatus(p.status))}
                            </span>
                        </td>
                        <td class="py-3.5 px-4 text-right">
                            <div class="flex items-center justify-end gap-1">
                                <button onclick="editProject(${p.id})" class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors" title="Editar">
                                    <i data-lucide="edit-3" class="w-4 h-4"></i>
                                </button>
                                <button onclick="duplicateProject(${p.id})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-slate-800 rounded-md transition-colors" title="Duplicar">
                                    <i data-lucide="copy" class="w-4 h-4"></i>
                                </button>
                                <button onclick="API.pdf.preview(${p.id}, 'client')" class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-md transition-colors" title="Visualizar Orçamento PDF">
                                    <i data-lucide="eye" class="w-4 h-4"></i>
                                </button>
                                <button onclick="API.pdf.preview(${p.id}, 'technical')" class="p-1.5 text-slate-400 hover:text-purple-400 hover:bg-slate-800 rounded-md transition-colors" title="Ficha Técnica de Produção">
                                    <i data-lucide="clipboard-list" class="w-4 h-4"></i>
                                </button>
                                <button onclick="deleteProject(${p.id})" class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors" title="Excluir">
                                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div class="px-4 py-3 bg-slate-900/50 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span>Exibindo <b>${items.length}</b> de <b>${state.projects.length}</b> projetos</span>
            <span class="text-slate-500 font-mono">3D Print Calc Pro</span>
        </div>
    `;
    refreshIcons();
}

function setProjectSort(field) {
    if (state.projectSortField === field) {
        state.projectSortAsc = !state.projectSortAsc;
    } else {
        state.projectSortField = field;
        state.projectSortAsc = (field === 'name' || field === 'client_name' || field === 'status');
    }
    const input = document.getElementById('project-search-input');
    renderProjectsTable(input ? input.value : '', state.projectStatusFilter || 'all');
}

function filterProjects() {
    const input = document.getElementById('project-search-input');
    renderProjectsTable(input ? input.value : '', state.projectStatusFilter || 'all');
}

function setProjectStatusFilter(status) {
    state.projectStatusFilter = status;

    // Update active style on filter chips
    document.querySelectorAll('.project-filter-chip').forEach(chip => {
        const chipStatus = chip.getAttribute('data-status');
        if (chipStatus === status) {
            chip.className = 'project-filter-chip px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all bg-blue-600/20 text-blue-400 border border-blue-500/40 shadow-sm';
        } else {
            chip.className = 'project-filter-chip px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all bg-slate-800/60 text-slate-400 border border-slate-700/50 hover:text-white';
        }
    });

    filterProjects();
}

function clearProjectFilters() {
    const input = document.getElementById('project-search-input');
    if (input) input.value = '';
    setProjectStatusFilter('all');
}

// ================= PROJECT CALCULATOR & EDITOR =================

function openNewProject() {
    state.currentProject = null;
    state.currentPlates = [createDefaultPlate(1)];
    state.currentBOM = [];

    // Prepopulate user defaults
    const u = state.user || {};
    document.getElementById('editor-project-title').textContent = 'Novo Orçamento';
    document.getElementById('editor-project-subtitle').textContent = 'Defina placas, arquivos 3MF/G-code e parâmetros comerciais';
    document.getElementById('proj-name').value = '';
    document.getElementById('proj-client-name').value = '';
    document.getElementById('proj-client-email').value = '';
    document.getElementById('proj-client-phone').value = '';
    document.getElementById('proj-status').value = 'draft';
    document.getElementById('proj-cad-hours').value = '0';
    document.getElementById('proj-cad-rate').value = u.default_cad_rate ?? 50;
    document.getElementById('proj-post-hours').value = '0';
    document.getElementById('proj-post-rate').value = u.default_post_rate ?? 30;
    document.getElementById('proj-overhead').value = '0';
    document.getElementById('proj-margin').value = u.default_profit_margin ?? 30;
    document.getElementById('proj-tax').value = u.default_tax_rate ?? 6;
    document.getElementById('proj-discount').value = '0';
    document.getElementById('proj-shipping').value = '0';
    document.getElementById('proj-delivery-days').value = '3';
    document.getElementById('proj-payment-terms').value = u.default_payment_terms || '';
    document.getElementById('proj-warranty-terms').value = u.default_warranty_terms || '';
    const defPay = (u.default_payment_terms || '').trim();
    const defWar = (u.default_warranty_terms || '').trim();
    document.getElementById('proj-payment-terms').placeholder = defPay 
        ? `Padrão da oficina: ${defPay}` 
        : 'Deixe em branco para usar o padrão da oficina';
    document.getElementById('proj-warranty-terms').placeholder = defWar 
        ? `Padrão da oficina: ${defWar}` 
        : 'Deixe em branco para usar o padrão da oficina';
    document.getElementById('proj-notes').value = '';

    renderPlates();
    renderBOM();
    recalcLiveSummary();
    navigateTo('project-editor');
}

async function editProject(id) {
    try {
        const proj = await API.projects.get(id);
        const u = state.user || {};
        state.currentProject = proj;
        state.currentPlates = (proj.plates && proj.plates.length > 0) ? proj.plates : [createDefaultPlate(1)];
        state.currentBOM = proj.bom_items || [];

        document.getElementById('editor-project-title').textContent = `Editar: ${proj.name}`;
        document.getElementById('editor-project-subtitle').textContent = `Orçamento #${proj.id.toString().padStart(4, '0')} • Cliente: ${proj.client_name || 'Não informado'}`;
        document.getElementById('proj-name').value = proj.name;
        document.getElementById('proj-client-name').value = proj.client_name || '';
        document.getElementById('proj-client-email').value = proj.client_email || '';
        document.getElementById('proj-client-phone').value = formatPhoneInput(proj.client_phone || '');
        document.getElementById('proj-status').value = proj.status || 'draft';
        document.getElementById('proj-cad-hours').value = proj.cad_hours ?? 0;
        document.getElementById('proj-cad-rate').value = proj.cad_hourly_rate ?? 50;
        document.getElementById('proj-post-hours').value = proj.post_process_hours ?? 0;
        document.getElementById('proj-post-rate').value = proj.post_process_hourly_rate ?? 30;
        document.getElementById('proj-overhead').value = proj.overhead_cost ?? 0;
        document.getElementById('proj-margin').value = proj.profit_margin_percent ?? 30;
        document.getElementById('proj-tax').value = proj.tax_rate_percent ?? 6;
        document.getElementById('proj-discount').value = proj.discount_percent ?? 0;
        document.getElementById('proj-shipping').value = proj.shipping_cost ?? 0;
        document.getElementById('proj-delivery-days').value = proj.delivery_days != null ? proj.delivery_days : '';
        const defPay = (u.default_payment_terms || '').trim();
        const defWar = (u.default_warranty_terms || '').trim();
        document.getElementById('proj-payment-terms').placeholder = defPay 
            ? `Padrão da oficina: ${defPay}` 
            : 'Deixe em branco para usar o padrão da oficina';
        document.getElementById('proj-warranty-terms').placeholder = defWar 
            ? `Padrão da oficina: ${defWar}` 
            : 'Deixe em branco para usar o padrão da oficina';
        document.getElementById('proj-payment-terms').value = proj.payment_terms || '';
        document.getElementById('proj-warranty-terms').value = proj.warranty_terms || '';
        document.getElementById('proj-notes').value = proj.notes || '';

        renderPlates();
        renderBOM();
        recalcLiveSummary();
        navigateTo('project-editor');
    } catch (err) {
        showToast(err.message, 'error');
        navigateTo('projects');
    }
}

function createDefaultPlate(idx = 1) {
    const defaultPrinter = state.printers[0];
    const defaultFilament = state.filaments[0];

    return {
        name: `Placa ${idx}`,
        printer_id: defaultPrinter ? defaultPrinter.id : null,
        filament_id: defaultFilament ? defaultFilament.id : null,
        custom_printer_hourly_rate: defaultPrinter ? null : 2.50,
        custom_filament_cost_per_g: defaultFilament ? null : 0.10,
        nozzle_diameter: '0.4',
        bed_type: 'Textured PEI',
        layer_height: '0.20',
        print_time_hours: 0,
        part_weight_g: 0,
        purge_weight_g: 0,
        slicer_filament_profile: null,
        failure_margin_percent: (state.user?.default_failure_rate ?? 10),
        quantity: 1,
        notes: '',
    };
}

function addNewPlateRow() {
    const idx = state.currentPlates.length + 1;
    state.currentPlates.push(createDefaultPlate(idx));
    renderPlates();
    recalcLiveSummary();
    const container = document.getElementById('plates-container');
    if (container && container.lastElementChild) {
        container.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function removePlateRow(index) {
    if (state.currentPlates.length <= 1) {
        showToast('O projeto precisa ter pelo menos uma placa.', 'info');
        return;
    }
    state.currentPlates.splice(index, 1);
    renderPlates();
    recalcLiveSummary();
}

// Issue #21: Duplicate a plate row - clones the object and inserts right after the original
function duplicatePlateRow(idx) {
    const orig = state.currentPlates[idx];
    if (!orig) return;
    const cloned = JSON.parse(JSON.stringify(orig));
    delete cloned.id;
    cloned.name = `${orig.name || 'Placa'} (Cópia)`;
    state.currentPlates.splice(idx + 1, 0, cloned);
    renderPlates();
    recalcLiveSummary();
    // Scroll to the new cloned plate
    const container = document.getElementById('plates-container');
    if (container) {
        const plateEls = container.querySelectorAll(':scope > div');
        if (plateEls[idx + 1]) {
            plateEls[idx + 1].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    showToast('Placa duplicada com sucesso!', 'success');
}
window.duplicatePlateRow = duplicatePlateRow;

// Global alias for compatibility
window.removePlate = removePlateRow;

function updatePlateTime(idx) {
    const hElem = document.getElementById(`plate-time-h-${idx}`);
    const mElem = document.getElementById(`plate-time-m-${idx}`);
    if (!hElem && !mElem) {
        return; // Preserva o print_time_hours já existente se os inputs não existirem no DOM
    }
    const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
    const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
    const currentHours = state.currentPlates[idx]?.print_time_hours || 0;

    // Se inputs estão zerados mas a placa possui tempo submétrico positivo pré-existente (ex: fatiado < 30s), preservar
    if (h === 0 && m === 0 && currentHours > 0 && currentHours < (1 / 60)) {
        recalcLiveSummary();
        return;
    }

    state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
    recalcLiveSummary();
}

function renderPlates() {
    const esc = (typeof escapeHtml === 'function') ? escapeHtml : (str => (str == null ? '' : String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;')));
    const container = document.getElementById('plates-container');
    if (!container) return;

    if (!state.currentPlates || state.currentPlates.length === 0) {
        container.innerHTML = `
            <div class="p-8 rounded-xl bg-slate-900/40 border border-dashed border-slate-800/80 text-center flex flex-col items-center justify-center space-y-3">
                <div class="w-12 h-12 rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/20 flex items-center justify-center shadow-inner">
                    <i data-lucide="layers" class="w-6 h-6"></i>
                </div>
                <p class="text-sm font-semibold text-white">Nenhuma placa de impressão configurada</p>
                <p class="text-xs text-slate-400 max-w-sm">Adicione arquivos 3MF/G-code ou configure placas manualmente para calcular o tempo de máquina e filamento.</p>
                <button type="button" onclick="addNewPlateRow()" class="py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-blue-600/20">
                    <i data-lucide="plus" class="w-4 h-4"></i> Adicionar Placa
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    container.innerHTML = state.currentPlates.map((plate, idx) => {
        const hasValidPrinter = !!(plate.printer_id && state.printers.some(p => p.id === plate.printer_id));
        const hasValidFilament = !!(plate.filament_id && state.filaments.some(f => f.id === plate.filament_id));
        const selFil = hasValidFilament ? state.filaments.find(f => f.id === plate.filament_id) : null;
        const totalMin = Math.round((plate.print_time_hours || 0) * 60);
        const timeH = Math.floor(totalMin / 60);
        const timeM = totalMin % 60;
        const isSubMinute = (plate.print_time_hours || 0) > 0 && totalMin === 0;
        const nozzle = plate.nozzle_diameter || '0.4';
        const bed = plate.bed_type || 'Textured PEI';
        const layer = plate.layer_height || '0.20';

        return `
        <div class="card-dark p-5 rounded-xl space-y-4 relative group transition-all">
            <!-- Plate Header: Index, Title, Slicer Import & Delete Action -->
            <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div class="flex items-center gap-2.5">
                    <span class="w-7 h-7 rounded-lg bg-blue-600/20 text-blue-400 font-bold text-xs flex items-center justify-center border border-blue-500/30 font-mono shadow-sm">
                        #${idx + 1}
                    </span>
                    <input type="text" value="${(plate.name || `Placa ${idx + 1}`).replace(/"/g, '&quot;')}" oninput="state.currentPlates[${idx}].name = this.value" class="px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-blue-500 w-48 sm:w-56 transition-colors placeholder:text-slate-500" placeholder="Nome da Placa">
                </div>

                <div class="flex items-center gap-2">
                    <label class="cursor-pointer px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-[11px] font-medium border border-slate-700 flex items-center gap-1.5 transition-all shadow-sm" title="Carregar 3MF, Gcode ou .gcode.3mf especificamente nesta placa">
                        <i data-lucide="file-up" class="w-3.5 h-3.5 text-blue-400"></i> Importar 3MF/Gcode
                        <input type="file" accept=".3mf,.gcode,.gcode.3mf" class="hidden" onchange="handleSinglePlateFile(event, ${idx})">
                    </label>
                    <button type="button" onclick="duplicatePlateRow(${idx})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors" title="Duplicar Placa">
                        <i data-lucide="copy" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="removePlateRow(${idx})" class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors" title="Remover Placa">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- Group A: Hardware & Setup Parameters -->
            <div class="bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/60 space-y-3">
                <div class="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <i data-lucide="cpu" class="w-3.5 h-3.5 text-blue-400"></i> Configuração de Hardware & Setup
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 items-start">
                    <!-- Printer Selector -->
                    <div class="plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1"><label class="text-[11px] font-medium text-slate-300 leading-tight">Impressora</label></div>
                        <select onchange="updatePlatePrinter(${idx}, this.value)" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500">
                            <option value="">Personalizada (Manual)</option>
                            ${state.printers.map(p => `
                                <option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
                                    ${esc(p.name)} (${formatCurrency(p.machine_hourly_rate)}/h)
                                </option>
                            `).join('')}
                        </select>
                        ${!hasValidPrinter ? `
                            <div class="mt-1.5 flex items-center gap-1.5 bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                                <span class="text-[10px] text-amber-400 font-medium">Taxa manual:</span>
                                <span class="text-[10px] text-slate-400">R$</span>
                                <input type="number" step="any" min="0" value="${plate.custom_printer_hourly_rate ?? 2.50}" oninput="state.currentPlates[${idx}].custom_printer_hourly_rate = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-20 px-1.5 py-0.5 bg-slate-900 border border-amber-500/40 rounded text-xs text-white font-medium focus:outline-none focus:border-amber-400 font-numeric" placeholder="2.50">
                                <span class="text-[10px] text-slate-400">/h</span>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Filament Selector with Dynamic Dot -->
                    <div class="plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1 w-full">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <label class="text-[11px] font-medium text-slate-300 leading-tight shrink-0">Filamento</label>
                                ${plate.slicer_filament_profile ? `
                                    <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors shrink-0 cursor-help" data-tooltip="Fatiado com: ${esc(cleanFilamentProfileName(plate.slicer_filament_profile))}">
                                        <i data-lucide="help-circle" class="w-3.5 h-3.5"></i>
                                    </span>
                                ` : ''}
                            </div>
                            ${selFil ? `<span class="flex items-center gap-1 text-[10px] text-slate-400 font-normal shrink-0 max-w-[55%] truncate" title="${esc(selFil.material)} ${esc(selFil.color || '')}"><span class="w-2 h-2 rounded-full inline-block border border-slate-600 shadow-sm shrink-0" style="background-color: ${esc(selFil.color_hex || '#10b981')};"></span> <span class="truncate">${esc(selFil.material)} ${esc(selFil.color || '')}</span></span>` : ''}
                        </div>
                        <div class="relative flex items-center">
                            <span class="absolute left-2.5 w-3 h-3 rounded-full border border-white/20 pointer-events-none shadow-sm" style="background-color: ${selFil ? esc(selFil.color_hex || '#10b981') : '#64748b'};"></span>
                            <select onchange="updatePlateFilament(${idx}, this.value)" class="w-full pl-8 pr-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500">
                                <option value="">Personalizado (Manual)</option>
                                ${state.filaments.map(f => `
                                    <option value="${f.id}" ${plate.filament_id === f.id ? 'selected' : ''}>
                                        ${esc(f.name)} (${formatCurrency(f.cost_per_gram || 0)}/g)
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        ${!hasValidFilament ? `
                            <div class="mt-1.5 flex items-center gap-1.5 bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                                <span class="text-[10px] text-amber-400 font-medium">Custo manual:</span>
                                <span class="text-[10px] text-slate-400">R$</span>
                                <input type="number" step="any" min="0" value="${plate.custom_filament_cost_per_g ?? 0.10}" oninput="state.currentPlates[${idx}].custom_filament_cost_per_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-20 px-1.5 py-0.5 bg-slate-900 border border-amber-500/40 rounded text-xs text-white font-medium focus:outline-none focus:border-amber-400 font-numeric" placeholder="0.10">
                                <span class="text-[10px] text-slate-400">/g</span>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2.5 border-t border-slate-800/60">
                    <div class="plate-field-col">
                        <label class="text-[10px] font-medium text-slate-400 mb-1 block">Bico (Diâmetro)</label>
                        <input type="text" value="${esc(nozzle)}" oninput="state.currentPlates[${idx}].nozzle_diameter = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500" placeholder="0.4">
                    </div>
                    <div class="plate-field-col">
                        <label class="text-[10px] font-medium text-slate-400 mb-1 block">Camada (Altura)</label>
                        <input type="text" value="${esc(layer)}" oninput="state.currentPlates[${idx}].layer_height = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500" placeholder="0.20">
                    </div>
                    <div class="plate-field-col">
                        <label class="text-[10px] font-medium text-slate-400 mb-1 block">Tipo de Mesa</label>
                        <input type="text" value="${esc(bed)}" oninput="state.currentPlates[${idx}].bed_type = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500" placeholder="Textured PEI">
                    </div>
                </div>
            </div>

            <!-- Group B: Slicer & Physical Parameters -->
            <div class="bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/60 space-y-3">
                <div class="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <i data-lucide="sliders" class="w-3.5 h-3.5 text-indigo-400"></i> Parâmetros do Fatiador & Físicos
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 plate-grid-aligned">
                    <!-- Print Time Dual Input (Hours & Minutes) -->
                    <div class="col-span-2 plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1">
                            <label class="text-[10px] font-medium text-slate-400 leading-tight">Tempo (h : min)</label>
                            ${isSubMinute ? `<span class="text-[9px] text-blue-400 font-medium" title="Tempo fatiado preservado: ~${Math.round((plate.print_time_hours || 0) * 3600)}s">&lt;1 min (~${Math.round((plate.print_time_hours || 0) * 3600)}s)</span>` : ''}
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="relative flex-1">
                                <input type="number" min="0" step="1" id="plate-time-h-${idx}" value="${timeH}" placeholder="0" oninput="updatePlateTime(${idx})" class="w-full pl-2 pr-4 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white text-center font-numeric focus:outline-none focus:border-blue-500" title="Horas">
                                <span class="absolute right-1.5 top-1.5 text-[10px] text-slate-400 pointer-events-none">h</span>
                            </div>
                            <span class="text-slate-500 font-bold">:</span>
                            <div class="relative flex-1">
                                <input type="number" min="0" max="59" step="1" id="plate-time-m-${idx}" value="${timeM}" placeholder="0" oninput="updatePlateTime(${idx})" class="w-full pl-2 pr-4 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white text-center font-numeric focus:outline-none focus:border-blue-500" title="Minutos">
                                <span class="absolute right-1.5 top-1.5 text-[10px] text-slate-400 pointer-events-none">m</span>
                            </div>
                        </div>
                    </div>

                    <!-- Total Filament Used Weight -->
                    <div class="col-span-1 plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1"><label class="text-[10px] font-medium text-slate-400 leading-tight">Filamento usado (g)</label></div>
                        <input type="number" step="any" min="0" value="${plate.part_weight_g}" oninput="state.currentPlates[${idx}].part_weight_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="0">
                    </div>

                    <!-- Purge Weight (g) -->
                    <div class="col-span-1 plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1"><label class="text-[10px] font-medium text-slate-400 leading-tight">Purga (g)</label></div>
                        <input type="number" step="any" min="0" value="${plate.purge_weight_g || 0}" oninput="state.currentPlates[${idx}].purge_weight_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="0">
                    </div>

                    <!-- Failure Margin -->
                    <div class="col-span-1 plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1"><label class="text-[10px] font-medium text-slate-400 leading-tight">Falha (%)</label></div>
                        <input type="number" step="any" min="0" value="${plate.failure_margin_percent}" oninput="state.currentPlates[${idx}].failure_margin_percent = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="10">
                    </div>

                    <!-- Quantity -->
                    <div class="col-span-1 plate-field-col">
                        <div class="plate-label-slot flex items-start justify-between gap-1 mb-1"><label class="text-[10px] font-medium text-slate-400 leading-tight">Qtd Cópias</label></div>
                        <input type="number" step="1" min="1" value="${plate.quantity}" oninput="state.currentPlates[${idx}].quantity = parseInt(this.value, 10) || 1; recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-bold font-numeric text-center focus:outline-none focus:border-blue-500" placeholder="1">
                    </div>
                </div>

                <!-- Plate Notes & Operational Instructions -->
                <div class="plate-field-col pt-2 border-t border-slate-800/60">
                    <label class="text-[10px] font-medium text-slate-400 mb-1 block">Observações / Instruções de Impressão</label>
                    <input type="text" value="${esc(plate.notes || '')}" oninput="state.currentPlates[${idx}].notes = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors" placeholder="Ex: Pausa na camada 45 para ímã, usar cola bastão, suportes orgânicos...">
                </div>
            </div>

            <!-- Single Plate Subtotal Summary Pill -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-2 px-1 border-t border-slate-800/80 text-xs">
                <div class="flex items-center gap-2 text-slate-400">
                    <span class="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                    <span id="plate-summary-text-${idx}" class="text-[11px] text-slate-400 font-mono">Calculando custo da placa...</span>
                </div>
                <div class="flex items-center gap-1.5 bg-blue-950/40 border border-blue-500/30 px-3 py-1 rounded-lg">
                    <span class="text-[10px] text-blue-400 uppercase font-semibold">Custo da Placa:</span>
                    <span class="font-bold text-white font-numeric text-xs" id="plate-cost-${idx}">R$ 0,00</span>
                </div>
            </div>
        </div>
        `;
    }).join('');

    refreshIcons();
}

function updatePlatePrinter(idx, val) {
    state.currentPlates[idx].printer_id = val ? parseInt(val, 10) : null;
    if (state.currentPlates[idx].printer_id) {
        state.currentPlates[idx].custom_printer_hourly_rate = null;
    } else {
        if (state.currentPlates[idx].custom_printer_hourly_rate == null) {
            state.currentPlates[idx].custom_printer_hourly_rate = 2.50;
        }
    }
    renderPlates();
    recalcLiveSummary();
}

function updatePlateFilament(idx, val) {
    state.currentPlates[idx].filament_id = val ? parseInt(val, 10) : null;
    if (state.currentPlates[idx].filament_id) {
        state.currentPlates[idx].custom_filament_cost_per_g = null;
    } else {
        if (state.currentPlates[idx].custom_filament_cost_per_g == null) {
            state.currentPlates[idx].custom_filament_cost_per_g = 0.10;
        }
    }
    renderPlates();
    recalcLiveSummary();
}

// ================= BOM (BILL OF MATERIALS) INSUMOS MANAGER =================

function createDefaultBOM() {
    return {
        name: 'Parafuso M3x12 Inox',
        category: 'Fixadores',
        quantity: 4,
        unit_cost: 0.50,
        notes: '',
    };
}

function addNewBomRow() {
    state.currentBOM.push(createDefaultBOM());
    renderBOM();
    recalcLiveSummary();
}

function removeBomRow(index) {
    state.currentBOM.splice(index, 1);
    renderBOM();
    recalcLiveSummary();
}

function duplicateBomRow(idx) {
    const orig = state.currentBOM[idx];
    if (!orig) return;
    const cloned = JSON.parse(JSON.stringify(orig));
    delete cloned.id;
    cloned.name = `${orig.name || 'Insumo'} (Cópia)`;
    state.currentBOM.splice(idx + 1, 0, cloned);
    renderBOM();
    recalcLiveSummary();
    showToast('Insumo duplicado com sucesso!', 'success');
}

// Casing aliases to ensure total runtime resilience
window.addNewBOMRow = addNewBomRow;
window.removeBOMRow = removeBomRow;
window.duplicateBomRow = duplicateBomRow;
window.duplicateBOMRow = duplicateBomRow;

function renderBOM() {
    const container = document.getElementById('bom-container');
    if (!container) return;

    if (!state.currentBOM || state.currentBOM.length === 0) {
        container.innerHTML = `
            <div class="p-6 rounded-xl bg-slate-900/40 border border-dashed border-slate-800/80 text-center flex flex-col items-center justify-center space-y-2">
                <div class="w-10 h-10 rounded-full bg-slate-800/60 border border-slate-700/60 flex items-center justify-center text-slate-400">
                    <i data-lucide="package-plus" class="w-5 h-5 text-blue-400/80"></i>
                </div>
                <p class="text-xs font-semibold text-slate-200">Nenhum componente ou insumo adicional cadastrado.</p>
                <p class="text-[11px] text-slate-400 max-w-sm">Adicione parafusos, insertos de latão, ímãs, rolamentos ou embalagens para cálculo automático no custo base.</p>
                <button type="button" onclick="addNewBomRow()" class="mt-2 py-1.5 px-3 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors">
                    <i data-lucide="plus" class="w-3.5 h-3.5"></i> Adicionar Primeiro Insumo
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    container.innerHTML = `
        <div class="space-y-2">
            <!-- Header Labels (Desktop Table Columns) -->
            <div class="hidden sm:grid sm:grid-cols-12 gap-3 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800/60">
                <div class="col-span-3">Descrição do Componente</div>
                <div class="col-span-2">Categoria</div>
                <div class="col-span-2">Especificações / Obs</div>
                <div class="col-span-1 text-center">Qtd</div>
                <div class="col-span-2 text-right">Custo Unit. (R$)</div>
                <div class="col-span-1 text-right">Subtotal</div>
                <div class="col-span-1 text-center">Ações</div>
            </div>
            <!-- Dynamic Insumo Rows -->
            ${state.currentBOM.map((item, idx) => `
                <div class="grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-3 p-3 bg-slate-900/70 hover:bg-slate-900/95 border border-slate-800/80 hover:border-slate-700 rounded-lg items-center text-xs transition-all shadow-sm">
                    <!-- Item Description -->
                    <div class="sm:col-span-3">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Item / Descrição</label>
                        <input type="text" value="${(item.name || '').replace(/"/g, '&quot;')}" oninput="state.currentBOM[${idx}].name = this.value" placeholder="Item (ex: Parafuso M3)" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors">
                    </div>

                    <!-- Category Select -->
                    <div class="sm:col-span-2">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Categoria</label>
                        <select onchange="state.currentBOM[${idx}].category = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs focus:outline-none focus:border-blue-500 transition-colors">
                            <option value="Fixadores" ${item.category === 'Fixadores' ? 'selected' : ''}>Fixadores</option>
                            <option value="Insertos" ${item.category === 'Insertos' ? 'selected' : ''}>Insertos</option>
                            <option value="Eletrônica" ${item.category === 'Eletrônica' ? 'selected' : ''}>Eletrônica</option>
                            <option value="Embalagem" ${item.category === 'Embalagem' ? 'selected' : ''}>Embalagem</option>
                            <option value="Outros" ${item.category === 'Outros' ? 'selected' : ''}>Outros</option>
                        </select>
                    </div>

                    <!-- Specifications / Notes -->
                    <div class="sm:col-span-2">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Especificações / Obs</label>
                        <input type="text" value="${(item.notes || '').replace(/"/g, '&quot;')}" oninput="state.currentBOM[${idx}].notes = this.value" placeholder="Obs / Especificação..." class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors">
                    </div>

                    <!-- Quantity Input (min=1 step=1) -->
                    <div class="sm:col-span-1">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Quantidade</label>
                        <input type="number" min="1" step="1" value="${item.quantity || 1}" oninput="state.currentBOM[${idx}].quantity = Math.max(1, parseInt(this.value, 10) || 1); recalcLiveSummary();" placeholder="Qtd" class="w-full px-1.5 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs text-center font-bold font-mono focus:outline-none focus:border-blue-500 transition-colors">
                    </div>

                    <!-- Unit Cost (CRITICAL CONTRACT: placeholder="R$ Unit" min="0" step="any") -->
                    <div class="sm:col-span-2">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Custo Unitário</label>
                        <div class="relative flex items-center">
                            <span class="absolute left-2 text-[11px] font-mono text-slate-500 pointer-events-none select-none">R$</span>
                            <input type="number" min="0" step="any" value="${item.unit_cost ?? 0}" oninput="state.currentBOM[${idx}].unit_cost = Math.max(0, parseLocaleFloat(this.value, 0)); recalcLiveSummary();" placeholder="R$ Unit" class="w-full pl-7 pr-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs text-right font-mono focus:outline-none focus:border-blue-500 transition-colors">
                        </div>
                    </div>

                    <!-- Subtotal (CRITICAL CONTRACT: id="bom-subtotal-${idx}") -->
                    <div class="sm:col-span-1 text-right font-mono font-bold text-white text-xs py-1" id="bom-subtotal-${idx}">
                        ${formatCurrency((item.quantity || 1) * (item.unit_cost || 0))}
                    </div>

                    <!-- Action Buttons (Duplicate & Delete) -->
                    <div class="sm:col-span-1 flex justify-center items-center gap-1 pt-1 sm:pt-0">
                        <button type="button" onclick="duplicateBomRow(${idx})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-md transition-all" title="Duplicar Insumo">
                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                        </button>
                        <button type="button" onclick="removeBomRow(${idx})" class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-all" title="Remover Insumo">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    refreshIcons();
}

// ================= REAL-TIME CLIENT-SIDE FINANCIAL CALCULATION =================

function recalcLiveSummary() {
    const printersMap = {};
    state.printers.forEach(p => { printersMap[p.id] = p; });

    const filamentsMap = {};
    state.filaments.forEach(f => { filamentsMap[f.id] = f; });

    let totalPlatesCost = 0;
    let totalMaterialCost = 0;
    let totalMachineCost = 0;
    let totalTimeHours = 0;
    let totalWeightGrams = 0;

    // 1. Plates math
    state.currentPlates.forEach((plate, idx) => {
        const printer = plate.printer_id ? printersMap[plate.printer_id] : null;
        const filament = plate.filament_id ? filamentsMap[plate.filament_id] : null;

        // Cost per gram
        let costPerGram = 0;
        if (filament && filament.spool_weight_g > 0) {
            costPerGram = filament.spool_price / filament.spool_weight_g;
        } else if (plate.custom_filament_cost_per_g != null) {
            costPerGram = Math.max(0, parseLocaleFloat(plate.custom_filament_cost_per_g, 0));
        } else {
            costPerGram = 0.10; // aligned with visual fallback of 0.10/g
        }

        // Machine rate
        let machineHourlyRate = 0;
        if (printer) {
            machineHourlyRate = printer.machine_hourly_rate ?? 2.0;
        } else if (plate.custom_printer_hourly_rate != null) {
            machineHourlyRate = Math.max(0, parseLocaleFloat(plate.custom_printer_hourly_rate, 0));
        } else {
            machineHourlyRate = 2.50; // aligned with visual fallback of 2.50/h
        }

        const qty = Math.max(1, parseInt(plate.quantity, 10) || 1);
        const printTime = Math.max(0, plate.print_time_hours || 0);
        const rawWeight = Math.max(0, (plate.part_weight_g || 0) + (plate.purge_weight_g || 0));
        const failureFactor = Math.max(1.0, 1.0 + (Math.max(0, plate.failure_margin_percent || 0) / 100));
        const effectiveWeight = rawWeight * failureFactor;

        const unitMaterialCost = effectiveWeight * costPerGram;
        const unitMachineCost = printTime * machineHourlyRate;
        const unitTotalCost = unitMaterialCost + unitMachineCost;

        const plateTotalCost = unitTotalCost * qty;
        totalPlatesCost += plateTotalCost;
        totalMaterialCost += unitMaterialCost * qty;
        totalMachineCost += unitMachineCost * qty;
        totalTimeHours += printTime * qty;
        totalWeightGrams += rawWeight * qty;

        // Update single plate cost pill
        const costEl = document.getElementById(`plate-cost-${idx}`);
        const sumTextEl = document.getElementById(`plate-summary-text-${idx}`);
        if (costEl) costEl.textContent = formatCurrency(plateTotalCost);
        if (sumTextEl) {
            const plateTotalTime = printTime * qty;
            const formattedTime = plateTotalTime > 0 && plateTotalTime < 0.1
                ? (Math.round(plateTotalTime * 60) < 1 ? `<1m (~${Math.max(1, Math.round(plateTotalTime * 3600))}s)` : `${Math.round(plateTotalTime * 60)}min`)
                : `${plateTotalTime.toFixed(1)}h`;
            sumTextEl.textContent = `${qty}x • ${formattedTime} • ${(rawWeight * qty).toFixed(1)}g (Mat: ${formatCurrency(unitMaterialCost * qty)} + Máq: ${formatCurrency(unitMachineCost * qty)})`;
        }
    });

    // 2. BOM Items math
    let totalBOMCost = 0;
    state.currentBOM.forEach((item, idx) => {
        const qty = Math.max(1, item.quantity || 1);
        const unit = Math.max(0, item.unit_cost || 0);
        const subtotal = qty * unit;
        totalBOMCost += subtotal;
        const subEl = document.getElementById(`bom-subtotal-${idx}`);
        if (subEl) subEl.textContent = formatCurrency(subtotal);
    });

    // 3. Labor costs
    const defaultCadRate = state.user?.default_cad_rate ?? 50;
    const defaultPostRate = state.user?.default_post_rate ?? 30;
    const defaultMargin = state.user?.default_profit_margin ?? 30;

    const cadHours = Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-hours')?.value, 0));
    const cadRate = Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate')?.value, defaultCadRate));
    const cadCost = cadHours * cadRate;

    const postHours = Math.max(0, parseLocaleFloat(document.getElementById('proj-post-hours')?.value, 0));
    const postRate = Math.max(0, parseLocaleFloat(document.getElementById('proj-post-rate')?.value, defaultPostRate));
    const postCost = postHours * postRate;

    const totalLaborCost = cadCost + postCost;

    // 4. Overhead & Base Cost
    const overheadCost = Math.max(0, parseLocaleFloat(document.getElementById('proj-overhead')?.value, 0));
    const baseCost = totalPlatesCost + totalBOMCost + totalLaborCost + overheadCost;

    // 5. Pricing, Margins, Taxes
    const marginPercent = Math.max(0, parseLocaleFloat(document.getElementById('proj-margin')?.value, defaultMargin));
    const taxPercent = Math.max(0, Math.min(99, parseLocaleFloat(document.getElementById('proj-tax')?.value, 0)));
    const discountPercent = Math.max(0, Math.min(100, parseLocaleFloat(document.getElementById('proj-discount')?.value, 0)));
    const shippingCost = Math.max(0, parseLocaleFloat(document.getElementById('proj-shipping')?.value, 0));

    const taxDivisor = Math.max(0.01, 1.0 - (taxPercent / 100.0));
    const suggestedPrice = baseCost > 0 
        ? Math.round(((baseCost * (1.0 + (marginPercent / 100.0))) / taxDivisor) * 100) / 100 
        : 0;

    const discountAmount = Math.round(suggestedPrice * (discountPercent / 100.0) * 100) / 100;
    const subtotalAfterDiscount = Math.round((suggestedPrice - discountAmount) * 100) / 100;
    const taxAmount = Math.round(subtotalAfterDiscount * (taxPercent / 100.0) * 100) / 100;
    const netRevenue = Math.round((subtotalAfterDiscount - taxAmount) * 100) / 100;
    const netProfit = Math.round((netRevenue - baseCost) * 100) / 100;
    const effectiveMarginPercent = baseCost > 0 ? Math.round((netProfit / baseCost * 100.0) * 100) / 100 : 0;
    const finalPriceToClient = Math.round((subtotalAfterDiscount + shippingCost) * 100) / 100;

    // Update Live Summary DOM
    const liveTimeFormatted = totalTimeHours > 0 && totalTimeHours < 0.1
        ? (Math.round(totalTimeHours * 60) < 1 ? `<1 min (~${Math.max(1, Math.round(totalTimeHours * 3600))}s)` : `${Math.round(totalTimeHours * 60)} min`)
        : `${totalTimeHours.toFixed(1)} h`;
    setText('live-weight', `${totalWeightGrams.toFixed(1)} g`);
    setText('live-time', liveTimeFormatted);
    setText('live-material-cost', formatCurrency(totalMaterialCost));
    setText('live-machine-cost', formatCurrency(totalMachineCost));
    setText('live-bom-cost', formatCurrency(totalBOMCost));
    setText('live-labor-cost', formatCurrency(totalLaborCost));
    setText('live-overhead-cost', formatCurrency(overheadCost));
    setText('live-base-cost', formatCurrency(baseCost));
    setText('live-suggested-price', formatCurrency(suggestedPrice));
    setText('live-discount-amount', `- ${formatCurrency(discountAmount)}`);
    setText('live-shipping-amount', `+ ${formatCurrency(shippingCost)}`);
    setText('live-tax-amount', formatCurrency(taxAmount));
    setText('live-final-price', formatCurrency(finalPriceToClient));
    setText('live-net-profit', formatCurrency(netProfit));

    // Dynamic Net Profit & Margin Color Indicator
    const netProfitEl = document.getElementById('live-net-profit');
    if (netProfitEl) {
        if (netProfit < 0) {
            netProfitEl.className = 'font-mono font-bold text-sm text-rose-400';
        } else if (effectiveMarginPercent >= 20) {
            netProfitEl.className = 'font-mono font-bold text-sm text-emerald-400';
        } else if (effectiveMarginPercent >= 5) {
            netProfitEl.className = 'font-mono font-bold text-sm text-amber-400';
        } else {
            netProfitEl.className = 'font-mono font-bold text-sm text-slate-300';
        }
    }

    const marginPill = document.querySelector('.profit-margin-pill');
    if (marginPill) {
        marginPill.textContent = `${effectiveMarginPercent >= 0 ? '+' : ''}${effectiveMarginPercent.toFixed(1)}%`;
        if (netProfit < 0) {
            marginPill.className = 'profit-margin-pill px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-rose-500/15 text-rose-400 border border-rose-500/30';
        } else if (effectiveMarginPercent >= 20) {
            marginPill.className = 'profit-margin-pill px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30';
        } else if (effectiveMarginPercent >= 5) {
            marginPill.className = 'profit-margin-pill px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30';
        } else {
            marginPill.className = 'profit-margin-pill px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-slate-800 text-slate-400 border border-slate-700';
        }
    }

    // Dynamic Cost Distribution Mini-Bar
    const barMat = document.querySelector('.cost-bar-mat');
    const barMach = document.querySelector('.cost-bar-mach');
    const barLabor = document.querySelector('.cost-bar-labor');
    const barBom = document.querySelector('.cost-bar-bom');
    const barOver = document.querySelector('.cost-bar-over');
    if (barMat && barMach && barLabor && barBom && barOver) {
        if (baseCost > 0) {
            barMat.style.width = `${((totalMaterialCost / baseCost) * 100).toFixed(1)}%`;
            barMach.style.width = `${((totalMachineCost / baseCost) * 100).toFixed(1)}%`;
            barLabor.style.width = `${((totalLaborCost / baseCost) * 100).toFixed(1)}%`;
            barBom.style.width = `${((totalBOMCost / baseCost) * 100).toFixed(1)}%`;
            barOver.style.width = `${((overheadCost / baseCost) * 100).toFixed(1)}%`;
        } else {
            barMat.style.width = '20%';
            barMach.style.width = '20%';
            barLabor.style.width = '20%';
            barBom.style.width = '20%';
            barOver.style.width = '20%';
        }
    }
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

// ================= SAVING & EXPORTING =================

async function saveCurrentProject(navigateBack = true) {
    normalizeNumericInputs();
    if (state.currentPlates) {
        state.currentPlates.forEach((_, idx) => updatePlateTime(idx));
    }
    const name = document.getElementById('proj-name').value.trim();
    if (!name) {
        showToast('Por favor, informe o título do projeto.', 'error');
        document.getElementById('proj-name').focus();
        return false;
    }

    if ((!state.currentPlates || state.currentPlates.length === 0) && (!state.currentBOM || state.currentBOM.length === 0)) {
        showToast('Aviso: orçamento sem placas ou insumos configurados.', 'warning');
    }

    const defaultCadRate = state.user?.default_cad_rate ?? 50;
    const defaultPostRate = state.user?.default_post_rate ?? 30;
    const defaultMargin = state.user?.default_profit_margin ?? 30;

    const payload = {
        name,
        client_name: document.getElementById('proj-client-name').value.trim(),
        client_email: document.getElementById('proj-client-email').value.trim(),
        client_phone: document.getElementById('proj-client-phone').value.trim(),
        status: document.getElementById('proj-status').value,
        cad_hours: Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-hours').value, 0)),
        cad_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate').value, defaultCadRate)),
        post_process_hours: Math.max(0, parseLocaleFloat(document.getElementById('proj-post-hours').value, 0)),
        post_process_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-post-rate').value, defaultPostRate)),
        overhead_cost: Math.max(0, parseLocaleFloat(document.getElementById('proj-overhead').value, 0)),
        profit_margin_percent: Math.max(0, parseLocaleFloat(document.getElementById('proj-margin').value, defaultMargin)),
        tax_rate_percent: Math.max(0, Math.min(99, parseLocaleFloat(document.getElementById('proj-tax').value, 0))),
        discount_percent: Math.max(0, Math.min(100, parseLocaleFloat(document.getElementById('proj-discount').value, 0))),
        shipping_cost: Math.max(0, parseLocaleFloat(document.getElementById('proj-shipping').value, 0)),
        delivery_days: (() => {
            const raw = document.getElementById('proj-delivery-days')?.value.trim();
            if (!raw) return null;
            const d = parseInt(raw, 10);
            return isNaN(d) || d < 0 ? null : d;
        })(),
        payment_terms: document.getElementById('proj-payment-terms')?.value.trim() || null,
        warranty_terms: document.getElementById('proj-warranty-terms')?.value.trim() || null,
        notes: document.getElementById('proj-notes').value.trim(),
        plates: state.currentPlates.map((p, idx) => {
            const pValidPrinter = !!(p.printer_id && state.printers.some(pr => pr.id === p.printer_id));
            const pValidFilament = !!(p.filament_id && state.filaments.some(fi => fi.id === p.filament_id));
            return {
                name: (p.name || '').trim() || `Placa ${idx + 1}`,
                printer_id: pValidPrinter ? p.printer_id : null,
                filament_id: pValidFilament ? p.filament_id : null,
                custom_printer_hourly_rate: pValidPrinter ? null : (p.custom_printer_hourly_rate != null ? Math.max(0, parseLocaleFloat(p.custom_printer_hourly_rate, 2.50)) : 2.50),
                custom_filament_cost_per_g: pValidFilament ? null : (p.custom_filament_cost_per_g != null ? Math.max(0, parseLocaleFloat(p.custom_filament_cost_per_g, 0.10)) : 0.10),
                nozzle_diameter: p.nozzle_diameter || '0.4',
                bed_type: p.bed_type || 'Textured PEI',
                layer_height: p.layer_height || '0.20',
                print_time_hours: Math.max(0, parseLocaleFloat(p.print_time_hours, 0)),
                part_weight_g: Math.max(0, parseLocaleFloat(p.part_weight_g, 0)),
                purge_weight_g: Math.max(0, parseLocaleFloat(p.purge_weight_g, 0)),
                failure_margin_percent: Math.max(0, parseLocaleFloat(p.failure_margin_percent, 0)),
                quantity: Math.max(1, parseInt(p.quantity, 10) || 1),
                slicer_filament_profile: p.slicer_filament_profile || null,
                notes: p.notes,
            };
        }),
        bom_items: state.currentBOM.map((b, idx) => ({
            name: (b.name || '').trim() || `Insumo ${idx + 1}`,
            category: b.category,
            quantity: Math.max(1, parseInt(b.quantity, 10) || 1),
            unit_cost: Math.max(0, parseLocaleFloat(b.unit_cost, 0)),
            notes: b.notes,
        })),
    };

    try {
        if (state.currentProject && state.currentProject.id) {
            // Update existing
            const updated = await API.projects.update(state.currentProject.id, payload);
            showToast('Projeto atualizado com sucesso!', 'success');
            state.currentProject = updated;
        } else {
            // Create new
            const created = await API.projects.create(payload);
            showToast('Projeto criado com sucesso!', 'success');
            state.currentProject = created;
        }

        await loadAllData();
        if (navigateBack) {
            navigateTo('projects');
        } else if (state.currentProject && state.currentProject.id) {
            if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
                const targetHash = `#/project-editor?id=${state.currentProject.id}`;
                if (window.location.hash !== targetHash) {
                    window.location.hash = targetHash;
                }
            }
        }
        return true;
    } catch (err) {
        showToast(err.message, 'error');
        return false;
    }
}

async function exportCurrentPdf(type = 'client') {
    const saved = await saveCurrentProject(false);
    if (!saved || !state.currentProject || !state.currentProject.id) {
        return;
    }
    API.pdf.preview(state.currentProject.id, type);
}

async function duplicateProject(id) {
    try {
        await API.projects.duplicate(id);
        showToast('Projeto duplicado com sucesso!', 'success');
        await loadAllData();
        renderProjectsTable();
        renderRecentProjects();
        if (state.activeView === 'dashboard') {
            renderDashboard();
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteProject(id) {
    if (!confirm('Deseja realmente excluir este orçamento?')) return;
    try {
        await API.projects.delete(id);
        if (state.currentProject && state.currentProject.id === id) {
            state.currentProject = null;
            if (state.activeView === 'project-editor') {
                openNewProject();
            }
        }
        showToast('Projeto excluído com sucesso.', 'success');
        await loadAllData();
        renderProjectsTable();
        renderRecentProjects();
        if (state.activeView === 'dashboard') {
            renderDashboard();
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ================= FILE IMPORT HANDLERS (HYBRID 3MF / G-CODE) =================

function setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-slicer-input');

    if (!dropzone || !fileInput) return;

    if (dropzone._dropzoneInitialized) return;
    dropzone._dropzoneInitialized = true;

    dropzone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    fileInput.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSlicerFiles(Array.from(e.dataTransfer.files));
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSlicerFiles(Array.from(e.target.files));
            // Reset so same file can be re-selected (issue #20)
            e.target.value = '';
        }
    });

    // Window-level drag-and-drop fallback so dropping anywhere in project-editor imports files
    window.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    window.addEventListener('drop', (e) => {
        e.preventDefault();
        if (state.activeView === 'project-editor' && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            if (!dropzone.contains(e.target)) {
                handleSlicerFiles(Array.from(e.dataTransfer.files));
            }
        }
    });
}

async function handleSlicerFile(file) {
    return handleSlicerFiles([file]);
}

async function handleSlicerFiles(files) {
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);

    // Natural sort files by filename so plate_1, plate_2, ... plate_10 are processed in order
    fileList.sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { numeric: true, sensitivity: 'base' }));

    if (fileList.length === 1) {
        showToast(`Processando metadados de ${fileList[0].name}...`, 'info');
    } else {
        showToast(`Processando lote de ${fileList.length} arquivos...`, 'info');
    }

    const defaultPrinter = state.printers[0] || null;
    const allExtractedPlates = [];
    let successCount = 0;

    for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        const name = (file.name || '').toLowerCase();
        // Exact filename without extension
        const cleanFileName = (file.name || `Placa ${allExtractedPlates.length + 1}`).replace(/^.*[\\\/]/, '').replace(/\.(?:gcode\.3mf|3mf|gcode)$/i, '').trim();

        try {
            if (name.endsWith('.3mf') || name.endsWith('.gcode.3mf')) {
                const plates = await parse3mfMetadata(file);
                if (plates && plates.length > 0) {
                    // USER REQUIREMENT: Name of each plate MUST be the corresponding filename without extension
                    if (cleanFileName) {
                        if (plates.length === 1) {
                            plates[0].name = cleanFileName;
                        } else {
                            plates.forEach((p, pIdx) => {
                                p.name = `${cleanFileName} - Placa ${pIdx + 1}`;
                            });
                        }
                    }

                    plates.forEach(p => {
                        // Apply default printer
                        if (defaultPrinter) {
                            p.printer_id = defaultPrinter.id;
                            p.custom_printer_hourly_rate = null;
                        } else {
                            p.printer_id = null;
                            p.custom_printer_hourly_rate = 2.50;
                        }

                        // Match filament material & profile
                        const matchedFilament = (typeof findBestMatchingFilament === 'function')
                            ? findBestMatchingFilament(
                                state.filaments,
                                p.name || '',
                                p.slicer_filament_profile || '',
                                p.filament_type || '',
                                p.filament_color_hex || ''
                            )
                            : (state.filaments?.find(f => (f.material || '').toLowerCase() === (p.filament_type || '').toLowerCase()) || null);

                        if (matchedFilament) {
                            p.filament_id = matchedFilament.id;
                            p.custom_filament_cost_per_g = null;
                        } else {
                            p.filament_id = null;
                            p.custom_filament_cost_per_g = 0.10;
                        }

                        p.nozzle_diameter = p.nozzle_diameter || '0.4';
                        p.bed_type = p.bed_type || 'Textured PEI';
                        p.layer_height = p.layer_height || '0.20';
                        p.failure_margin_percent = (state.user?.default_failure_rate ?? 10);
                        p.quantity = p.quantity || 1;
                        p.notes = p.notes || '';
                    });

                    allExtractedPlates.push(...plates);
                    successCount++;
                }
            } else if (name.endsWith('.gcode')) {
                const text = await file.text();
                const meta = parseGcodeMetadata(text);
                const newPlate = {
                    name: cleanFileName || `Placa ${allExtractedPlates.length + 1}`,
                    printer_id: defaultPrinter ? defaultPrinter.id : null,
                    filament_id: null,
                    custom_printer_hourly_rate: defaultPrinter ? null : 2.50,
                    custom_filament_cost_per_g: null,
                    nozzle_diameter: meta.nozzle_diameter || '0.4',
                    bed_type: meta.bed_type || 'Textured PEI',
                    layer_height: meta.layer_height || '0.20',
                    print_time_hours: meta.print_time_hours || 0,
                    part_weight_g: meta.part_weight_g || 0,
                    purge_weight_g: 0,
                    slicer_filament_profile: cleanFilamentProfileName(meta.slicer_filament_profile, file.name) || null,
                    failure_margin_percent: (state.user?.default_failure_rate ?? 10),
                    quantity: 1,
                    notes: '',
                };

                const matchedFilament = (typeof findBestMatchingFilament === 'function')
                    ? findBestMatchingFilament(
                        state.filaments,
                        newPlate.name || '',
                        meta.slicer_filament_profile || '',
                        meta.filament_type || '',
                        meta.filament_color_hex || ''
                    )
                    : (state.filaments?.find(f => (f.material || '').toLowerCase() === (meta.filament_type || '').toLowerCase()) || null);

                if (matchedFilament) {
                    newPlate.filament_id = matchedFilament.id;
                    newPlate.custom_filament_cost_per_g = null;
                } else {
                    newPlate.filament_id = null;
                    newPlate.custom_filament_cost_per_g = 0.10;
                }

                allExtractedPlates.push(newPlate);
                successCount++;
            } else {
                showToast(`Formato não suportado para "${file.name || 'arquivo'}". Utilize arquivos .3mf, .gcode ou .gcode.3mf.`, 'error');
            }
        } catch (err) {
            showToast(`Erro ao ler "${file.name || 'arquivo'}": ${err.message}`, 'error');
        }
    }

    if (allExtractedPlates.length > 0) {
        // If only 1 empty plate exists, replace it, else append
        if (state.currentPlates.length === 1 && state.currentPlates[0].print_time_hours === 0 && state.currentPlates[0].part_weight_g === 0) {
            state.currentPlates = allExtractedPlates;
        } else {
            state.currentPlates = [...state.currentPlates, ...allExtractedPlates];
        }

        if (fileList.length === 1) {
            const firstName = (fileList[0].name || '').toLowerCase();
            const fileTypeLabel = firstName.endsWith('.gcode.3mf') ? '.gcode.3mf' : firstName.endsWith('.gcode') ? 'G-Code' : '3MF';
            showToast(`Arquivo ${fileTypeLabel} lido! ${allExtractedPlates.length} placa(s) adicionada(s).`, 'success');
        } else {
            showToast(`Lote concluído: ${successCount} arquivo(s) processado(s)! ${allExtractedPlates.length} placa(s) adicionada(s).`, 'success');
        }

        renderPlates();
        recalcLiveSummary();
    }
}

async function handleSinglePlateFile(e, plateIdx) {
    const file = e.target.files[0];
    // Reset input value so re-selecting the same file triggers 'change' again (issue #20)
    if (e.target) e.target.value = '';
    if (!file) return;

    try {
        const name = file.name.toLowerCase();
        const cleanName = (file.name || '').replace(/\.(?:gcode\.3mf|3mf|gcode)$/i, '').trim();
        if (name.endsWith('.3mf') || name.endsWith('.gcode.3mf')) {
            const plates = await parse3mfMetadata(file);
            if (plates.length > 0) {
                if (cleanName) {
                    state.currentPlates[plateIdx].name = plates.length > 1 ? `${cleanName} - Placa 1` : cleanName;
                }
                state.currentPlates[plateIdx].print_time_hours = plates[0].print_time_hours;
                state.currentPlates[plateIdx].part_weight_g = plates[0].part_weight_g;
                state.currentPlates[plateIdx].purge_weight_g = plates[0].purge_weight_g;
                state.currentPlates[plateIdx].slicer_filament_profile = cleanFilamentProfileName(plates[0].slicer_filament_profile, file.name) || null;
                if (plates[0].nozzle_diameter) state.currentPlates[plateIdx].nozzle_diameter = plates[0].nozzle_diameter;
                if (plates[0].layer_height) state.currentPlates[plateIdx].layer_height = plates[0].layer_height;
                if (plates[0].bed_type) state.currentPlates[plateIdx].bed_type = plates[0].bed_type;
                if (plates[0].notes) {
                    state.currentPlates[plateIdx].notes = plates[0].notes;
                }

                const matchedFilament = (typeof findBestMatchingFilament === 'function')
                    ? findBestMatchingFilament(
                        state.filaments,
                        state.currentPlates[plateIdx].name || '',
                        plates[0].slicer_filament_profile || '',
                        plates[0].filament_type || '',
                        plates[0].filament_color_hex || ''
                    )
                    : (state.filaments?.find(f => (f.material || '').toLowerCase() === (plates[0].filament_type || '').toLowerCase()) || null);
                if (matchedFilament) {
                    state.currentPlates[plateIdx].filament_id = matchedFilament.id;
                    state.currentPlates[plateIdx].custom_filament_cost_per_g = null;
                } else {
                    state.currentPlates[plateIdx].filament_id = null;
                    if (state.currentPlates[plateIdx].custom_filament_cost_per_g == null) {
                        state.currentPlates[plateIdx].custom_filament_cost_per_g = 0.10;
                    }
                }

                if (plates.length > 1) {
                    const additionalPlates = plates.slice(1).map((p, sliceIdx) => {
                        const plateNum = sliceIdx + 2;
                        const plateName = cleanName ? `${cleanName} - Placa ${plateNum}` : `Placa ${plateIdx + plateNum}`;
                        const basePrinterId = state.currentPlates[plateIdx].printer_id ?? (state.printers?.[0]?.id || null);
                        const newP = {
                            name: plateName,
                            printer_id: basePrinterId,
                            filament_id: null,
                            custom_printer_hourly_rate: basePrinterId ? null : (state.currentPlates[plateIdx].custom_printer_hourly_rate ?? 2.50),
                            custom_filament_cost_per_g: null,
                            nozzle_diameter: p.nozzle_diameter || state.currentPlates[plateIdx].nozzle_diameter || '0.4',
                            bed_type: p.bed_type || state.currentPlates[plateIdx].bed_type || 'Textured PEI',
                            layer_height: p.layer_height || state.currentPlates[plateIdx].layer_height || '0.20',
                            print_time_hours: p.print_time_hours || 0,
                            part_weight_g: p.part_weight_g || 0,
                            purge_weight_g: p.purge_weight_g || 0,
                            slicer_filament_profile: cleanFilamentProfileName(p.slicer_filament_profile, file.name) || null,
                            failure_margin_percent: (state.user?.default_failure_rate ?? 10),
                            quantity: p.quantity || 1,
                            notes: p.notes || '',
                        };

                        const matched = (typeof findBestMatchingFilament === 'function')
                            ? findBestMatchingFilament(
                                state.filaments,
                                newP.name || '',
                                p.slicer_filament_profile || '',
                                p.filament_type || '',
                                p.filament_color_hex || ''
                            )
                            : (state.filaments?.find(f => (f.material || '').toLowerCase() === (p.filament_type || '').toLowerCase()) || null);

                        if (matched) {
                            newP.filament_id = matched.id;
                            newP.custom_filament_cost_per_g = null;
                        } else {
                            newP.filament_id = null;
                            newP.custom_filament_cost_per_g = 0.10;
                        }
                        return newP;
                    });

                    state.currentPlates.splice(plateIdx + 1, 0, ...additionalPlates);
                    showToast(`Placa atualizada e ${plates.length - 1} nova(s) placa(s) adicionada(s) a partir do arquivo 3MF!`, 'success');
                } else {
                    const fileTypeLabel = name.endsWith('.gcode.3mf') ? '.gcode.3mf' : '3MF';
                    showToast(`Placa atualizada com dados do ${fileTypeLabel}!`, 'success');
                }
            }
        } else if (name.endsWith('.gcode')) {
            const text = await file.text();
            const meta = parseGcodeMetadata(text, file.name);
            if (cleanName) {
                state.currentPlates[plateIdx].name = cleanName;
            }
            state.currentPlates[plateIdx].print_time_hours = meta.print_time_hours;
            state.currentPlates[plateIdx].part_weight_g = meta.part_weight_g;
            state.currentPlates[plateIdx].purge_weight_g = 0;
            state.currentPlates[plateIdx].slicer_filament_profile = cleanFilamentProfileName(meta.slicer_filament_profile, file.name) || null;
            if (meta.nozzle_diameter) state.currentPlates[plateIdx].nozzle_diameter = meta.nozzle_diameter;
            if (meta.layer_height) state.currentPlates[plateIdx].layer_height = meta.layer_height;
            if (meta.bed_type) state.currentPlates[plateIdx].bed_type = meta.bed_type;
            if (meta.notes) {
                state.currentPlates[plateIdx].notes = meta.notes;
            }

            const matchedFilament = (typeof findBestMatchingFilament === 'function')
                ? findBestMatchingFilament(
                    state.filaments,
                    state.currentPlates[plateIdx].name || '',
                    meta.slicer_filament_profile || '',
                    meta.filament_type || '',
                    meta.filament_color_hex || ''
                )
                : (state.filaments?.find(f => (f.material || '').toLowerCase() === (meta.filament_type || '').toLowerCase()) || null);
                if (matchedFilament) {
                    state.currentPlates[plateIdx].filament_id = matchedFilament.id;
                    state.currentPlates[plateIdx].custom_filament_cost_per_g = null;
                } else {
                    state.currentPlates[plateIdx].filament_id = null;
                    if (state.currentPlates[plateIdx].custom_filament_cost_per_g == null) {
                        state.currentPlates[plateIdx].custom_filament_cost_per_g = 0.10;
                    }
                }

            showToast(`Placa atualizada com dados do G-Code!`, 'success');
        } else {
            showToast('Formato não suportado. Utilize arquivos .3mf, .gcode ou .gcode.3mf.', 'error');
            return;
        }
        renderPlates();
        recalcLiveSummary();
    } catch (err) {
        showToast(`Erro ao carregar arquivo: ${err.message}`, 'error');
    }
}

function updatePrinterRatePreview() {
    const costInput = document.getElementById('printer-cost');
    const lifespanInput = document.getElementById('printer-lifespan');
    const powerInput = document.getElementById('printer-power');
    const maintInput = document.getElementById('printer-maintenance');
    const energyInput = document.getElementById('printer-energy');

    const previewEl = document.getElementById('printer-rate-preview-value');
    if (!previewEl) return;

    const cost = Math.max(0, parseLocaleFloat(costInput?.value, 0));
    const lifespan = Math.max(0, parseLocaleFloat(lifespanInput?.value, 5000));
    const power = Math.max(0, parseLocaleFloat(powerInput?.value, 150));
    const maint = Math.max(0, parseLocaleFloat(maintInput?.value, 1.0));
    const energy = Math.max(0, parseLocaleFloat(energyInput?.value, 0.85));

    const depPerHour = lifespan > 0 ? (cost / lifespan) : 0;
    const energyPerHour = (power / 1000.0) * energy;
    const totalRate = depPerHour + maint + energyPerHour;

    previewEl.textContent = formatCurrency(totalRate);

    const depEl = document.getElementById('printer-rate-preview-dep');
    if (depEl) depEl.textContent = `${formatCurrency(depPerHour)}/h`;
    const energyEl = document.getElementById('printer-rate-preview-energy');
    if (energyEl) energyEl.textContent = `${formatCurrency(energyPerHour)}/h`;
    const maintEl = document.getElementById('printer-rate-preview-maint');
    if (maintEl) maintEl.textContent = `${formatCurrency(maint)}/h`;
}
window.updatePrinterRatePreview = updatePrinterRatePreview;

function editPrinter(id) {
    const printer = state.printers.find(p => p.id === id);
    if (printer) openPrinterModal(printer);
}

function openPrinterModal(printer = null) {
    const modal = document.getElementById('modal-printer');
    const title = document.getElementById('modal-printer-title');
    modal.classList.remove('hidden');

    if (printer) {
        title.innerHTML = `<i data-lucide="printer" class="w-5 h-5 text-blue-400"></i> Editar Impressora`;
        document.getElementById('printer-id').value = printer.id;
        document.getElementById('printer-name').value = printer.name;
        document.getElementById('printer-model').value = printer.model || '';
        document.getElementById('printer-cost').value = printer.acquisition_cost;
        document.getElementById('printer-lifespan').value = printer.lifespan_hours;
        document.getElementById('printer-power').value = printer.avg_power_watts;
        document.getElementById('printer-maintenance').value = printer.maintenance_cost_per_hour;
        document.getElementById('printer-energy').value = printer.energy_rate_kwh;
        const activeEl = document.getElementById('printer-active');
        if (activeEl) activeEl.value = printer.is_active !== false ? 'true' : 'false';
    } else {
        title.innerHTML = `<i data-lucide="printer" class="w-5 h-5 text-blue-400"></i> Cadastrar Impressora`;
        document.getElementById('printer-id').value = '';
        document.getElementById('printer-name').value = '';
        document.getElementById('printer-model').value = '';
        document.getElementById('printer-cost').value = '3500';
        document.getElementById('printer-lifespan').value = '5000';
        document.getElementById('printer-power').value = '150';
        document.getElementById('printer-maintenance').value = '1.0';
        document.getElementById('printer-energy').value = (state.user?.default_energy_rate ?? 0.85);
        const activeEl = document.getElementById('printer-active');
        if (activeEl) activeEl.value = 'true';
    }
    updatePrinterRatePreview();
    refreshIcons();
}

function closePrinterModal() {
    document.getElementById('modal-printer').classList.add('hidden');
}

async function handleSavePrinter(e) {
    e.preventDefault();
    normalizeNumericInputs();
    const id = document.getElementById('printer-id').value;
    const name = document.getElementById('printer-name').value.trim();
    if (!name) {
        showToast('Informe o nome ou identificação da impressora.', 'error');
        document.getElementById('printer-name')?.focus();
        return;
    }

    const lifespanHours = parseLocaleFloat(document.getElementById('printer-lifespan').value, 5000);
    if (isNaN(lifespanHours) || lifespanHours <= 0) {
        showToast('A vida útil estimada da impressora deve ser maior que zero.', 'error');
        document.getElementById('printer-lifespan')?.focus();
        return;
    }

    const acquisitionCost = parseLocaleFloat(document.getElementById('printer-cost').value, 0);
    if (isNaN(acquisitionCost) || acquisitionCost < 0) {
        showToast('O custo de aquisição da impressora não pode ser negativo.', 'error');
        document.getElementById('printer-cost')?.focus();
        return;
    }

    const powerWatts = parseLocaleFloat(document.getElementById('printer-power').value, 150);
    if (isNaN(powerWatts) || powerWatts < 0) {
        showToast('A potência média não pode ser negativa.', 'error');
        document.getElementById('printer-power')?.focus();
        return;
    }

    const maintenanceCost = parseLocaleFloat(document.getElementById('printer-maintenance').value, 1.0);
    if (isNaN(maintenanceCost) || maintenanceCost < 0) {
        showToast('A taxa de manutenção não pode ser negativa.', 'error');
        document.getElementById('printer-maintenance')?.focus();
        return;
    }

    const energyRate = parseLocaleFloat(document.getElementById('printer-energy').value, 0.85);
    if (isNaN(energyRate) || energyRate < 0) {
        showToast('A tarifa de energia elétrica não pode ser negativa.', 'error');
        document.getElementById('printer-energy')?.focus();
        return;
    }

    const payload = {
        name,
        model: document.getElementById('printer-model').value.trim(),
        acquisition_cost: acquisitionCost,
        lifespan_hours: lifespanHours,
        avg_power_watts: powerWatts,
        maintenance_cost_per_hour: maintenanceCost,
        energy_rate_kwh: energyRate,
    };
    const activeEl = document.getElementById('printer-active');
    if (activeEl) {
        payload.is_active = activeEl.value !== 'false';
    }

    try {
        if (id) {
            await API.printers.update(id, payload);
            showToast('Impressora atualizada com sucesso!', 'success');
        } else {
            await API.printers.create(payload);
            showToast('Impressora cadastrada com sucesso!', 'success');
        }
        closePrinterModal();
        await loadAllData();
        renderPrintersGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function duplicatePrinter(id) {
    try {
        await API.printers.duplicate(id);
        showToast('Impressora duplicada com sucesso!', 'success');
        await loadAllData();
        renderPrintersGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}
window.duplicatePrinter = duplicatePrinter;

async function deletePrinter(id) {
    if (!confirm('Deseja realmente remover esta impressora?')) return;
    try {
        await API.printers.delete(id);
        showToast('Impressora removida.', 'success');
        await loadAllData();
        renderPrintersGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Issue #22 & #25: Real-time search/filter for printers grid (search term + operational status)
function clearPrinterFilters() {
    const inp = document.getElementById('printer-search-input');
    if (inp) inp.value = '';
    const st = document.getElementById('printer-status-filter');
    if (st) st.value = 'all';
    filterPrinters();
}
window.clearPrinterFilters = clearPrinterFilters;

function filterPrinters() {
    const term = (document.getElementById('printer-search-input')?.value || '').trim();
    const status = (document.getElementById('printer-status-filter')?.value || 'all').trim();
    renderPrintersGrid(term, status);
}
window.filterPrinters = filterPrinters;

function renderPrintersGrid(filterTerm = null, filterStatus = null) {
    const esc = (typeof escapeHtml === 'function') ? escapeHtml : (str => (str == null ? '' : String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;')));
    const grid = document.getElementById('printers-grid');
    if (!grid) return;

    const term = (filterTerm !== null && filterTerm !== undefined ? filterTerm : (document.getElementById('printer-search-input')?.value || '')).trim();
    const status = (filterStatus !== null && filterStatus !== undefined ? filterStatus : (document.getElementById('printer-status-filter')?.value || 'all')).trim();

    let printers = state.printers;
    if (status === 'active') {
        printers = printers.filter(p => p.is_active !== false);
    } else if (status === 'inactive') {
        printers = printers.filter(p => p.is_active === false);
    }
    if (term) {
        printers = printers.filter(p =>
            matchesSearch(`${p.name || ''} ${p.model || ''}`, term)
        );
    }

    if (state.printers.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-12 text-center text-slate-400">
                <i data-lucide="printer" class="w-12 h-12 mx-auto mb-3 text-slate-600"></i>
                <h4 class="text-base font-bold text-white">Nenhuma impressora cadastrada</h4>
                <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">Cadastre suas impressoras reais para calcular depreciação por hora de uso, custo em kWh de energia elétrica e manutenção preventiva.</p>
                <button onclick="openPrinterModal()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold">
                    + Cadastrar Impressora
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    if (printers.length === 0 && (term || status !== 'all')) {
        const statusLabel = status === 'active' ? 'ativas' : (status === 'inactive' ? 'inativas/manutenção' : '');
        const filterDesc = [
            term ? `busca "<strong class="text-white">${esc(term)}</strong>"` : '',
            statusLabel ? `status "<strong class="text-white">${esc(statusLabel)}</strong>"` : ''
        ].filter(Boolean).join(' e ');

        grid.innerHTML = `
            <div class="col-span-full card-dark p-8 text-center text-slate-400">
                <i data-lucide="search-x" class="w-10 h-10 mx-auto mb-3 text-slate-600"></i>
                <p class="text-sm">Nenhuma impressora encontrada para os filtros aplicados (${filterDesc}).</p>
                <button type="button" onclick="clearPrinterFilters()" class="mt-3 inline-block px-3 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 rounded text-xs font-medium transition-colors">
                    Limpar filtros
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    grid.innerHTML = printers.map(p => {
        const rates = p.rates_breakdown || {};
        return `
            <div class="card-dark p-6 space-y-4 hover:border-slate-600 transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="flex items-center gap-2">
                                <h4 class="font-bold text-white text-base">${esc(p.name)}</h4>
                                <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${p.is_active !== false ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40' : 'bg-red-950/40 text-red-400 border border-red-800/40'}">
                                    ${p.is_active !== false ? 'Ativa' : 'Inativa'}
                                </span>
                            </div>
                            <p class="text-xs text-slate-400">${esc(p.model || 'FDM')}</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="editPrinter(${p.id})" class="p-1 text-slate-400 hover:text-white transition-colors" title="Editar">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                            </button>
                            <button onclick="duplicatePrinter(${p.id})" class="p-1 text-slate-400 hover:text-blue-400 transition-colors" title="Duplicar">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                            <button onclick="deletePrinter(${p.id})" class="p-1 text-slate-400 hover:text-red-400 transition-colors" title="Excluir">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Highlighted Machine Rate -->
                    <div class="mt-4 p-3 rounded-lg bg-blue-950/30 border border-blue-800/40 text-center">
                        <span class="text-[10px] uppercase font-semibold text-blue-300 tracking-wider">Tarifa Horária Total</span>
                        <div class="text-2xl font-black text-blue-400 mt-0.5">
                            ${formatCurrency(p.machine_hourly_rate)}<span class="text-xs font-normal text-slate-400">/h</span>
                        </div>
                    </div>

                    <!-- Breakdown Table -->
                    <div class="mt-4 space-y-2 text-xs text-slate-300">
                        <div class="flex justify-between">
                            <span class="text-slate-400">Depreciação:</span>
                            <span>${formatCurrency(rates.depreciation_per_hour || 0)}/h</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-slate-400">Energia (${p.avg_power_watts}W):</span>
                            <span>${formatCurrency(rates.energy_cost_per_hour || 0)}/h</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-slate-400">Reserva Manutenção:</span>
                            <span>${formatCurrency(rates.maintenance_cost_per_hour || 0)}/h</span>
                        </div>
                    </div>
                </div>

                <div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
                    <span>Vida útil: ${p.lifespan_hours} h</span>
                    <span>Aquisição: ${formatCurrency(p.acquisition_cost)}</span>
                </div>
            </div>
        `;
    }).join('');
    refreshIcons();
}


function editFilament(id) {
    const filament = state.filaments.find(f => f.id === id || String(f.id) === String(id));
    if (filament) openFilamentModal(filament);
}

function duplicateFilament(id) {
    const filament = state.filaments.find(f => f.id === id || String(f.id) === String(id));
    if (filament) openFilamentModal(filament, true);
}

// Standard reference densities in g/cm³ for 3D printing polymers
const MATERIAL_DENSITIES = {
    'PLA': 1.24,
    'PETG': 1.27,
    'ABS': 1.04,
    'TPU': 1.21,
    'ASA': 1.07,
    'Resina': 1.15,
    'Outro': 1.24,
};

// Issue #24 & #26: Handle material dropdown change with preview update and suggested density
function onFilamentMaterialChange() {
    const mat = document.getElementById('filament-material')?.value || 'PLA';
    const densityInput = document.getElementById('filament-density');
    if (densityInput) {
        densityInput.value = MATERIAL_DENSITIES[mat] !== undefined ? MATERIAL_DENSITIES[mat] : 1.24;
    }
    updateFilamentNamePreview();
}
window.onFilamentMaterialChange = onFilamentMaterialChange;

function updateFilamentNamePreview() {
    const mat = document.getElementById('filament-material')?.value.trim() || 'PLA';
    const colInput = document.getElementById('filament-color');
    const colVal = colInput?.value.trim();
    const col = colVal || (colInput?.placeholder && colInput.placeholder.includes('nova cor') ? 'Nova Cor' : 'Preto');
    const brd = document.getElementById('filament-brand')?.value.trim() || 'Marca';
    const hex = document.getElementById('filament-color-hex')?.value || '#10b981';
    const textElem = document.getElementById('filament-preview-text');
    const dotElem = document.getElementById('filament-preview-dot');
    if (textElem) textElem.innerText = `${mat} ${col} - ${brd}`;
    if (dotElem) dotElem.style.backgroundColor = hex;
}

function openFilamentModal(filament = null, isDuplicate = false) {
    const modal = document.getElementById('modal-filament');
    const title = document.getElementById('modal-filament-title');
    const colorInput = document.getElementById('filament-color');
    modal.classList.remove('hidden');

    if (filament && !isDuplicate) {
        title.textContent = 'Editar Filamento';
        document.getElementById('filament-id').value = filament.id;
        document.getElementById('filament-material').value = filament.material || 'PLA';
        document.getElementById('filament-brand').value = filament.brand || '';
        document.getElementById('filament-color').value = filament.color || '';
        document.getElementById('filament-color-hex').value = filament.color_hex || '#10b981';
        document.getElementById('filament-density').value = filament.density_g_cm3 != null ? filament.density_g_cm3 : (MATERIAL_DENSITIES[filament.material] || 1.24);
        document.getElementById('filament-weight').value = filament.spool_weight_g;
        document.getElementById('filament-price').value = filament.spool_price;
        const activeEl = document.getElementById('filament-active');
        if (activeEl) activeEl.value = filament.is_active !== false ? 'true' : 'false';
        const notesInput = document.getElementById('filament-notes');
        if (notesInput) notesInput.value = filament.notes || '';
        if (colorInput) colorInput.placeholder = 'Ex: Preto';
    } else if (filament && isDuplicate) {
        title.textContent = 'Cadastrar Filamento (Duplicar)';
        document.getElementById('filament-id').value = '';
        document.getElementById('filament-material').value = filament.material || 'PLA';
        document.getElementById('filament-brand').value = filament.brand || '';
        document.getElementById('filament-color').value = filament.color ? `${filament.color} (Cópia)` : '';
        document.getElementById('filament-color-hex').value = filament.color_hex || '#10b981';
        document.getElementById('filament-density').value = filament.density_g_cm3 != null ? filament.density_g_cm3 : (MATERIAL_DENSITIES[filament.material] || 1.24);
        document.getElementById('filament-weight').value = filament.spool_weight_g;
        document.getElementById('filament-price').value = filament.spool_price;
        const activeEl = document.getElementById('filament-active');
        if (activeEl) activeEl.value = filament.is_active !== false ? 'true' : 'false';
        const notesInput = document.getElementById('filament-notes');
        if (notesInput) notesInput.value = filament.notes || '';
        if (colorInput) {
            colorInput.placeholder = 'Digite a nova cor...';
            try {
                colorInput.focus();
                colorInput.select();
            } catch (_) {}
            setTimeout(() => {
                try {
                    colorInput.focus();
                    colorInput.select();
                } catch (_) {}
            }, 50);
        }
    } else {
        title.textContent = 'Cadastrar Filamento';
        document.getElementById('filament-id').value = '';
        document.getElementById('filament-material').value = 'PLA';
        document.getElementById('filament-brand').value = '';
        document.getElementById('filament-color').value = '';
        document.getElementById('filament-color-hex').value = '#10b981';
        document.getElementById('filament-density').value = '1.24';
        document.getElementById('filament-weight').value = '1000';
        document.getElementById('filament-price').value = '95.00';
        const activeEl = document.getElementById('filament-active');
        if (activeEl) activeEl.value = 'true';
        const notesInput = document.getElementById('filament-notes');
        if (notesInput) notesInput.value = '';
        if (colorInput) colorInput.placeholder = 'Ex: Preto';
    }
    updateFilamentNamePreview();
    refreshIcons();
}

function closeFilamentModal() {
    document.getElementById('modal-filament').classList.add('hidden');
    document.getElementById('filament-id').value = '';
    const colorInput = document.getElementById('filament-color');
    if (colorInput) colorInput.placeholder = 'Ex: Preto';
    const notesInput = document.getElementById('filament-notes');
    if (notesInput) notesInput.value = '';
}

async function handleSaveFilament(e) {
    e.preventDefault();
    normalizeNumericInputs();
    const id = document.getElementById('filament-id').value;
    const mat = document.getElementById('filament-material').value;
    const brand = document.getElementById('filament-brand').value.trim();
    if (!brand) {
        showToast('Informe a marca do filamento.', 'error');
        document.getElementById('filament-brand')?.focus();
        return;
    }
    const color = document.getElementById('filament-color').value.trim();
    if (!color) {
        showToast('Informe a cor do filamento.', 'error');
        document.getElementById('filament-color')?.focus();
        return;
    }
    const colorHex = document.getElementById('filament-color-hex').value || '#10b981';
    const standardName = `${mat} ${color} - ${brand}`;

    const density = parseLocaleFloat(document.getElementById('filament-density')?.value, 1.24);
    if (isNaN(density) || density <= 0) {
        showToast('A densidade do material deve ser maior que zero.', 'error');
        document.getElementById('filament-density')?.focus();
        return;
    }

    const spoolWeight = parseLocaleFloat(document.getElementById('filament-weight').value, 1000);
    if (isNaN(spoolWeight) || spoolWeight <= 0) {
        showToast('O peso do carretel deve ser maior que zero.', 'error');
        document.getElementById('filament-weight')?.focus();
        return;
    }

    const spoolPrice = parseLocaleFloat(document.getElementById('filament-price').value, 0);
    if (isNaN(spoolPrice) || spoolPrice < 0) {
        showToast('O preço do carretel não pode ser negativo.', 'error');
        document.getElementById('filament-price')?.focus();
        return;
    }

    const payload = {
        name: standardName,
        brand: brand,
        material: mat,
        color: color,
        color_hex: colorHex,
        density_g_cm3: density,
        spool_weight_g: spoolWeight,
        spool_price: spoolPrice,
        notes: document.getElementById('filament-notes')?.value.trim() || null,
    };
    const activeEl = document.getElementById('filament-active');
    if (activeEl) {
        payload.is_active = activeEl.value !== 'false';
    }

    try {
        if (id) {
            await API.filaments.update(id, payload);
            showToast('Filamento atualizado com sucesso!', 'success');
        } else {
            await API.filaments.create(payload);
            showToast('Filamento cadastrado com sucesso!', 'success');
        }
        closeFilamentModal();
        await loadAllData();
        renderFilamentsGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteFilament(id) {
    if (!confirm('Deseja realmente remover este filamento?')) return;
    try {
        await API.filaments.delete(id);
        showToast('Filamento removido.', 'success');
        await loadAllData();
        renderFilamentsGrid();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Issue #22 & #25: Real-time search/filter for filaments grid (search term + material filter + status filter)
function clearFilamentFilters() {
    const inp = document.getElementById('filament-search-input');
    if (inp) inp.value = '';
    const mat = document.getElementById('filament-material-filter');
    if (mat) mat.value = '';
    const st = document.getElementById('filament-status-filter');
    if (st) st.value = 'all';
    filterFilaments();
}
window.clearFilamentFilters = clearFilamentFilters;

function filterFilaments() {
    const term = (document.getElementById('filament-search-input')?.value || '').trim();
    const material = (document.getElementById('filament-material-filter')?.value || '').trim();
    const status = (document.getElementById('filament-status-filter')?.value || 'all').trim();
    renderFilamentsGrid(term, material, status);
}
window.filterFilaments = filterFilaments;

function renderFilamentsGrid(filterTerm = null, filterMaterial = null, filterStatus = null) {
    const esc = (typeof escapeHtml === 'function') ? escapeHtml : (str => (str == null ? '' : String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;')));
    const grid = document.getElementById('filaments-grid');
    if (!grid) return;

    const term = (filterTerm !== null && filterTerm !== undefined ? filterTerm : (document.getElementById('filament-search-input')?.value || '')).trim();
    const material = (filterMaterial !== null && filterMaterial !== undefined ? filterMaterial : (document.getElementById('filament-material-filter')?.value || '')).trim();
    const status = (filterStatus !== null && filterStatus !== undefined ? filterStatus : (document.getElementById('filament-status-filter')?.value || 'all')).trim();

    let filaments = state.filaments;
    if (status === 'active') {
        filaments = filaments.filter(f => f.is_active !== false);
    } else if (status === 'inactive') {
        filaments = filaments.filter(f => f.is_active === false);
    }
    if (material) {
        filaments = filaments.filter(f => (f.material || '').toUpperCase() === material.toUpperCase());
    }
    if (term) {
        filaments = filaments.filter(f =>
            matchesSearch(`${f.name || ''} ${f.brand || ''} ${f.material || ''} ${f.color || ''}`, term)
        );
    }

    if (state.filaments.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-12 text-center text-slate-400">
                <i data-lucide="cylinder" class="w-12 h-12 mx-auto mb-3 text-slate-600"></i>
                <h4 class="text-base font-bold text-white">Nenhum filamento cadastrado</h4>
                <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">Cadastre suas marcas e carretéis reais para apurar o custo exato em gramas de cada projeto impresso.</p>
                <button onclick="openFilamentModal()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold">
                    + Cadastrar Filamento
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    if (filaments.length === 0 && (term || material || status !== 'all')) {
        const statusLabel = status === 'active' ? 'ativos' : (status === 'inactive' ? 'inativos/esgotados' : '');
        const filterDesc = [
            term ? `busca "<strong class="text-white">${esc(term)}</strong>"` : '',
            material ? `material "<strong class="text-white">${esc(material)}</strong>"` : '',
            statusLabel ? `status "<strong class="text-white">${esc(statusLabel)}</strong>"` : ''
        ].filter(Boolean).join(' e ');

        grid.innerHTML = `
            <div class="col-span-full card-dark p-8 text-center text-slate-400">
                <i data-lucide="search-x" class="w-10 h-10 mx-auto mb-3 text-slate-600"></i>
                <p class="text-sm">Nenhum filamento encontrado para os filtros aplicados (${filterDesc}).</p>
                <button type="button" onclick="clearFilamentFilters()" class="mt-3 inline-block px-3 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 rounded text-xs font-medium transition-colors">
                    Limpar filtros
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    grid.innerHTML = filaments.map(f => {
        const matLower = (f.material || 'other').toLowerCase();
        const safeHex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$/.test(f.color_hex || '') ? f.color_hex : '#10b981';
        return `
            <div class="card-dark p-6 space-y-4 hover:border-slate-600 transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl border border-slate-700/60 flex items-center justify-center relative shadow-sm" style="background-color: ${safeHex}22;">
                                <span class="w-4 h-4 rounded-full border border-white/30 shadow-sm" style="background-color: ${safeHex};"></span>
                            </div>
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-mat-${matLower}">
                                        ${esc(f.material)}
                                    </span>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${f.is_active !== false ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40' : 'bg-red-950/40 text-red-400 border border-red-800/40'}">
                                        ${f.is_active !== false ? 'Ativo' : 'Inativo'}
                                    </span>
                                    <h4 class="font-bold text-white text-sm">${esc(f.name)}</h4>
                                </div>
                                <p class="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                                    <span class="inline-block w-2.5 h-2.5 rounded-full border border-white/20 shadow-sm" style="background-color: ${safeHex};"></span>
                                    <span>${esc(f.brand || 'Genérico')} • ${esc(f.color || 'Cor padrão')}</span>
                                </p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="duplicateFilament(${f.id})" class="p-1 text-slate-400 hover:text-blue-400 transition-colors" title="Duplicar">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                            <button onclick="editFilament(${f.id})" class="p-1 text-slate-400 hover:text-white transition-colors" title="Editar">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
                            </button>
                            <button onclick="deleteFilament(${f.id})" class="p-1 text-slate-400 hover:text-red-400 transition-colors" title="Excluir">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Highlighted Gram Cost -->
                    <div class="mt-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-center">
                        <span class="text-[10px] uppercase font-semibold text-emerald-300 tracking-wider">Custo por Grama</span>
                        <div class="text-2xl font-black text-emerald-400 mt-0.5" data-cost-fixed="${f.cost_per_gram != null ? f.cost_per_gram.toFixed(2) : '0.00'}">
                            ${formatCurrency(f.cost_per_gram || 0)}<span class="text-xs font-normal text-slate-400">/g</span>
                        </div>
                    </div>
                </div>

                <div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between items-center gap-2">
                    <span>Carretel: ${f.spool_weight_g} g</span>
                    <span>Densidade: ${f.density_g_cm3 != null ? Number(f.density_g_cm3).toFixed(2) : '1.24'} g/cm³</span>
                    <span>Preço: ${formatCurrency(f.spool_price)}</span>
                </div>
                ${f.notes ? `
                <div class="pt-2 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center gap-1.5 truncate" title="${esc(f.notes)}">
                    <i data-lucide="info" class="w-3.5 h-3.5 text-blue-400 shrink-0"></i>
                    <span class="truncate">Obs: ${esc(f.notes)}</span>
                </div>` : ''}
            </div>
        `;
    }).join('');
    refreshIcons();
}


// ================= SETTINGS & PREFERENCES =================

function populateSettingsForm() {
    const u = state.user;
    if (!u) return;

    document.getElementById('pref-company').value = u.company_name || '';
    document.getElementById('pref-fullname').value = u.full_name || '';
    document.getElementById('pref-phone').value = u.phone ? formatPhoneInput(u.phone) : '';
    document.getElementById('pref-pix').value = u.pix_key || '';
    document.getElementById('pref-energy').value = u.default_energy_rate ?? 0.85;
    document.getElementById('pref-margin').value = u.default_profit_margin ?? 30;
    document.getElementById('pref-tax').value = u.default_tax_rate ?? 6;
    document.getElementById('pref-failure').value = u.default_failure_rate ?? 10;
    document.getElementById('pref-cad-rate').value = u.default_cad_rate ?? 50;
    document.getElementById('pref-post-rate').value = u.default_post_rate ?? 30;
    document.getElementById('pref-payment-terms').value = u.default_payment_terms || '';
    document.getElementById('pref-warranty-terms').value = u.default_warranty_terms || '';
}

async function handleSavePreferences(e) {
    e.preventDefault();
    normalizeNumericInputs();

    const energyRate = parseLocaleFloat(document.getElementById('pref-energy').value, 0.85);
    if (isNaN(energyRate) || energyRate < 0) {
        showToast('A tarifa de energia padrão não pode ser negativa.', 'error');
        document.getElementById('pref-energy')?.focus();
        return;
    }
    const profitMargin = parseLocaleFloat(document.getElementById('pref-margin').value, 30);
    if (isNaN(profitMargin) || profitMargin < 0) {
        showToast('A margem de lucro padrão não pode ser negativa.', 'error');
        document.getElementById('pref-margin')?.focus();
        return;
    }
    const taxRate = parseLocaleFloat(document.getElementById('pref-tax').value, 6);
    if (isNaN(taxRate) || taxRate < 0 || taxRate >= 100) {
        showToast('A alíquota de impostos padrão deve estar entre 0% e 99%.', 'error');
        document.getElementById('pref-tax')?.focus();
        return;
    }
    const failureRate = parseLocaleFloat(document.getElementById('pref-failure').value, 10);
    if (isNaN(failureRate) || failureRate < 0) {
        showToast('A taxa de perda padrão não pode ser negativa.', 'error');
        document.getElementById('pref-failure')?.focus();
        return;
    }
    const cadRate = parseLocaleFloat(document.getElementById('pref-cad-rate').value, 50);
    if (isNaN(cadRate) || cadRate < 0) {
        showToast('A taxa horária CAD padrão não pode ser negativa.', 'error');
        document.getElementById('pref-cad-rate')?.focus();
        return;
    }
    const postRate = parseLocaleFloat(document.getElementById('pref-post-rate').value, 30);
    if (isNaN(postRate) || postRate < 0) {
        showToast('A taxa de pós-processamento padrão não pode ser negativa.', 'error');
        document.getElementById('pref-post-rate')?.focus();
        return;
    }

    const payload = {
        company_name: document.getElementById('pref-company').value.trim(),
        full_name: document.getElementById('pref-fullname').value.trim(),
        phone: document.getElementById('pref-phone').value.trim(),
        pix_key: document.getElementById('pref-pix').value.trim(),
        default_energy_rate: energyRate,
        default_profit_margin: profitMargin,
        default_tax_rate: taxRate,
        default_failure_rate: failureRate,
        default_cad_rate: cadRate,
        default_post_rate: postRate,
        default_payment_terms: document.getElementById('pref-payment-terms')?.value.trim() || null,
        default_warranty_terms: document.getElementById('pref-warranty-terms')?.value.trim() || null,
    };

    try {
        const updated = await API.auth.updatePreferences(payload);
        state.user = updated;
        updateUserUI();
        showToast('Preferências salvas com sucesso!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ================= SUMMARY PANEL STICKY HEIGHT ADAPTATION =================

function updateSummaryPanelHeight() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (typeof document.querySelector !== 'function') return;
    const card = document.querySelector('.summary-panel-card');
    if (!card) return;
    if (typeof window.innerWidth === 'number' && window.innerWidth < 1024) {
        card.style.height = '';
        card.style.maxHeight = '';
        return;
    }
    const col = card.parentElement;
    if (!col || typeof col.getBoundingClientRect !== 'function') return;
    const colRect = col.getBoundingClientRect();
    const stickyTop = 80; // 5rem = 80px (offset below header)
    const currentTop = Math.max(colRect.top, stickyTop);
    const bottomMargin = 20; // 20px padding from screen bottom
    const availableHeight = Math.floor((window.innerHeight || 800) - currentTop - bottomMargin);
    if (availableHeight > 320) {
        card.style.height = `${availableHeight}px`;
        card.style.maxHeight = `${availableHeight}px`;
    }
}

function setupSummaryPanelStickyHeight() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const main = typeof document.querySelector === 'function' ? document.querySelector('main') : null;
    if (main && typeof main.addEventListener === 'function') {
        main.addEventListener('scroll', updateSummaryPanelHeight, { passive: true });
    }
    if (typeof window.addEventListener === 'function') {
        window.addEventListener('resize', updateSummaryPanelHeight);
    }
    updateSummaryPanelHeight();
    initSmoothScroll();
}

// ================= SMOOTH SCROLL ENGINE =================

function initSmoothScroll() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    function attachSmoothScroll(element) {
        if (!element || element._hasSmoothScroll || typeof element.addEventListener !== 'function') return;
        element._hasSmoothScroll = true;

        let targetY = element.scrollTop || 0;
        let currentY = element.scrollTop || 0;
        let isRunning = false;

        function step() {
            const diff = targetY - currentY;
            if (Math.abs(diff) < 0.75) {
                currentY = targetY;
                element.scrollTop = Math.round(currentY);
                isRunning = false;
                return;
            }

            // Snappy and natural momentum easing (0.15)
            currentY += diff * 0.15;
            element.scrollTop = Math.round(currentY);
            if (typeof requestAnimationFrame !== 'undefined') {
                requestAnimationFrame(step);
            } else {
                isRunning = false;
            }
        }

        element.addEventListener('wheel', (e) => {
            // Ignore horizontal wheel, zoom gestures (ctrl/meta), or shift modifier
            if (e.ctrlKey || e.metaKey || e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;

            // Sync position if user scrolled via scrollbar thumb or keyboard
            if (!isRunning) {
                currentY = element.scrollTop;
                targetY = element.scrollTop;
            }

            // Normalize line vs pixel delta
            let delta = e.deltaY;
            if (e.deltaMode === 1) delta *= 33; // Line delta
            else if (e.deltaMode === 2) delta *= (element.clientHeight || 500); // Page delta

            const maxScroll = (element.scrollHeight || 0) - (element.clientHeight || 0);
            if (maxScroll <= 0) return;

            // Clamped target
            const nextTarget = Math.max(0, Math.min(maxScroll, targetY + delta));
            if (nextTarget === targetY) return;

            targetY = nextTarget;
            if (typeof e.preventDefault === 'function') {
                e.preventDefault();
            }

            if (!isRunning) {
                isRunning = true;
                if (typeof requestAnimationFrame !== 'undefined') {
                    requestAnimationFrame(step);
                } else {
                    element.scrollTop = targetY;
                    isRunning = false;
                }
            }
        }, { passive: false });

        element.addEventListener('scroll', () => {
            if (!isRunning) {
                currentY = element.scrollTop;
                targetY = element.scrollTop;
            }
        }, { passive: true });
    }

    const main = typeof document.querySelector === 'function' ? document.querySelector('main') : null;
    if (main) attachSmoothScroll(main);

    const panelBody = typeof document.querySelector === 'function' ? document.querySelector('.summary-panel-body') : null;
    if (panelBody) attachSmoothScroll(panelBody);
}

// ================= COLLAPSIBLE SIDEBAR ENGINE =================

function initSidebarState() {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined' || typeof document === 'undefined') return;
    try {
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        const sidebar = document.getElementById('app-sidebar');
        if (sidebar && isCollapsed) {
            sidebar.classList.add('sidebar-collapsed');
            updateSidebarToggleIcons(true);
        }
    } catch (e) {
        // Restricted storage guard
    }
}
window.initSidebarState = initSidebarState;

function toggleSidebar() {
    if (typeof document === 'undefined') return;
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    const isCollapsed = sidebar.classList.toggle('sidebar-collapsed');
    try {
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('sidebar_collapsed', isCollapsed ? 'true' : 'false');
        }
    } catch (e) {}

    updateSidebarToggleIcons(isCollapsed);

    if (typeof refreshIcons === 'function') {
        refreshIcons();
    }
    if (typeof updateSummaryPanelHeight === 'function') {
        setTimeout(updateSummaryPanelHeight, 310);
    }
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new CustomEvent('sidebar:toggle', { detail: { isCollapsed } }));
    }
}
window.toggleSidebar = toggleSidebar;

function toggleSidebarIfCollapsed() {
    if (typeof document === 'undefined') return;
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('sidebar-collapsed')) {
        toggleSidebar();
    }
}
window.toggleSidebarIfCollapsed = toggleSidebarIfCollapsed;

function updateSidebarToggleIcons(isCollapsed) {
    if (typeof document === 'undefined') return;
    const sidebarBtn = document.getElementById('sidebar-toggle-btn');
    if (sidebarBtn) {
        sidebarBtn.setAttribute('title', isCollapsed ? 'Expandir barra lateral' : 'Recolher barra lateral');
        const icon = sidebarBtn.querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', isCollapsed ? 'panel-left-open' : 'panel-left-close');
        }
    }
    const brandInfo = document.querySelector('.brand-info');
    if (brandInfo) {
        brandInfo.setAttribute('title', isCollapsed ? 'Clique para expandir a barra lateral' : 'PrintCalc 3D');
    }
    if (typeof refreshIcons === 'function') {
        refreshIcons();
    }
}
window.updateSidebarToggleIcons = updateSidebarToggleIcons;

// ================= INITIALIZATION =================

window.addEventListener('DOMContentLoaded', async () => {
    initSidebarState();
    refreshIcons();
    setupDropzone();
    setupSummaryPanelStickyHeight();
    initSmoothScroll();

    const sidebar = typeof document.querySelector === 'function' ? document.getElementById('app-sidebar') : null;
    if (sidebar && typeof sidebar.addEventListener === 'function') {
        sidebar.addEventListener('transitionend', (e) => {
            if (e.propertyName === 'width' && typeof updateSummaryPanelHeight === 'function') {
                updateSummaryPanelHeight();
            }
        });
    }

    // Issue #27: Dynamic phone masking for commercial phones and WhatsApp
    attachPhoneMask(document.getElementById('proj-client-phone'));
    attachPhoneMask(document.getElementById('pref-phone'));

    // Issue #19: Close filament/printer modals with ESC key (WAI-ARIA dialog pattern)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
            closeFilamentModal();
            closePrinterModal();
        }
    });

    // Issue #19: Close modals when clicking on their backdrop (the outer container)
    document.getElementById('modal-filament')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeFilamentModal();
    });
    document.getElementById('modal-printer')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closePrinterModal();
    });

    function handleLogout() {
        if (confirm('Deseja realmente sair da sua conta? Certifique-se de ter salvo suas alterações.')) {
            API.auth.logout();
        }
    }
    window.handleLogout = handleLogout;

    window.addEventListener('auth:unauthorized', () => {
        clearUserData();
        document.getElementById('auth-modal')?.classList.remove('hidden');
    });

    window.addEventListener('auth:logout', () => {
        clearUserData();
        if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
            window.location.hash = '#/dashboard';
        }
        document.getElementById('auth-modal')?.classList.remove('hidden');
    });

    const token = API.getToken();
    if (token) {
        try {
            state.user = await API.auth.getMe();
            document.getElementById('auth-modal')?.classList.add('hidden');
            updateUserUI();
            await loadAllData();
            const route = getRouteFromHash();
            await applyRoute(route);
        } catch (err) {
            API.clearSession();
            clearUserData();
            document.getElementById('auth-modal')?.classList.remove('hidden');
        }
    } else {
        clearUserData();
        document.getElementById('auth-modal')?.classList.remove('hidden');
    }
});
