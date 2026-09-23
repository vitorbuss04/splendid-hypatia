/**
 * API Service with JWT Interceptor and Toast Notifications
 */

const API = {
    getToken() {
        return localStorage.getItem("auth_token");
    },

    setSession(token, user) {
        localStorage.setItem("auth_token", token);
        localStorage.setItem("user_profile", JSON.stringify(user));
    },

    getUser() {
        const str = localStorage.getItem("user_profile");
        return str ? JSON.parse(str) : null;
    },

    clearSession() {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user_profile");
    },

    async request(url, options = {}) {
        const token = this.getToken();
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        };

        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers,
        };

        try {
            const resp = await fetch(url, config);

            if (resp.status === 401) {
                this.clearSession();
                window.dispatchEvent(new CustomEvent("auth:unauthorized"));
                throw new Error("Sessão expirada. Faça login novamente.");
            }

            if (resp.status === 204) {
                return null;
            }

            const data = await resp.json().catch(() => null);

            if (!resp.ok) {
                const msg = data && data.detail ? data.detail : `Erro na requisição (${resp.status})`;
                throw new Error(msg);
            }

            return data;
        } catch (err) {
            console.error("API Error:", err);
            throw err;
        }
    },

    // Auth endpoints
    auth: {
        async register(email, password, full_name, company_name) {
            const res = await API.request("/api/auth/register", {
                method: "POST",
                body: JSON.stringify({ email, password, full_name, company_name }),
            });
            API.setSession(res.access_token, res.user);
            return res;
        },

        async login(email, password) {
            const res = await API.request("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });
            API.setSession(res.access_token, res.user);
            return res;
        },

        async getMe() {
            const user = await API.request("/api/auth/me");
            localStorage.setItem("user_profile", JSON.stringify(user));
            return user;
        },

        async updatePreferences(data) {
            const user = await API.request("/api/auth/preferences", {
                method: "PUT",
                body: JSON.stringify(data),
            });
            localStorage.setItem("user_profile", JSON.stringify(user));
            return user;
        },

        logout() {
            API.clearSession();
            window.dispatchEvent(new CustomEvent("auth:logout"));
        }
    },

    // Printers endpoints
    printers: {
        list: () => API.request("/api/printers"),
        get: (id) => API.request(`/api/printers/${id}`),
        create: (data) => API.request("/api/printers", { method: "POST", body: JSON.stringify(data) }),
        update: (id, data) => API.request(`/api/printers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
        delete: (id) => API.request(`/api/printers/${id}`, { method: "DELETE" }),
    },

    // Filaments endpoints
    filaments: {
        list: () => API.request("/api/filaments"),
        get: (id) => API.request(`/api/filaments/${id}`),
        create: (data) => API.request("/api/filaments", { method: "POST", body: JSON.stringify(data) }),
        update: (id, data) => API.request(`/api/filaments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
        delete: (id) => API.request(`/api/filaments/${id}`, { method: "DELETE" }),
    },

    // Projects endpoints
    projects: {
        list: () => API.request("/api/projects"),
        get: (id) => API.request(`/api/projects/${id}`),
        create: (data) => API.request("/api/projects", { method: "POST", body: JSON.stringify(data) }),
        update: (id, data) => API.request(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
        delete: (id) => API.request(`/api/projects/${id}`, { method: "DELETE" }),
        duplicate: (id) => API.request(`/api/projects/${id}/duplicate`, { method: "POST" }),
        getSummary: (id) => API.request(`/api/projects/${id}/summary`),
    },

    // Plates endpoints
    plates: {
        create: (projectId, data) => API.request(`/api/projects/${projectId}/plates`, { method: "POST", body: JSON.stringify(data) }),
        update: (projectId, plateId, data) => API.request(`/api/projects/${projectId}/plates/${plateId}`, { method: "PUT", body: JSON.stringify(data) }),
        delete: (projectId, plateId) => API.request(`/api/projects/${projectId}/plates/${plateId}`, { method: "DELETE" }),
    },

    // BOM items endpoints
    bom: {
        create: (projectId, data) => API.request(`/api/projects/${projectId}/bom`, { method: "POST", body: JSON.stringify(data) }),
        update: (projectId, bomId, data) => API.request(`/api/projects/${projectId}/bom/${bomId}`, { method: "PUT", body: JSON.stringify(data) }),
        delete: (projectId, bomId) => API.request(`/api/projects/${projectId}/bom/${bomId}`, { method: "DELETE" }),
    },

    // PDF Download Helper
    pdf: {
        async download(projectId, type = "client") {
            const token = API.getToken();
            const url = `/api/projects/${projectId}/pdf?type=${type}`;
            const res = await fetch(url, {
                headers: {
                    ...(token ? { "Authorization": `Bearer ${token}` } : {})
                }
            });

            if (!res.ok) {
                throw new Error("Erro ao gerar PDF.");
            }

            const blob = await res.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = downloadUrl;

            // Extract filename from header or fallback
            const disposition = res.headers.get("Content-Disposition");
            let filename = `orcamento_${projectId}.pdf`;
            if (disposition && disposition.includes("filename=")) {
                filename = disposition.split("filename=")[1].replace(/["']/g, "");
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();
        },

        preview(projectId, type = "client") {
            window.open(`/preview.html?project_id=${projectId}&type=${type}`, '_blank');
        }
    }
};
