const AGENT_URL = 'http://localhost:8000/api';

export const getLeads = async () => {
    try {
        const res = await fetch(`${AGENT_URL}/leads`);
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        console.error("Agent API Error:", e);
        return [];
    }
};

export const getProposals = async () => {
    try {
        const res = await fetch(`${AGENT_URL}/proposals`);
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
        headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Approval failed');
    }
    return await res.json();
};
