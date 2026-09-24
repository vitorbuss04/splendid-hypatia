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
    toast.innerHTML = `<span>${message}</span>`;
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
        renderPrintersGrid();
    }
    if (viewName === 'filaments') {
        const inp = document.getElementById('filament-search-input');
        if (inp) inp.value = '';
        renderFilamentsGrid();
    }
    if (viewName === 'settings') populateSettingsForm();

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
    if (!state.user) return;
    const nameEl = document.getElementById('user-display-name');
    const compEl = document.getElementById('user-display-company');
    const avatarEl = document.getElementById('user-avatar');

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
        ? state.projects.filter(p => ['draft', 'quoted', 'in_production'].includes(p.status)).length 
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
            cb.net_profit || 0
        ] : [0, 0, 0, 0, 0];

        const hasCostData = cbValues.some(v => v > 0);

        if (!hasCostData) {
            costCanvas.classList.add('hidden');
            costEmpty.classList.remove('hidden');
        } else {
            costCanvas.classList.remove('hidden');
            costEmpty.classList.add('hidden');

            const cbLabels = ['Filamento', 'Máquina & Energia', 'Mão de Obra', 'Insumos BOM', 'Lucro Líquido'];
            const cbColors = ['#8b5cf6', '#3b82f6', '#f59e0b', '#64748b', '#10b981'];

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
                                <span class="font-semibold text-white group-hover:text-blue-400 transition-colors">${p.name}</span>
                            </div>
                        </td>
                        <td class="py-3 px-3 text-slate-300">
                            ${p.client_name ? `<span class="flex items-center gap-1.5"><i data-lucide="user" class="w-3 h-3 text-slate-500"></i>${p.client_name}</span>` : '<span class="text-slate-500">—</span>'}
                        </td>
                        <td class="py-3 px-3 text-center">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                ${p.plates_count} un
                            </span>
                        </td>
                        <td class="py-3 px-3 font-mono text-slate-300">${p.total_time_hours.toFixed(1)} h</td>
                        <td class="py-3 px-3 font-mono font-bold text-blue-400">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3 px-3 text-center">
                            <span class="badge-${p.status}">
                                ${formatStatus(p.status)}
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
                        ? (term ? `Nenhum projeto encontrado para "<strong class="text-white">${term}</strong>". Tente buscar por outros termos ou limpar os filtros.` : 'Não encontramos resultados para os filtros selecionados. Tente buscar por outros termos ou limpar os filtros.')
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

    // Render modern SaaS Dark Mode Table
    container.innerHTML = `
        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-800 bg-slate-900/70 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                    <th class="py-3 px-4">Projeto & Referência</th>
                    <th class="py-3 px-4">Cliente</th>
                    <th class="py-3 px-4 text-center">Placas</th>
                    <th class="py-3 px-4">Tempo Total</th>
                    <th class="py-3 px-4">Custo Base</th>
                    <th class="py-3 px-4">Preço de Venda</th>
                    <th class="py-3 px-4 text-center">Status</th>
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
                                    <p class="font-bold text-white group-hover:text-blue-400 transition-colors truncate">${p.name}</p>
                                    <p class="text-[10px] text-slate-500 font-mono">#${p.id.toString().padStart(4, '0')}</p>
                                </div>
                            </div>
                        </td>
                        <td class="py-3.5 px-4 text-slate-300">
                            ${p.client_name ? `
                                <div class="flex items-center gap-1.5">
                                    <i data-lucide="user" class="w-3.5 h-3.5 text-slate-500 shrink-0"></i>
                                    <span class="truncate">${p.client_name}</span>
                                </div>
                            ` : '<span class="text-slate-500">—</span>'}
                        </td>
                        <td class="py-3.5 px-4 text-center">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                ${p.plates_count} un
                            </span>
                        </td>
                        <td class="py-3.5 px-4 font-mono text-slate-300">${p.total_time_hours.toFixed(1)} h</td>
                        <td class="py-3.5 px-4 font-mono text-slate-400">${formatCurrency(p.base_cost)}</td>
                        <td class="py-3.5 px-4 font-mono font-bold text-blue-400 text-sm">${formatCurrency(p.final_price_to_client)}</td>
                        <td class="py-3.5 px-4 text-center">
                            <span class="badge-${p.status}">
                                ${formatStatus(p.status)}
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
    document.getElementById('proj-payment-terms').value = '';
    document.getElementById('proj-warranty-terms').value = '';
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
        document.getElementById('proj-client-phone').value = proj.client_phone || '';
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
        document.getElementById('proj-delivery-days').value = proj.delivery_days ?? 3;
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
    const cloned = JSON.parse(JSON.stringify(orig));
    cloned.name = `${orig.name} (Cópia)`;
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

// Global alias for compatibility
window.removePlate = removePlateRow;

function updatePlateTime(idx) {
    const hElem = document.getElementById(`plate-time-h-${idx}`);
    const mElem = document.getElementById(`plate-time-m-${idx}`);
    const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
    const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
    state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
    recalcLiveSummary();
}

function renderPlates() {
    const container = document.getElementById('plates-container');
    if (!container) return;

    container.innerHTML = state.currentPlates.map((plate, idx) => {
        const selFil = state.filaments.find(f => f.id === plate.filament_id);
        const totalMin = Math.round((plate.print_time_hours || 0) * 60);
        const timeH = Math.floor(totalMin / 60);
        const timeM = totalMin % 60;
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

                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <!-- Printer Selector -->
                    <div>
                        <label class="block text-[11px] font-medium text-slate-300 mb-1">Impressora</label>
                        <select onchange="updatePlatePrinter(${idx}, this.value)" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500">
                            <option value="">Personalizada (Manual)</option>
                            ${state.printers.map(p => `
                                <option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
                                    ${p.name} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
                                </option>
                            `).join('')}
                        </select>
                        ${!plate.printer_id ? `
                            <div class="mt-1.5 flex items-center gap-1.5 bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                                <span class="text-[10px] text-amber-400 font-medium">Taxa manual:</span>
                                <span class="text-[10px] text-slate-400">R$</span>
                                <input type="number" step="any" min="0" value="${plate.custom_printer_hourly_rate ?? 2.50}" oninput="state.currentPlates[${idx}].custom_printer_hourly_rate = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-20 px-1.5 py-0.5 bg-slate-900 border border-amber-500/40 rounded text-xs text-white font-medium focus:outline-none focus:border-amber-400 font-numeric" placeholder="2.50">
                                <span class="text-[10px] text-slate-400">/h</span>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Nozzle Diameter -->
                    <div>
                        <label class="block text-[11px] font-medium text-slate-300 mb-1">Diâmetro do Bico</label>
                        <select onchange="state.currentPlates[${idx}].nozzle_diameter = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 font-numeric">
                            <option value="0.4" ${nozzle === '0.4' ? 'selected' : ''}>0.4 mm (Padrão)</option>
                            <option value="0.2" ${nozzle === '0.2' ? 'selected' : ''}>0.2 mm (Alta Res.)</option>
                            <option value="0.6" ${nozzle === '0.6' ? 'selected' : ''}>0.6 mm (Rápido)</option>
                            <option value="0.8" ${nozzle === '0.8' ? 'selected' : ''}>0.8 mm (Industrial)</option>
                        </select>
                    </div>

                    <!-- Bed Surface Type -->
                    <div>
                        <label class="block text-[11px] font-medium text-slate-300 mb-1">Superfície da Mesa</label>
                        <select onchange="state.currentPlates[${idx}].bed_type = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500">
                            <option value="Textured PEI" ${bed === 'Textured PEI' ? 'selected' : ''}>PEI Texturizada</option>
                            <option value="Smooth PEI" ${bed === 'Smooth PEI' ? 'selected' : ''}>PEI Lisa</option>
                            <option value="Glass" ${bed === 'Glass' ? 'selected' : ''}>Vidro Borossilicato</option>
                            <option value="Engineering" ${bed === 'Engineering' ? 'selected' : ''}>Engenharia / Fixação</option>
                            <option value="Garolite" ${bed === 'Garolite' ? 'selected' : ''}>Garolite / G10 (Nylon)</option>
                        </select>
                    </div>

                    <!-- Filament Selector with Dynamic Dot -->
                    <div>
                        <label class="block text-[11px] font-medium text-slate-300 mb-1 flex items-center justify-between">
                            <span>Filamento</span>
                            ${selFil ? `<span class="flex items-center gap-1 text-[10px] text-slate-400 font-normal"><span class="w-2 h-2 rounded-full inline-block border border-slate-600 shadow-sm" style="background-color: ${selFil.color_hex || '#10b981'};"></span> ${selFil.material} ${selFil.color || ''}</span>` : ''}
                        </label>
                        <div class="relative flex items-center">
                            <span class="absolute left-2.5 w-3 h-3 rounded-full border border-white/20 pointer-events-none shadow-sm" style="background-color: ${selFil ? (selFil.color_hex || '#10b981') : '#64748b'};"></span>
                            <select onchange="updatePlateFilament(${idx}, this.value)" class="w-full pl-8 pr-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500">
                                <option value="">Personalizado (Manual)</option>
                                ${state.filaments.map(f => `
                                    <option value="${f.id}" ${plate.filament_id === f.id ? 'selected' : ''}>
                                        ${f.name} (R$ ${(Number(f.cost_per_gram) || 0).toFixed(2)}/g)
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        ${!plate.filament_id ? `
                            <div class="mt-1.5 flex items-center gap-1.5 bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                                <span class="text-[10px] text-amber-400 font-medium">Custo manual:</span>
                                <span class="text-[10px] text-slate-400">R$</span>
                                <input type="number" step="any" min="0" value="${plate.custom_filament_cost_per_g ?? 0.10}" oninput="state.currentPlates[${idx}].custom_filament_cost_per_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-20 px-1.5 py-0.5 bg-slate-900 border border-amber-500/40 rounded text-xs text-white font-medium focus:outline-none focus:border-amber-400 font-numeric" placeholder="0.10">
                                <span class="text-[10px] text-slate-400">/g</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>

            <!-- Group B: Slicer & Physical Parameters -->
            <div class="bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/60 space-y-3">
                <div class="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <i data-lucide="sliders" class="w-3.5 h-3.5 text-indigo-400"></i> Parâmetros do Fatiador & Físicos
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                    <!-- Print Time Dual Input (Hours & Minutes) -->
                    <div class="col-span-2 sm:col-span-2 lg:col-span-2">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Tempo (h : min)</label>
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

                    <!-- Layer Height -->
                    <div class="col-span-1">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Camada (mm)</label>
                        <select onchange="state.currentPlates[${idx}].layer_height = this.value" class="w-full px-2.5 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 font-numeric">
                            <option value="0.08" ${layer === '0.08' ? 'selected' : ''}>0.08 mm</option>
                            <option value="0.12" ${layer === '0.12' ? 'selected' : ''}>0.12 mm</option>
                            <option value="0.16" ${layer === '0.16' ? 'selected' : ''}>0.16 mm</option>
                            <option value="0.20" ${layer === '0.20' ? 'selected' : ''}>0.20 mm</option>
                            <option value="0.24" ${layer === '0.24' ? 'selected' : ''}>0.24 mm</option>
                            <option value="0.28" ${layer === '0.28' ? 'selected' : ''}>0.28 mm</option>
                        </select>
                    </div>

                    <!-- Part Weight -->
                    <div class="col-span-1">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Peso Peça (g)</label>
                        <input type="number" step="any" min="0" value="${plate.part_weight_g}" oninput="state.currentPlates[${idx}].part_weight_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="0">
                    </div>

                    <!-- Purge Weight -->
                    <div class="col-span-1">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Purga (g)</label>
                        <input type="number" step="any" min="0" value="${plate.purge_weight_g}" oninput="state.currentPlates[${idx}].purge_weight_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="0">
                    </div>

                    <!-- Failure Margin -->
                    <div class="col-span-1">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Falha (%)</label>
                        <input type="number" step="any" min="0" value="${plate.failure_margin_percent}" oninput="state.currentPlates[${idx}].failure_margin_percent = parseLocaleFloat(this.value, 0); recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" placeholder="10">
                    </div>

                    <!-- Quantity -->
                    <div class="col-span-1">
                        <label class="block text-[10px] font-medium text-slate-400 mb-1">Qtd Cópias</label>
                        <input type="number" step="1" min="1" value="${plate.quantity}" oninput="state.currentPlates[${idx}].quantity = parseInt(this.value, 10) || 1; recalcLiveSummary();" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-bold font-numeric text-center focus:outline-none focus:border-blue-500" placeholder="1">
                    </div>
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

// Casing aliases to ensure total runtime resilience
window.addNewBOMRow = addNewBomRow;
window.removeBOMRow = removeBomRow;

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
                <div class="col-span-4">Descrição do Componente</div>
                <div class="col-span-2">Categoria</div>
                <div class="col-span-2 text-center">Qtd</div>
                <div class="col-span-2 text-right">Custo Unit. (R$)</div>
                <div class="col-span-1 text-right">Subtotal</div>
                <div class="col-span-1 text-center">Ações</div>
            </div>
            <!-- Dynamic Insumo Rows -->
            ${state.currentBOM.map((item, idx) => `
                <div class="grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-3 p-3 bg-slate-900/70 hover:bg-slate-900/95 border border-slate-800/80 hover:border-slate-700 rounded-lg items-center text-xs transition-all shadow-sm">
                    <!-- Item Description -->
                    <div class="sm:col-span-4">
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

                    <!-- Quantity Input (min=1 step=1) -->
                    <div class="sm:col-span-2">
                        <label class="block sm:hidden text-[10px] text-slate-400 mb-1">Quantidade</label>
                        <input type="number" min="1" step="1" value="${item.quantity || 1}" oninput="state.currentBOM[${idx}].quantity = Math.max(1, parseInt(this.value, 10) || 1); recalcLiveSummary();" placeholder="Qtd" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-white text-xs text-center font-bold font-mono focus:outline-none focus:border-blue-500 transition-colors">
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

                    <!-- Delete Button Action -->
                    <div class="sm:col-span-1 flex justify-center items-center pt-1 sm:pt-0">
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
            costPerGram = parseLocaleFloat(plate.custom_filament_cost_per_g, 0);
        } else {
            costPerGram = 0.09; // fallback standard PLA
        }

        // Machine rate
        let machineHourlyRate = 0;
        if (printer) {
            machineHourlyRate = printer.machine_hourly_rate ?? 2.0;
        } else if (plate.custom_printer_hourly_rate != null) {
            machineHourlyRate = parseLocaleFloat(plate.custom_printer_hourly_rate, 0);
        } else {
            machineHourlyRate = 2.0; // fallback standard rate
        }

        const qty = plate.quantity || 1;
        const printTime = plate.print_time_hours || 0;
        const rawWeight = (plate.part_weight_g || 0) + (plate.purge_weight_g || 0);
        const failureFactor = 1.0 + ((plate.failure_margin_percent || 0) / 100);
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
            sumTextEl.textContent = `${qty}x • ${(printTime * qty).toFixed(1)}h • ${(rawWeight * qty).toFixed(1)}g (Mat: ${formatCurrency(unitMaterialCost * qty)} + Máq: ${formatCurrency(unitMachineCost * qty)})`;
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
    const cadHours = parseLocaleFloat(document.getElementById('proj-cad-hours')?.value, 0);
    const cadRate = parseLocaleFloat(document.getElementById('proj-cad-rate')?.value, 50);
    const cadCost = cadHours * cadRate;

    const postHours = parseLocaleFloat(document.getElementById('proj-post-hours')?.value, 0);
    const postRate = parseLocaleFloat(document.getElementById('proj-post-rate')?.value, 30);
    const postCost = postHours * postRate;

    const totalLaborCost = cadCost + postCost;

    // 4. Overhead & Base Cost
    const overheadCost = parseLocaleFloat(document.getElementById('proj-overhead')?.value, 0);
    const baseCost = totalPlatesCost + totalBOMCost + totalLaborCost + overheadCost;

    // 5. Pricing, Margins, Taxes
    const marginPercent = parseLocaleFloat(document.getElementById('proj-margin')?.value, 30);
    const taxPercent = Math.min(99, parseLocaleFloat(document.getElementById('proj-tax')?.value, 0));
    const discountPercent = Math.min(100, parseLocaleFloat(document.getElementById('proj-discount')?.value, 0));
    const shippingCost = parseLocaleFloat(document.getElementById('proj-shipping')?.value, 0);

    const taxDivisor = Math.max(0.01, 1.0 - (taxPercent / 100.0));
    const suggestedPrice = baseCost > 0 ? ((baseCost * (1.0 + (marginPercent / 100.0))) / taxDivisor) : 0;

    const discountAmount = suggestedPrice * (discountPercent / 100.0);
    const subtotalAfterDiscount = suggestedPrice - discountAmount;
    const taxAmount = subtotalAfterDiscount * (taxPercent / 100.0);
    const netRevenue = subtotalAfterDiscount - taxAmount;
    const netProfit = netRevenue - baseCost;
    const effectiveMarginPercent = baseCost > 0 ? (netProfit / baseCost * 100.0) : 0;
    const finalPriceToClient = subtotalAfterDiscount + shippingCost;

    // Update Live Summary DOM
    setText('live-weight', `${totalWeightGrams.toFixed(1)} g`);
    setText('live-time', `${totalTimeHours.toFixed(1)} h`);
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

    const payload = {
        name,
        client_name: document.getElementById('proj-client-name').value.trim(),
        client_email: document.getElementById('proj-client-email').value.trim(),
        client_phone: document.getElementById('proj-client-phone').value.trim(),
        status: document.getElementById('proj-status').value,
        cad_hours: parseLocaleFloat(document.getElementById('proj-cad-hours').value, 0),
        cad_hourly_rate: parseLocaleFloat(document.getElementById('proj-cad-rate').value, 0),
        post_process_hours: parseLocaleFloat(document.getElementById('proj-post-hours').value, 0),
        post_process_hourly_rate: parseLocaleFloat(document.getElementById('proj-post-rate').value, 0),
        overhead_cost: parseLocaleFloat(document.getElementById('proj-overhead').value, 0),
        profit_margin_percent: parseLocaleFloat(document.getElementById('proj-margin').value, 0),
        tax_rate_percent: parseLocaleFloat(document.getElementById('proj-tax').value, 0),
        discount_percent: parseLocaleFloat(document.getElementById('proj-discount').value, 0),
        shipping_cost: parseLocaleFloat(document.getElementById('proj-shipping').value, 0),
        delivery_days: (() => { const d = parseInt(document.getElementById('proj-delivery-days')?.value, 10); return isNaN(d) ? 3 : d; })(),
        payment_terms: document.getElementById('proj-payment-terms')?.value.trim() || null,
        warranty_terms: document.getElementById('proj-warranty-terms')?.value.trim() || null,
        notes: document.getElementById('proj-notes').value.trim(),
        plates: state.currentPlates.map(p => ({
            name: p.name,
            printer_id: p.printer_id,
            filament_id: p.filament_id,
            custom_printer_hourly_rate: p.printer_id ? null : (p.custom_printer_hourly_rate != null ? parseLocaleFloat(p.custom_printer_hourly_rate, 2.50) : 2.50),
            custom_filament_cost_per_g: p.filament_id ? null : (p.custom_filament_cost_per_g != null ? parseLocaleFloat(p.custom_filament_cost_per_g, 0.10) : 0.10),
            print_time_hours: parseLocaleFloat(p.print_time_hours, 0),
            part_weight_g: parseLocaleFloat(p.part_weight_g, 0),
            purge_weight_g: parseLocaleFloat(p.purge_weight_g, 0),
            failure_margin_percent: parseLocaleFloat(p.failure_margin_percent, 0),
            quantity: parseInt(p.quantity, 10) || 1,
            notes: p.notes,
        })),
        bom_items: state.currentBOM.map(b => ({
            name: b.name,
            category: b.category,
            quantity: parseInt(b.quantity, 10) || 1,
            unit_cost: parseLocaleFloat(b.unit_cost, 0),
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
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteProject(id) {
    if (!confirm('Deseja realmente excluir este orçamento?')) return;
    try {
        await API.projects.delete(id);
        showToast('Projeto excluído com sucesso.', 'success');
        await loadAllData();
        renderProjectsTable();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ================= FILE IMPORT HANDLERS (HYBRID 3MF / G-CODE) =================

function setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-slicer-input');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleSlicerFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSlicerFile(e.target.files[0]);
            // Reset so same file can be re-selected (issue #20)
            e.target.value = '';
        }
    });
}

async function handleSlicerFile(file) {
    const name = file.name.toLowerCase();
    showToast(`Processando metadados de ${file.name}...`, 'info');

    try {
        if (name.endsWith('.3mf') || name.endsWith('.gcode.3mf')) {
            const extractedPlates = await parse3mfMetadata(file);
            if (extractedPlates && extractedPlates.length > 0) {
                const defaultPrinter = state.printers[0] || null;

                extractedPlates.forEach(p => {
                    if (defaultPrinter) {
                        p.printer_id = defaultPrinter.id;
                        p.custom_printer_hourly_rate = null;
                    } else {
                        p.printer_id = null;
                        p.custom_printer_hourly_rate = 2.50;
                    }

                    let matchedFilament = null;
                    if (p.filament_type && state.filaments.length > 0) {
                        const types = p.filament_type.toLowerCase().split(',').map(s => s.trim());
                        matchedFilament = state.filaments.find(f => types.includes(f.material.toLowerCase()));
                    }
                    if (!matchedFilament && state.filaments.length > 0) {
                        matchedFilament = state.filaments[0];
                    }

                    if (matchedFilament) {
                        p.filament_id = matchedFilament.id;
                        p.custom_filament_cost_per_g = null;
                    } else {
                        p.filament_id = null;
                        p.custom_filament_cost_per_g = 0.10;
                    }

                    p.failure_margin_percent = (state.user?.default_failure_rate ?? 10);
                    p.quantity = p.quantity || 1;
                    p.notes = p.notes || '';
                });

                // If only 1 empty plate exists, replace it, else append
                if (state.currentPlates.length === 1 && state.currentPlates[0].print_time_hours === 0 && state.currentPlates[0].part_weight_g === 0) {
                    state.currentPlates = extractedPlates;
                } else {
                    state.currentPlates = [...state.currentPlates, ...extractedPlates];
                }
                const fileTypeLabel = name.endsWith('.gcode.3mf') ? '.gcode.3mf' : '3MF';
                showToast(`Arquivo ${fileTypeLabel} lido! ${extractedPlates.length} placa(s) adicionada(s).`, 'success');
            }
        } else if (name.endsWith('.gcode')) {
            const text = await file.text();
            const meta = parseGcodeMetadata(text);
            const newPlate = createDefaultPlate(state.currentPlates.length + 1);
            newPlate.name = file.name.replace(/\.(?:gcode\.3mf|3mf|gcode)$/i, '');
            newPlate.print_time_hours = meta.print_time_hours;
            newPlate.part_weight_g = meta.part_weight_g;

            if (meta.filament_type && state.filaments.length > 0) {
                const matched = state.filaments.find(f => f.material.toLowerCase() === meta.filament_type.toLowerCase());
                if (matched) {
                    newPlate.filament_id = matched.id;
                    newPlate.custom_filament_cost_per_g = null;
                }
            }

            if (state.currentPlates.length === 1 && state.currentPlates[0].print_time_hours === 0 && state.currentPlates[0].part_weight_g === 0) {
                state.currentPlates = [newPlate];
            } else {
                state.currentPlates.push(newPlate);
            }
            showToast(`G-Code lido com sucesso (${meta.print_time_hours}h, ${meta.part_weight_g}g)!`, 'success');
        } else {
            showToast('Formato não suportado. Utilize arquivos .3mf, .gcode ou .gcode.3mf.', 'error');
            return;
        }

        renderPlates();
        recalcLiveSummary();
    } catch (err) {
        showToast(`Erro ao ler arquivo: ${err.message}`, 'error');
    }
}

async function handleSinglePlateFile(e, plateIdx) {
    const file = e.target.files[0];
    // Reset input value so re-selecting the same file triggers 'change' again (issue #20)
    if (e.target) e.target.value = '';
    if (!file) return;

    try {
        const name = file.name.toLowerCase();
        if (name.endsWith('.3mf') || name.endsWith('.gcode.3mf')) {
            const plates = await parse3mfMetadata(file);
            if (plates.length > 0) {
                state.currentPlates[plateIdx].print_time_hours = plates[0].print_time_hours;
                state.currentPlates[plateIdx].part_weight_g = plates[0].part_weight_g;
                state.currentPlates[plateIdx].purge_weight_g = plates[0].purge_weight_g;

                if (plates[0].filament_type && state.filaments.length > 0) {
                    const types = plates[0].filament_type.toLowerCase().split(',').map(s => s.trim());
                    const matched = state.filaments.find(f => types.includes(f.material.toLowerCase()));
                    if (matched) {
                        state.currentPlates[plateIdx].filament_id = matched.id;
                        state.currentPlates[plateIdx].custom_filament_cost_per_g = null;
                    }
                }

                const fileTypeLabel = name.endsWith('.gcode.3mf') ? '.gcode.3mf' : '3MF';
                showToast(`Placa atualizada com dados do ${fileTypeLabel}!`, 'success');
            }
        } else if (name.endsWith('.gcode')) {
            const text = await file.text();
            const meta = parseGcodeMetadata(text);
            state.currentPlates[plateIdx].print_time_hours = meta.print_time_hours;
            state.currentPlates[plateIdx].part_weight_g = meta.part_weight_g;

            if (meta.filament_type && state.filaments.length > 0) {
                const matched = state.filaments.find(f => f.material.toLowerCase() === meta.filament_type.toLowerCase());
                if (matched) {
                    state.currentPlates[plateIdx].filament_id = matched.id;
                    state.currentPlates[plateIdx].custom_filament_cost_per_g = null;
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
    }
    refreshIcons();
}

function closePrinterModal() {
    document.getElementById('modal-printer').classList.add('hidden');
}

async function handleSavePrinter(e) {
    e.preventDefault();
    normalizeNumericInputs();
    const id = document.getElementById('printer-id').value;
    const payload = {
        name: document.getElementById('printer-name').value.trim(),
        model: document.getElementById('printer-model').value.trim(),
        acquisition_cost: parseLocaleFloat(document.getElementById('printer-cost').value, 0),
        lifespan_hours: parseLocaleFloat(document.getElementById('printer-lifespan').value, 5000),
        avg_power_watts: parseLocaleFloat(document.getElementById('printer-power').value, 150),
        maintenance_cost_per_hour: parseLocaleFloat(document.getElementById('printer-maintenance').value, 1.0),
        energy_rate_kwh: parseLocaleFloat(document.getElementById('printer-energy').value, 0.85),
    };

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

// Issue #22: Real-time search/filter for printers grid
function filterPrinters() {
    const term = (document.getElementById('printer-search-input')?.value || '').trim();
    renderPrintersGrid(term);
}

function renderPrintersGrid(filterTerm = null) {
    const grid = document.getElementById('printers-grid');
    if (!grid) return;

    const term = (filterTerm !== null && filterTerm !== undefined ? filterTerm : (document.getElementById('printer-search-input')?.value || '')).trim();
    const printers = term
        ? state.printers.filter(p =>
            matchesSearch(`${p.name || ''} ${p.model || ''}`, term)
          )
        : state.printers;

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

    if (printers.length === 0 && term) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-8 text-center text-slate-400">
                <i data-lucide="search-x" class="w-10 h-10 mx-auto mb-3 text-slate-600"></i>
                <p class="text-sm">Nenhuma impressora encontrada para "<strong class="text-white">${term}</strong>".</p>
                <button type="button" onclick="const inp = document.getElementById('printer-search-input'); if(inp){inp.value='';} filterPrinters();" class="mt-3 inline-block px-3 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 rounded text-xs font-medium transition-colors">
                    Limpar filtro
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
                            <h4 class="font-bold text-white text-base">${p.name}</h4>
                            <p class="text-xs text-slate-400">${p.model || 'FDM'}</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="editPrinter(${p.id})" class="p-1 text-slate-400 hover:text-white transition-colors" title="Editar">
                                <i data-lucide="edit-2" class="w-4 h-4"></i>
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
        document.getElementById('filament-weight').value = filament.spool_weight_g;
        document.getElementById('filament-price').value = filament.spool_price;
        if (colorInput) colorInput.placeholder = 'Ex: Preto';
    } else if (filament && isDuplicate) {
        title.textContent = 'Cadastrar Filamento (Duplicar)';
        document.getElementById('filament-id').value = '';
        document.getElementById('filament-material').value = filament.material || 'PLA';
        document.getElementById('filament-brand').value = filament.brand || '';
        document.getElementById('filament-color').value = '';
        document.getElementById('filament-color-hex').value = filament.color_hex || '#10b981';
        document.getElementById('filament-weight').value = filament.spool_weight_g;
        document.getElementById('filament-price').value = filament.spool_price;
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
        document.getElementById('filament-weight').value = '1000';
        document.getElementById('filament-price').value = '95.00';
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

    const payload = {
        name: standardName,
        brand: brand,
        material: mat,
        color: color,
        color_hex: colorHex,
        spool_weight_g: parseLocaleFloat(document.getElementById('filament-weight').value, 1000),
        spool_price: parseLocaleFloat(document.getElementById('filament-price').value, 90),
    };

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

// Issue #22: Real-time search/filter for filaments grid
function filterFilaments() {
    const term = (document.getElementById('filament-search-input')?.value || '').trim();
    renderFilamentsGrid(term);
}

function renderFilamentsGrid(filterTerm = null) {
    const grid = document.getElementById('filaments-grid');
    if (!grid) return;

    const term = (filterTerm !== null && filterTerm !== undefined ? filterTerm : (document.getElementById('filament-search-input')?.value || '')).trim();
    const filaments = term
        ? state.filaments.filter(f =>
            matchesSearch(`${f.name || ''} ${f.brand || ''} ${f.material || ''} ${f.color || ''}`, term)
          )
        : state.filaments;

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

    if (filaments.length === 0 && term) {
        grid.innerHTML = `
            <div class="col-span-full card-dark p-8 text-center text-slate-400">
                <i data-lucide="search-x" class="w-10 h-10 mx-auto mb-3 text-slate-600"></i>
                <p class="text-sm">Nenhum filamento encontrado para "<strong class="text-white">${term}</strong>".</p>
                <button type="button" onclick="const inp = document.getElementById('filament-search-input'); if(inp){inp.value='';} filterFilaments();" class="mt-3 inline-block px-3 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 rounded text-xs font-medium transition-colors">
                    Limpar filtro
                </button>
            </div>
        `;
        refreshIcons();
        return;
    }

    grid.innerHTML = filaments.map(f => {
        const matLower = (f.material || 'other').toLowerCase();
        return `
            <div class="card-dark p-6 space-y-4 hover:border-slate-600 transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl border border-slate-700/60 flex items-center justify-center relative shadow-sm" style="background-color: ${f.color_hex || '#10b981'}22;">
                                <span class="w-4 h-4 rounded-full border border-white/30 shadow-sm" style="background-color: ${f.color_hex || '#10b981'};"></span>
                            </div>
                            <div>
                                <div class="flex items-center gap-2">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider badge-mat-${matLower}">
                                        ${f.material}
                                    </span>
                                    <h4 class="font-bold text-white text-sm">${f.name}</h4>
                                </div>
                                <p class="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                                    <span class="inline-block w-2.5 h-2.5 rounded-full border border-white/20 shadow-sm" style="background-color: ${f.color_hex || '#10b981'};"></span>
                                    <span>${f.brand || 'Genérico'} • ${f.color || 'Cor padrão'}</span>
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
                        <div class="text-2xl font-black text-emerald-400 mt-0.5">
                            R$ ${f.cost_per_gram.toFixed(2)}<span class="text-xs font-normal text-slate-400">/g</span>
                        </div>
                    </div>
                </div>

                <div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
                    <span>Carretel: ${f.spool_weight_g} g</span>
                    <span>Preço: ${formatCurrency(f.spool_price)}</span>
                </div>
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
    document.getElementById('pref-phone').value = u.phone || '';
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
    const payload = {
        company_name: document.getElementById('pref-company').value.trim(),
        full_name: document.getElementById('pref-fullname').value.trim(),
        phone: document.getElementById('pref-phone').value.trim(),
        pix_key: document.getElementById('pref-pix').value.trim(),
        default_energy_rate: parseLocaleFloat(document.getElementById('pref-energy').value, 0.85),
        default_profit_margin: parseLocaleFloat(document.getElementById('pref-margin').value, 30),
        default_tax_rate: parseLocaleFloat(document.getElementById('pref-tax').value, 6),
        default_failure_rate: parseLocaleFloat(document.getElementById('pref-failure').value, 10),
        default_cad_rate: parseLocaleFloat(document.getElementById('pref-cad-rate').value, 50),
        default_post_rate: parseLocaleFloat(document.getElementById('pref-post-rate').value, 30),
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

// ================= INITIALIZATION =================

window.addEventListener('DOMContentLoaded', async () => {
    refreshIcons();
    setupDropzone();

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

    window.addEventListener('auth:unauthorized', () => {
        document.getElementById('auth-modal').classList.remove('hidden');
    });

    window.addEventListener('auth:logout', () => {
        state.user = null;
        if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
            window.location.hash = '#/dashboard';
        }
        document.getElementById('auth-modal').classList.remove('hidden');
    });

    const token = API.getToken();
    if (token) {
        try {
            state.user = await API.auth.getMe();
            document.getElementById('auth-modal').classList.add('hidden');
            updateUserUI();
            await loadAllData();
            const route = getRouteFromHash();
            await applyRoute(route);
        } catch (err) {
            API.clearSession();
            document.getElementById('auth-modal').classList.remove('hidden');
        }
    } else {
        document.getElementById('auth-modal').classList.remove('hidden');
    }
});
