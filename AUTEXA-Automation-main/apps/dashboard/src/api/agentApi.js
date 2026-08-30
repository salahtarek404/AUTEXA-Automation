const AGENT_URL = 'http://localhost:8000/api';

let activeTenantId = 'autexa';

export const setTenantId = (id) => {
    activeTenantId = id;
};

export const getTenantId = () => {
    return activeTenantId;
};

export const getLeads = async () => {
    try {
        const res = await fetch(`${AGENT_URL}/leads`, {
            headers: { 'X-Tenant-ID': activeTenantId }
        });
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        console.error("Agent API Error:", e);
        return [];
    }
};

export const getProposals = async () => {
    try {
        const res = await fetch(`${AGENT_URL}/proposals`, {
            headers: { 'X-Tenant-ID': activeTenantId }
        });
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        console.error("Proposals API Error:", e);
        return [];
    }
};

export const approveProposal = async (id) => {
    const res = await fetch(`${AGENT_URL}/proposals/${id}/approve`, {
        method: 'PATCH',
        headers: { 
            'Content-Type': 'application/json',
            'X-Tenant-ID': activeTenantId
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Approval failed');
    }
    return await res.json();
};

export const getAnalytics = async (startDate = '', endDate = '') => {
    try {
        let url = `${AGENT_URL}/analytics`;
        const params = [];
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        if (params.length) url += `?${params.join('&')}`;

        const res = await fetch(url, {
            headers: { 'X-Tenant-ID': activeTenantId }
        });
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        console.error("Analytics API Error:", e);
        return {
            conversion_rate: 0,
            average_response_time_seconds: null,
            source_performance: [],
            total_leads: 0,
            converted_leads: 0
        };
    }
};
