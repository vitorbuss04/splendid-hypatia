const UI_READY_ELEMENTS = [
    'md-circular-progress',
    'md-filled-card',
    'md-elevated-card',
    'md-outlined-card',
    'md-filled-button',
    'md-outlined-text-field',
    'md-navigation-drawer',
    'md-navigation-drawer-modal',
];

let pendingLoads = 0;
let initialBootDone = false;

/**
 * Waits for critical @material/web components (with bounded timeout fallback).
 */
export async function waitForUiReady(timeoutMs = 2500) {
    const defs = UI_READY_ELEMENTS.map(tag =>
        customElements.get(tag)
            ? Promise.resolve()
            : customElements.whenDefined(tag),
    );
    const fontsReady = document.fonts?.ready || Promise.resolve();
    const timeout = new Promise(resolve => setTimeout(resolve, timeoutMs));
    await Promise.race([Promise.all([...defs, fontsReady]), timeout]);
}

function updateBodyLoadingClass() {
    const active = !initialBootDone || pendingLoads > 0;
    document.body.classList.toggle('m3-page-loading', active);
}

/**
 * Shows the fullscreen M3 circular loading overlay and hides page content
 * until every concurrent load completes (and UI elements are upgraded).
 * Returns a release function safe to call in a finally block.
 */
export function startPageLoading() {
    pendingLoads += 1;
    updateBodyLoadingClass();

    let released = false;
    return () => {
        if (released) return;
        released = true;
        pendingLoads = Math.max(0, pendingLoads - 1);
        if (pendingLoads === 0 && initialBootDone) {
            requestAnimationFrame(() => updateBodyLoadingClass());
        }
    };
}

/**
 * Completes the initial UI boot phase once custom elements and theme are ready.
 */
export async function markUiReady() {
    await waitForUiReady();
    initialBootDone = true;
    requestAnimationFrame(() => updateBodyLoadingClass());
}

/**
 * Clears any stuck loading overlay (for example on unauthenticated 401 redirect).
 */
export function clearPageLoading() {
    pendingLoads = 0;
    initialBootDone = true;
    updateBodyLoadingClass();
}
