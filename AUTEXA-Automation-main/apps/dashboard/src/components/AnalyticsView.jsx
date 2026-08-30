import React, { useState, useEffect } from 'react';
import { getAnalytics } from '../api/agentApi';
import { Calendar, BarChart3, TrendingUp, Clock, AlertCircle, RefreshCw } from 'lucide-react';

export default function AnalyticsView() {
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState({
        conversion_rate: 0,
        average_response_time_seconds: null,
        source_performance: [],
        total_leads: 0,
        converted_leads: 0
    });

    const fetchAnalytics = async () => {
        setLoading(true);
        const res = await getAnalytics(startDate, endDate);
        setData(res);
        setLoading(false);
    };

    useEffect(() => {
        fetchAnalytics();
    }, [startDate, endDate]);

    // Format response time nicely (e.g., "1m 23s" or "45s")
    const formatResponseTime = (seconds) => {
        if (seconds === null || seconds === undefined) return 'N/A';
        if (seconds < 60) return `${Math.round(seconds)}s`;
        const mins = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${mins}m ${secs}s`;
    };

    // Quick filter helper
    const handleQuickFilter = (days) => {
        if (days === 'all') {
            setStartDate('');
            setEndDate('');
            return;
        }
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - days);

        // Format to YYYY-MM-DD local time
        const offset = start.getTimezoneOffset();
        const startLocal = new Date(start.getTime() - (offset*60*1000));
        const endLocal = new Date(end.getTime() - (offset*60*1000));

        setStartDate(startLocal.toISOString().split('T')[0]);
        setEndDate(endLocal.toISOString().split('T')[0]);
    };

    return (
        <div className="space-y-8">
            {/* Filter controls */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-100 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                        <Calendar className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-gray-800">Date Range</h3>
                        <p className="text-xs text-gray-500">Filter performance metrics</p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    {/* Presets */}
                    <div className="flex bg-gray-100 p-1 rounded-xl">
                        <button
                            onClick={() => handleQuickFilter('all')}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer transition-colors ${!startDate && !endDate ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
                        >
                            All Time
                        </button>
                        <button
                            onClick={() => handleQuickFilter(7)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer transition-colors ${startDate && (new Date() - new Date(startDate)) < 8 * 24 * 3600 * 1000 ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
                        >
                            Last 7 Days
                        </button>
                        <button
                            onClick={() => handleQuickFilter(30)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer transition-colors ${startDate && (new Date() - new Date(startDate)) > 8 * 24 * 3600 * 1000 && (new Date() - new Date(startDate)) < 32 * 24 * 3600 * 1000 ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
                        >
                            Last 30 Days
                        </button>
                    </div>

                    {/* Custom Picker Inputs */}
                    <div className="flex items-center gap-2">
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 focus:outline-none"
                        />
                        <span className="text-gray-400 text-xs">to</span>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 focus:outline-none"
                        />
                    </div>

                    <button
                        onClick={fetchAnalytics}
                        className="p-2 text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-xl border border-gray-200 transition-colors cursor-pointer"
                        title="Reload metrics"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-16 text-center text-gray-400 flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
                    <span>Analyzing metrics data...</span>
                </div>
            ) : (
                <>
                    {/* Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Conversion Rate Card */}
                        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between min-h-[160px]">
                            <div className="flex justify-between items-start">
                                <div>
                                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Conversion Rate</span>
                                    <div className="text-3xl font-extrabold text-gray-900 mt-1">{data.conversion_rate}%</div>
                                </div>
                                <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
                                    <TrendingUp className="w-5 h-5" />
                                </div>
                            </div>
                            <div className="mt-4">
                                <div className="w-full bg-gray-100 rounded-full h-2">
                                    <div 
                                        className="bg-gradient-to-r from-emerald-400 to-teal-500 h-2 rounded-full transition-all duration-500" 
                                        style={{ width: `${Math.min(data.conversion_rate, 100)}%` }}
                                    ></div>
                                </div>
                                <div className="text-xs text-gray-400 mt-2 flex justify-between">
                                    <span>{data.converted_leads} won</span>
                                    <span>{data.total_leads} total leads</span>
                                </div>
                            </div>
                        </div>

                        {/* Response Time Card */}
                        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between min-h-[160px]">
                            <div className="flex justify-between items-start">
                                <div>
                                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Avg. Response Time</span>
                                    <div className="text-3xl font-extrabold text-gray-900 mt-1">
                                        {formatResponseTime(data.average_response_time_seconds)}
                                    </div>
                                </div>
                                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                                    <Clock className="w-5 h-5" />
                                </div>
                            </div>
                            <p className="text-xs text-gray-400 mt-auto">
                                Derived from first message exchange timestamps.
                            </p>
                        </div>

                        {/* Total Leads Card */}
                        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm relative overflow-hidden flex flex-col justify-between min-h-[160px]">
                            <div className="flex justify-between items-start">
                                <div>
                                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Leads</span>
                                    <div className="text-3xl font-extrabold text-gray-900 mt-1">{data.total_leads}</div>
                                </div>
                                <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                                    <BarChart3 className="w-5 h-5" />
                                </div>
                            </div>
                            <div className="text-xs text-gray-400 mt-auto">
                                Active contacts across all channels within this date range.
                            </div>
                        </div>
                    </div>

                    {/* Breakdown & Chart Section */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* Channel breakdown */}
                        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
                            <div className="flex items-center justify-between pb-4 border-b border-gray-50 mb-4">
                                <h3 className="font-bold text-gray-800">Lead Source Performance</h3>
                                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                                    {data.source_performance.length} Channels
                                </span>
                            </div>

                            <div className="overflow-x-auto flex-1">
                                <table className="w-full text-left border-collapse text-xs">
                                    <thead>
                                        <tr className="text-gray-400 font-semibold uppercase tracking-wider border-b border-gray-50">
                                            <th className="py-2.5">Source</th>
                                            <th className="py-2.5">Total Leads</th>
                                            <th className="py-2.5">Converted</th>
                                            <th className="py-2.5 text-right">Conversion Rate</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50 text-gray-600">
                                        {data.source_performance.length === 0 ? (
                                            <tr>
                                                <td colSpan="4" className="py-8 text-center text-gray-400">
                                                    No channel metrics found for this period.
                                                </td>
                                            </tr>
                                        ) : (
                                            data.source_performance.map((perf, index) => (
                                                <tr key={index} className="hover:bg-gray-50/50 transition-colors">
                                                    <td className="py-3 font-semibold text-gray-800 capitalize flex items-center gap-2">
                                                        <span className={`w-2.5 h-2.5 rounded-full ${
                                                            perf.source === 'website' ? 'bg-indigo-500' :
                                                            perf.source === 'whatsapp' ? 'bg-emerald-500' :
                                                            perf.source === 'instagram' ? 'bg-pink-500' : 'bg-gray-400'
                                                        }`} />
                                                        {perf.source}
                                                    </td>
                                                    <td className="py-3 font-medium">{perf.total_leads}</td>
                                                    <td className="py-3 font-medium text-emerald-600">{perf.converted_leads}</td>
                                                    <td className="py-3 font-semibold text-right text-gray-900">{perf.conversion_rate}%</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Interactive SVG Chart */}
                        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col justify-between">
                            <div className="flex items-center justify-between pb-4 border-b border-gray-50 mb-4">
                                <h3 className="font-bold text-gray-800">Conversion Rate by Channel</h3>
                            </div>

                            {data.source_performance.length === 0 ? (
                                <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-8 text-center">
                                    <AlertCircle className="w-8 h-8 text-gray-300 mb-2" />
                                    <span>No chart data available</span>
                                </div>
                            ) : (
                                <div className="flex-1 flex flex-col justify-center space-y-5 py-4">
                                    {data.source_performance.map((perf, index) => (
                                        <div key={index} className="space-y-1.5">
                                            <div className="flex justify-between text-xs font-semibold text-gray-700">
                                                <span className="capitalize">{perf.source}</span>
                                                <span>{perf.conversion_rate}% ({perf.converted_leads}/{perf.total_leads})</span>
                                            </div>
                                            <div className="w-full bg-gray-100 rounded-full h-3">
                                                <div 
                                                    className={`h-3 rounded-full transition-all duration-500 ${
                                                        perf.source === 'website' ? 'bg-gradient-to-r from-indigo-500 to-blue-500' :
                                                        perf.source === 'whatsapp' ? 'bg-gradient-to-r from-emerald-500 to-teal-500' :
                                                        perf.source === 'instagram' ? 'bg-gradient-to-r from-pink-500 to-purple-500' : 'bg-gray-400'
                                                    }`}
                                                    style={{ width: `${perf.conversion_rate}%` }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
