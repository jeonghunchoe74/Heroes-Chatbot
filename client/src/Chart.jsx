// npm install recharts

import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';
import './Chart.css';

const API_BASE_URL = 'http://localhost:8000';

// 파이 차트 색상
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];


function Chart({ onBack }) {
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // 컴포넌트 마운트 시 데이터 가져오기
    useEffect(() => {
        fetchChartData();
    }, []);

    const fetchChartData = async () => {
        setLoading(true);
        setError(null);
        
        try {
        const response = await fetch(`${API_BASE_URL}/chart`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error(`서버 오류: ${response.status}`);
        }

        const data = await response.json();
        setChartData(data.data);
        } catch (error) {
        console.error('차트 데이터 로드 실패:', error);
        setError('차트 데이터를 불러오는데 실패했습니다.');
        } finally {
        setLoading(false);
        }
    };

    return (
        <div className="chart-container">
            <div className="chart-header">
                <h2>데이터 차트</h2>
                <button onClick={onBack} className="back-button">
                뒤로가기
                </button>
            </div>

            <div className="chart-content">
                {loading && (
                <div className="chart-loading">
                    <div className="loading-spinner"></div>
                    <p>데이터를 불러오는 중...</p>
                </div>
                )}

                {error && (
                <div className="chart-error">
                    <p>{error}</p>
                    <button onClick={fetchChartData} className="retry-button">
                    다시 시도
                    </button>
                </div>
                )}

                {!loading && !error && chartData.length > 0 && (
                <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                    >
                        {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                    </PieChart>
                </ResponsiveContainer>
                )}

                {!loading && !error && chartData.length === 0 && (
                <div className="chart-empty">
                    <p>표시할 데이터가 없습니다.</p>
                </div>
                )}
            </div>
        </div>
    );   
}

export default Chart;