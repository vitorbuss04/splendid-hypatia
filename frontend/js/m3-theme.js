import {
    argbFromHex,
    themeFromSourceColor,
    applyTheme,
    hexFromArgb,
} from '@material/material-color-utilities';

export const DEFAULT_THEME_MODE = 'system';
export const DEFAULT_THEME_SEED = '#2563EB';
export const THEME_PRESETS = [
    { seed: '#6750A4', label: 'M3 Purple' },
    { seed: '#2563EB', label: 'Royal Cobalt' },
    { seed: '#006874', label: 'Ocean Teal' },
    { seed: '#006D3B', label: 'Emerald' },
    { seed: '#B3261E', label: 'Crimson' },
];

const CACHE_KEY_PREFIX = 'm3_theme_prefs_u_';
const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');

let currentThemeMode = DEFAULT_THEME_MODE;
let currentSeedColor = DEFAULT_THEME_SEED;
let activeUserId = null;
let initialized = false;
let onAppliedHandler = null;
let onNotifyHandler = null;

export function normalizeThemeMode(mode) {
    return mode === 'light' || mode === 'dark' || mode === 'system'
        ? mode
        : DEFAULT_THEME_MODE;
}

export function normalizeSeedColor(hex) {
    const clean = String(hex || '').trim().toUpperCase();
    return /^#[0-9A-F]{6}$/.test(clean) ? clean : DEFAULT_THEME_SEED;
}

export function resolveIsDark(mode) {
    if (mode === 'dark') return true;
    if (mode === 'light') return false;
    return colorSchemeQuery.matches;
}

function getApiClient() {
    try {
        if (typeof API !== 'undefined') return API;
    } catch {
        // Fallback below
    }
    return globalThis.API || null;
}

function getAuthToken() {
    try {
        return getApiClient()?.getToken?.() || localStorage.getItem('auth_token');
    } catch {
        return null;
    }
}

function getActiveUserIdFromStorage() {
    try {
        const cachedProfile = getApiClient()?.getUser?.() || JSON.parse(localStorage.getItem('user_profile') || 'null');
        if (cachedProfile?.id != null) return String(cachedProfile.id);
    } catch {
        // Fallback to JWT decode
    }

    try {
        const token = getAuthToken();
        if (!token) return null;
        const parts = token.split('.');
        if (parts.length < 2) return null;
        const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(base64));
        return payload?.sub != null ? String(payload.sub) : null;
    } catch {
        return null;
    }
}

function readCachedUserPrefs(userId) {
    if (!userId) return null;
    try {
        const raw = localStorage.getItem(`${CACHE_KEY_PREFIX}${userId}`);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return {
            themeMode: normalizeThemeMode(parsed.theme_mode),
            seedColor: normalizeSeedColor(parsed.theme_seed_color),
        };
    } catch {
        return null;
    }
}

function writeCachedUserPrefs(userId, themeMode, seedColor) {
    if (!userId) return;
    try {
        localStorage.setItem(
            `${CACHE_KEY_PREFIX}${userId}`,
            JSON.stringify({
                theme_mode: normalizeThemeMode(themeMode),
                theme_seed_color: normalizeSeedColor(seedColor),
            }),
        );
    } catch {
        // Ignore storage quota / privacy errors
    }
}

export function getThemeState() {
    return {
        themeMode: currentThemeMode,
        seedColor: currentSeedColor,
        isDark: resolveIsDark(currentThemeMode),
        userId: activeUserId,
    };
}

