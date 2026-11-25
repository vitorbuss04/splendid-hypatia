import '@material/web/labs/navigationdrawer/navigation-drawer.js';

const DESKTOP_MEDIA_QUERY = '(min-width: 1100px)';
const DESKTOP_OPEN_STORAGE_KEY = 'm3_desktop_drawer_open';

let cachedController = null;

/**
 * Configures the navigation drawer responsively across all Material 3 pages:
 * - >= 1100px: side-by-side <md-navigation-drawer> expanding sideways without overlap
 *   or scrim, hiding the mobile close ('X') button and persisting toggle state.
 * - < 1100px: modal <md-navigation-drawer-modal> overlapping content with scrim,
 *   closing via the 'X' button, scrim click, or Escape key.
 */
export function initResponsiveDrawer() {
    if (cachedController) return cachedController;

    const modalDrawer = document.getElementById('nav-drawer');
    const drawerContent = modalDrawer?.querySelector('.drawer-content');
    if (!modalDrawer || !drawerContent) {
        return () => {};
    }

    const desktopMedia = window.matchMedia(DESKTOP_MEDIA_QUERY);
    document.body.classList.add('has-responsive-drawer');

    let desktopDrawer = document.getElementById('nav-drawer-desktop');
    if (!desktopDrawer) {
        desktopDrawer = document.createElement('md-navigation-drawer');
        desktopDrawer.id = 'nav-drawer-desktop';
        desktopDrawer.setAttribute('pivot', 'start');
        desktopDrawer.setAttribute(
            'aria-label',
            modalDrawer.getAttribute('aria-label') || 'Menu de Navegação Principal',
        );
        modalDrawer.parentNode.insertBefore(desktopDrawer, modalDrawer);
    }

    const getSavedDesktopOpen = () => {
        try {
            return localStorage.getItem(DESKTOP_OPEN_STORAGE_KEY) !== 'false';
        } catch {
            return true;
        }
    };

    const setSavedDesktopOpen = (open) => {
        try {
            localStorage.setItem(DESKTOP_OPEN_STORAGE_KEY, open ? 'true' : 'false');
        } catch {
            // Ignore storage errors in restricted contexts
        }
    };

    const syncDrawerHost = () => {
        if (desktopMedia.matches) {
            if (drawerContent.parentElement !== desktopDrawer) {
                desktopDrawer.appendChild(drawerContent);
            }
            modalDrawer.opened = false;
            modalDrawer.classList.remove('is-open');

            const shouldBeOpen = getSavedDesktopOpen();
            desktopDrawer.opened = shouldBeOpen;
            desktopDrawer.classList.toggle('is-open', shouldBeOpen);
        } else {
            if (drawerContent.parentElement !== modalDrawer) {
                modalDrawer.appendChild(drawerContent);
            }
            desktopDrawer.opened = false;
            desktopDrawer.classList.remove('is-open');

            modalDrawer.opened = false;
            modalDrawer.classList.remove('is-open');
        }
    };

    const setDrawerOpen = (open, { desktop = false, persist = false } = {}) => {
        const next = Boolean(open);
        if (desktopMedia.matches) {
            if (!desktop) return;
            desktopDrawer.opened = next;
            desktopDrawer.classList.toggle('is-open', next);
            if (persist) setSavedDesktopOpen(next);
            return;
        }
        modalDrawer.opened = next;
        modalDrawer.classList.toggle('is-open', next);
    };

    document.getElementById('drawer-open-btn')?.addEventListener('click', () => {
        const currentlyOpen = desktopMedia.matches ? desktopDrawer.opened : modalDrawer.opened;
        setDrawerOpen(!currentlyOpen, { desktop: true, persist: true });
    });

    document.getElementById('drawer-close-btn')?.addEventListener('click', () => {
        if (!desktopMedia.matches) {
            setDrawerOpen(false);
        }
    });

    modalDrawer.addEventListener('navigation-drawer-changed', (e) => {
        modalDrawer.classList.toggle('is-open', Boolean(e.detail?.opened));
    });

    desktopDrawer.addEventListener('navigation-drawer-changed', (e) => {
        desktopDrawer.classList.toggle('is-open', Boolean(e.detail?.opened));
    });

    const syncDrawerBrand = (user = null) => {
        const titleEl = document.getElementById('drawer-company-title');
        if (!titleEl) return;
        let profile = user;
        if (!profile) {
            try {
                profile = JSON.parse(localStorage.getItem('user_profile') || 'null');
            } catch {
                profile = null;
            }
        }
        const companyName = String(profile?.company_name || '').trim();
        titleEl.textContent = companyName || '3D Print Calc Pro';
    };

    desktopMedia.addEventListener('change', syncDrawerHost);
    window.addEventListener('m3:user-synced', (e) => syncDrawerBrand(e.detail));
    window.addEventListener('auth:logout', () => {
        const titleEl = document.getElementById('drawer-company-title');
        if (titleEl) titleEl.textContent = '3D Print Calc Pro';
    });
    syncDrawerHost();
    syncDrawerBrand();

    cachedController = setDrawerOpen;
    return cachedController;
}
