import React from 'react';
import LeadsTable from './components/LeadsTable';
import { LayoutDashboard } from 'lucide-react';

function App() {
    return (
        <div className="min-h-screen">
            <nav className="bg-white border-b border-gray-100 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16 items-center">
                        <div className="flex items-center gap-3 cursor-pointer">
                            <div className="p-2 bg-indigo-600 text-white rounded-lg">
                                <LayoutDashboard className="w-5 h-5" />
                            </div>
                            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">
                                Autexa
                            </span>
                        </div>
                        <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-700">Admin</span>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-4rem)]">
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                    <p className="mt-1 text-sm text-gray-500">Monitor incoming leads from your AI channels in real-time.</p>
                </div>
                <LeadsTable />
            </main>
        </div>
    );
}

export default App;
