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
}
