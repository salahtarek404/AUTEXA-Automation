import React, { useEffect, useState } from 'react';
import { getProposals, approveProposal } from '../api/agentApi';
import { FileText, CheckCircle, Clock, AlertTriangle, X, DollarSign, Calendar, Building } from 'lucide-react';

export default function ProposalsView() {
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [confirmModal, setConfirmModal] = useState(null); // { proposalId, leadName }
    const [approving, setApproving] = useState(false);
    const [toast, setToast] = useState(null);

    const fetchProposals = async () => {
        setLoading(true);
        const data = await getProposals();
        setProposals(data);
        setLoading(false);
    };

    useEffect(() => {
        fetchProposals();
    }, []);

    const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3500);
    };

    const handleApproveClick = (proposal) => {
        setConfirmModal({ proposalId: proposal.id, leadName: proposal.lead_name });
    };

    const handleConfirmApprove = async () => {
        if (!confirmModal) return;
        setApproving(true);
        try {
            await approveProposal(confirmModal.proposalId);
            showToast(`Proposal for ${confirmModal.leadName} approved. Remember to dispatch it manually.`);
            setConfirmModal(null);
            fetchProposals();
        } catch (e) {
            showToast('Failed to approve proposal. Please try again.', 'error');
        } finally {
            setApproving(false);
        }
    };

    const statusConfig = {
        draft: {
            label: 'DRAFT — PENDING APPROVAL',
            bg: 'bg-amber-50',
            border: 'border-amber-300',
            badge: 'bg-amber-100 text-amber-800 border-amber-300',
            icon: <AlertTriangle className="w-3.5 h-3.5" />,
        },
        approved: {
            label: 'APPROVED',
            bg: 'bg-emerald-50',
            border: 'border-emerald-200',
            badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
            icon: <CheckCircle className="w-3.5 h-3.5" />,
        },
        sent: {
            label: 'SENT',
            bg: 'bg-blue-50',
            border: 'border-blue-200',
            badge: 'bg-blue-100 text-blue-800 border-blue-200',
            icon: <FileText className="w-3.5 h-3.5" />,
        },
    };

    return (
        <div className="space-y-6">
            {/* Toast */}
            {toast && (
                <div className={`fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all ${toast.type === 'error'
                        ? 'bg-red-50 border-red-200 text-red-800'
                        : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    }`}>
                    {toast.type === 'error' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                    {toast.msg}
                </div>
            )}

            {/* Header bar */}
            <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-50 rounded-lg">
                        <FileText className="w-5 h-5 text-amber-600" />
                    </div>
                    <div>
                        <h2 className="font-semibold text-gray-900">Proposal Drafts</h2>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Review AI-generated drafts. Approval does not send — you dispatch manually.
                        </p>
                    </div>
                </div>
                <button
                    onClick={fetchProposals}
                    className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm transition-colors cursor-pointer"
                >
                    Refresh
                </button>
            </div>

            {loading ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-400">
                    Loading proposals...
                </div>
            ) : proposals.length === 0 ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-16 text-center">
                    <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">No proposals yet</p>
                    <p className="text-gray-400 text-sm mt-1">
                        The agent will draft proposals when a lead is qualified as hot + buying.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
                    {proposals.map(p => {
                        const cfg = statusConfig[p.status] || statusConfig.draft;
                        return (
                            <div
                                key={p.id}
                                className={`rounded-xl border-2 p-5 space-y-4 transition-shadow hover:shadow-md ${cfg.bg} ${cfg.border}`}
                            >
                                {/* Status banner */}
                                <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border tracking-wide ${cfg.badge}`}>
                                    {cfg.icon}
                                    {cfg.label}
                                </div>

                                {/* Lead info */}
                                <div>
                                    <div className="font-bold text-gray-900 text-base">{p.lead_name}</div>
                                    {p.lead_email && <div className="text-xs text-gray-500 mt-0.5">{p.lead_email}</div>}
                                    {p.lead_phone && <div className="text-xs text-gray-500">{p.lead_phone}</div>}
                                </div>

                                {/* Scope */}
                                <div className="bg-white/70 rounded-lg p-3 space-y-1 border border-white">
                                    <div className="flex items-start gap-2 text-xs text-gray-700">
                                        <Building className="w-3.5 h-3.5 mt-0.5 text-indigo-500 shrink-0" />
                                        <span>{p.service_scope}</span>
                                    </div>
                                </div>

                                {/* Price & timeline */}
                                <div className="flex gap-3">
                                    <div className="flex-1 bg-white/70 rounded-lg p-2.5 border border-white">
                                        <div className="flex items-center gap-1 text-[10px] font-semibold text-gray-500 uppercase mb-1">
                                            <DollarSign className="w-3 h-3" /> Estimate
                                        </div>
                                        <div className="text-xs font-medium text-gray-800">{p.estimated_price}</div>
                                        <div className="text-[9px] text-gray-400 mt-0.5 italic">Rough estimate only</div>
                                    </div>
                                    <div className="flex-1 bg-white/70 rounded-lg p-2.5 border border-white">
                                        <div className="flex items-center gap-1 text-[10px] font-semibold text-gray-500 uppercase mb-1">
                                            <Calendar className="w-3 h-3" /> Timeline
                                        </div>
                                        <div className="text-xs font-medium text-gray-800">{p.estimated_timeline}</div>
                                    </div>
                                </div>

                                {/* Date + action */}
                                <div className="flex items-center justify-between pt-1">
                                    <div className="flex items-center gap-1 text-[10px] text-gray-400">
                                        <Clock className="w-3 h-3" />
                                        {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                                    </div>
                                    {p.status === 'draft' && (
                                        <button
                                            onClick={() => handleApproveClick(p)}
                                            className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors cursor-pointer"
                                        >
                                            Approve Proposal
                                        </button>
                                    )}
                                    {p.status === 'approved' && (
                                        <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                                            <CheckCircle className="w-3.5 h-3.5" /> Approved
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Confirmation Modal */}
            {confirmModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 space-y-5">
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-amber-50 rounded-lg">
                                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                                </div>
                                <h3 className="font-bold text-gray-900 text-lg">Confirm Approval</h3>
                            </div>
                            <button
                                onClick={() => setConfirmModal(null)}
                                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                            >
                                <X className="w-4 h-4 text-gray-500" />
                            </button>
                        </div>

                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800 space-y-2">
                            <p className="font-semibold">⚠️ Human action required before sending</p>
                            <p>
                                You are approving the draft proposal for <strong>{confirmModal.leadName}</strong>.
                            </p>
                            <p>
                                This will mark the proposal as <strong>approved</strong>.{' '}
                                <span className="underline">The customer has NOT been notified</span> — you are responsible for sending it manually after approval.
                            </p>
                            <p className="text-xs">All pricing in this proposal is a rough estimate. Final billing depends on scoping.</p>
                        </div>

                        <div className="flex gap-3 pt-1">
                            <button
                                onClick={() => setConfirmModal(null)}
                                disabled={approving}
                                className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors cursor-pointer disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmApprove}
                                disabled={approving}
                                className="flex-1 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors cursor-pointer disabled:opacity-50"
                            >
                                {approving ? 'Approving...' : 'Confirm Approval'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
