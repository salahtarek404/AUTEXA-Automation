import React, { useEffect, useState } from 'react';
import { getLeads } from '../api/agentApi';
import { Users, Phone, LayoutGrid, Table as TableIcon, Flame, Target, MessageSquare } from 'lucide-react';

export default function LeadsTable() {
    const [leads, setLeads] = useState([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState('pipeline'); // 'pipeline' or 'table'

    const fetchLeads = async () => {
        setLoading(true);
        const data = await getLeads();
        setLeads(data);
        setLoading(false);
    };

    useEffect(() => {
        fetchLeads();
    }, []);

    // Helper to get priority badge color classes
    const getPriorityBadge = (priority) => {
        if (!priority) return null;
        const lower = priority.toLowerCase();
        if (lower === 'hot') return 'bg-rose-50 text-rose-700 border-rose-100';
        if (lower === 'warm') return 'bg-amber-50 text-amber-700 border-amber-100';
        return 'bg-blue-50 text-blue-700 border-blue-100';
    };

    // Helper to get intent badge color classes
    const getIntentBadge = (intent) => {
        if (!intent) return null;
        const lower = intent.toLowerCase();
        if (lower === 'buying') return 'bg-emerald-50 text-emerald-700 border-emerald-100';
        if (lower === 'browsing') return 'bg-indigo-50 text-indigo-700 border-indigo-100';
        return 'bg-slate-50 text-slate-700 border-slate-100';
    };

    // Kanban columns mapping
    const columns = [
        { id: 'new', title: 'New Leads', statuses: ['new'] },
        { id: 'qualified', title: 'Qualified', statuses: ['qualified'] },
        { id: 'proposal', title: 'Proposal', statuses: ['proposal_sent', 'proposal'] },
        { id: 'won', title: 'Won', statuses: ['won'] }
    ];

    return (
        <div className="space-y-6">
            {/* View controls & actions */}
            <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                <div className="flex items-center gap-4">
                    <div className="flex bg-gray-100 p-1 rounded-lg">
                        <button
                            onClick={() => setViewMode('pipeline')}
                            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                                viewMode === 'pipeline'
                                    ? 'bg-white text-indigo-600 shadow-sm'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                        >
                            <LayoutGrid className="w-4 h-4" />
                            Pipeline View
                        </button>
                        <button
                            onClick={() => setViewMode('table')}
                            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                                viewMode === 'table'
                                    ? 'bg-white text-indigo-600 shadow-sm'
                                    : 'text-gray-600 hover:text-gray-900'
                            }`}
                        >
                            <TableIcon className="w-4 h-4" />
                            Table View
                        </button>
                    </div>
                </div>
                
                <button
                    onClick={fetchLeads}
                    className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm transition-colors cursor-pointer"
                >
                    Refresh Leads
                </button>
            </div>

            {loading ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-400">
                    Loading leads...
                </div>
            ) : viewMode === 'pipeline' ? (
                /* Kanban Pipeline View */
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {columns.map(col => {
                        const colLeads = leads.filter(l => col.statuses.includes(l.status?.toLowerCase()));
                        return (
                            <div key={col.id} className="flex flex-col bg-gray-50/50 rounded-xl p-4 border border-gray-100 min-h-[500px]">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wider">{col.title}</h3>
                                    <span className="bg-gray-200/80 text-gray-700 text-xs px-2 py-0.5 rounded-full font-bold">
                                        {colLeads.length}
                                    </span>
                                </div>
                                <div className="flex-1 space-y-3 overflow-y-auto">
                                    {colLeads.length === 0 ? (
                                        <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center text-xs text-gray-400">
                                            No leads here
                                        </div>
                                    ) : (
                                        colLeads.map(lead => (
                                            <div key={lead.id} className="bg-white p-4 rounded-xl border border-gray-200/80 shadow-sm hover:shadow-md transition-shadow space-y-3">
                                                <div>
                                                    <div className="font-semibold text-gray-900 text-sm">{lead.name}</div>
                                                    {lead.business_type && (
                                                        <div className="text-xs font-medium text-indigo-600 mt-0.5">{lead.business_type}</div>
                                                    )}
                                                </div>

                                                <div className="flex flex-wrap gap-1.5">
                                                    {lead.intent && (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold border capitalize ${getIntentBadge(lead.intent)}`}>
                                                            <Target className="w-2.5 h-2.5 mr-1" />
                                                            {lead.intent}
                                                        </span>
                                                    )}
                                                    {lead.priority && (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold border capitalize ${getPriorityBadge(lead.priority)}`}>
                                                            <Flame className="w-2.5 h-2.5 mr-1" />
                                                            {lead.priority}
                                                        </span>
                                                    )}
                                                </div>

                                                {lead.service_requested && (
                                                    <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded-lg border border-gray-100">
                                                        <span className="font-medium text-gray-700">Requested:</span> {lead.service_requested}
                                                    </div>
                                                )}

                                                <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
                                                    <div className="flex items-center gap-1">
                                                        <Phone className="w-3 h-3" />
                                                        {lead.phone || '-'}
                                                    </div>
                                                    <span className="inline-flex px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded text-[9px] font-bold border border-purple-100 capitalize">
                                                        {lead.source}
                                                    </span>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                /* Traditional Table View */
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-50 rounded-lg">
                                <Users className="w-5 h-5 text-blue-600" />
                            </div>
                            <h2 className="text-xl font-semibold text-gray-800">Leads List</h2>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50/50 border-b border-gray-100">
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Lead</th>
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Contact</th>
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Source</th>
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Analysis</th>
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {leads.length === 0 ? (
                                    <tr><td colSpan="6" className="p-8 text-center text-gray-400">No leads found.</td></tr>
                                ) : (
                                    leads.map(lead => (
                                        <tr key={lead.id} className="hover:bg-gray-50/50 transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">{lead.name}</div>
                                                {lead.business_type && <div className="text-xs text-indigo-600 mt-1">{lead.business_type}</div>}
                                            </td>
                                            <td className="px-6 py-4 text-gray-600">
                                                <div className="flex items-center gap-2 text-sm">
                                                    <Phone className="w-4 h-4 text-gray-400" />
                                                    {lead.phone || '-'}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 capitalize border border-purple-100">
                                                    {lead.source}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex gap-1.5">
                                                    {lead.intent && (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border capitalize ${getIntentBadge(lead.intent)}`}>
                                                            {lead.intent}
                                                        </span>
                                                    )}
                                                    {lead.priority && (
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border capitalize ${getPriorityBadge(lead.priority)}`}>
                                                            {lead.priority}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium capitalize border ${
                                                    lead.status === 'new' ? 'bg-green-50 text-green-700 border-green-100' :
                                                    lead.status === 'qualified' ? 'bg-blue-50 text-blue-700 border-blue-100' : 
                                                    lead.status === 'proposal_sent' || lead.status === 'proposal' ? 'bg-amber-50 text-amber-700 border-amber-100' :
                                                    'bg-gray-50 text-gray-700 border-gray-100'
                                                }`}>
                                                    {lead.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                                                {new Date(lead.created_at).toLocaleDateString()}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