export function applyThemeState({
    themeMode,
    seedColor,
    persistLocal = false,
    userId,
} = {}) {
    currentThemeMode = normalizeThemeMode(themeMode ?? currentThemeMode);
    currentSeedColor = normalizeSeedColor(seedColor ?? currentSeedColor);
    if (userId !== undefined) {
        activeUserId = userId != null ? String(userId) : null;
    }

    const dark = resolveIsDark(currentThemeMode);
    const theme = themeFromSourceColor(argbFromHex(currentSeedColor));
    const root = document.documentElement;
    applyTheme(theme, { target: root, dark });

    const neutral = theme.palettes.neutral;
    const tones = dark
        ? {
            'surface-dim': 6,
            'surface-bright': 24,
            'surface-container-lowest': 4,
            'surface-container-low': 10,
            'surface-container': 12,
            'surface-container-high': 17,
            'surface-container-highest': 22,
        }
        : {
            'surface-dim': 87,
            'surface-bright': 98,
            'surface-container-lowest': 100,
            'surface-container-low': 96,
            'surface-container': 94,
            'surface-container-high': 92,
            'surface-container-highest': 90,
        };

    for (const [token, toneVal] of Object.entries(tones)) {
        root.style.setProperty(`--md-sys-color-${token}`, hexFromArgb(neutral.tone(toneVal)));
    }

    const surfaceHex = hexFromArgb(neutral.tone(dark ? 6 : 98));
    root.style.setProperty('--md-sys-color-surface', surfaceHex);
    root.style.setProperty('--md-sys-color-background', surfaceHex);

    root.dataset.theme = dark ? 'dark' : 'light';
    root.style.colorScheme = dark ? 'dark' : 'light';

    const themeBtn = document.getElementById('theme-mode-toggle');
    if (themeBtn) themeBtn.selected = dark;

    document.querySelectorAll('.seed-btn').forEach(btn => {
        btn.setAttribute(
            'aria-pressed',
            btn.dataset.seed?.toUpperCase() === currentSeedColor ? 'true' : 'false',
        );
    });

    const colorPicker = document.getElementById('pref-theme-color-picker');
    if (colorPicker && colorPicker.value.toUpperCase() !== currentSeedColor) {
        colorPicker.value = currentSeedColor.toLowerCase();
    }

    const colorHexLabel = document.getElementById('pref-theme-color-hex');
    if (colorHexLabel) colorHexLabel.textContent = currentSeedColor;

    document.querySelectorAll('#pref-theme-mode-chips md-filter-chip').forEach(chip => {
        chip.selected = chip.getAttribute('data-theme-mode') === currentThemeMode;
    });

    if (persistLocal) {
        const targetUid = activeUserId ?? getActiveUserIdFromStorage();
        if (targetUid) {
            writeCachedUserPrefs(targetUid, currentThemeMode, currentSeedColor);
        }
    }

    onAppliedHandler?.(getThemeState());
    return getThemeState();
}

export function syncThemeFromUser(user) {
    if (!user || user.id == null) return getThemeState();
    window.dispatchEvent(new CustomEvent('m3:user-synced', { detail: user }));
    return applyThemeState({
        themeMode: user.theme_mode || DEFAULT_THEME_MODE,
        seedColor: user.theme_seed_color || DEFAULT_THEME_SEED,
        persistLocal: true,
        userId: user.id,
    });
}

export async function saveUserThemePreferences({ themeMode, seedColor } = {}) {
    const nextState = applyThemeState({
        themeMode,
        seedColor,
        persistLocal: true,
    });

    const token = getAuthToken();
    if (!token) {
        return { state: nextState, savedToServer: false };
    }

    const bodyPayload = {
        theme_mode: nextState.themeMode,
        theme_seed_color: nextState.seedColor,
    };

    const apiClient = getApiClient();
    let updated = null;
    if (apiClient?.auth?.updatePreferences) {
        updated = await apiClient.auth.updatePreferences(bodyPayload);
    } else {
        const resp = await fetch('/api/auth/preferences', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(bodyPayload),
        });
        if (!resp.ok) {
            throw new Error(`Erro ao salvar aparência (${resp.status})`);
        }
        updated = await resp.json();
        try {
            localStorage.setItem('user_profile', JSON.stringify(updated));
        } catch {
            // Ignore storage errors
        }
    }

    syncThemeFromUser(updated);
    return { state: getThemeState(), user: updated, savedToServer: true };
}

export function initThemeController({ onApplied, onNotify } = {}) {
    onAppliedHandler = onApplied || onAppliedHandler;
    onNotifyHandler = onNotify || onNotifyHandler;

    if (!initialized) {
        initialized = true;

        const initialUid = getActiveUserIdFromStorage();
        const cached = readCachedUserPrefs(initialUid);
        applyThemeState({
            themeMode: cached?.themeMode ?? DEFAULT_THEME_MODE,
            seedColor: cached?.seedColor ?? DEFAULT_THEME_SEED,
            userId: initialUid,
        });

        colorSchemeQuery.addEventListener('change', () => {
            if (currentThemeMode === 'system') {
                applyThemeState({ themeMode: 'system' });
            }
        });

        document.getElementById('theme-mode-toggle')?.addEventListener('change', async (e) => {
            const nextMode = e.target.selected ? 'dark' : 'light';
            try {
                await saveUserThemePreferences({ themeMode: nextMode });
                onNotifyHandler?.(
                    nextMode === 'dark' ? 'Tema Escuro (M3 Dark) ativado' : 'Tema Claro (M3 Light) ativado',
                    nextMode === 'dark' ? 'dark_mode' : 'light_mode',
                );
            } catch (err) {
                onNotifyHandler?.(err?.message || 'Erro ao salvar tema.', 'error');
            }
        });

        window.addEventListener('auth:logout', () => {
            applyThemeState({
                themeMode: DEFAULT_THEME_MODE,
                seedColor: DEFAULT_THEME_SEED,
                persistLocal: false,
                userId: null,
            });
        });
    } else {
        onAppliedHandler?.(getThemeState());
    }

    return getThemeState();
}
