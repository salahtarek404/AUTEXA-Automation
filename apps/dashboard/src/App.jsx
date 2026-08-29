import React, { useState } from 'react';
import LeadsTable from './components/LeadsTable';
import ProposalsView from './components/ProposalsView';
import { LayoutDashboard, FileText } from 'lucide-react';

const TABS = [
    { id: 'leads', label: 'Leads', icon: LayoutDashboard },
    { id: 'proposals', label: 'Proposals', icon: FileText },
];

function App() {
    const [activeTab, setActiveTab] = useState('leads');

    return (
        <div className="min-h-screen bg-gray-50">
            <nav className="bg-white border-b border-gray-100 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16 items-center">
                        <div className="flex items-center gap-6">
                            <div className="flex items-center gap-3 cursor-pointer">
                                <div className="p-2 bg-indigo-600 text-white rounded-lg">
                                    <LayoutDashboard className="w-5 h-5" />
                                </div>
                                <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">
                                    Autexa
                                </span>
                            </div>

                            {/* Tab navigation */}
                            <div className="flex bg-gray-100 p-1 rounded-lg">
                                {TABS.map(tab => {
                                    const Icon = tab.icon;
                                    return (
                                        <button
                                            key={tab.id}
                                            onClick={() => setActiveTab(tab.id)}
                                            className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${activeTab === tab.id
                                                    ? 'bg-white text-indigo-600 shadow-sm'
                                                    : 'text-gray-600 hover:text-gray-900'
                                                }`}
                                        >
                                            <Icon className="w-4 h-4" />
                                            {tab.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-700">Admin</span>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-8">
                    {activeTab === 'leads' && (
                        <>
                            <h1 className="text-2xl font-bold text-gray-900">Lead Pipeline</h1>
                            <p className="mt-1 text-sm text-gray-500">Monitor incoming leads from your AI channels in real-time.</p>
                        </>
                    )}
                    {activeTab === 'proposals' && (
                        <>
                            <h1 className="text-2xl font-bold text-gray-900">Proposals</h1>
                            <p className="mt-1 text-sm text-gray-500">
                                Review AI-generated draft proposals. Approve them here — nothing is sent automatically.
                            </p>
                        </>
                    )}
                </div>

                {activeTab === 'leads' && <LeadsTable />}
                {activeTab === 'proposals' && <ProposalsView />}
            </main>
        </div>
    );
}

export default App;
