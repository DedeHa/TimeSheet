const dashboard = {
    // Configuration
    config: {
        apiBasePath: '../data/',
        refreshInterval: 300000, // 5 minutes
        chartColors: {
            primary: '#2563eb',
            secondary: '#64748b',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444'
        }
    },

    // Data storage
    data: {
        metrics: null,
        runtimes: null,
        lastUpdated: null
    },

    // Chart instances
    charts: {},

    // Initialize dashboard
    init() {
        this.loadData();
        this.setupEventListeners();
        this.startAutoRefresh();
    },

    // Load data from JSON files
    async loadData() {
        try {
            const [metricsResponse, runtimesResponse] = await Promise.all([
                fetch(`${this.config.apiBasePath}metrics.json`),
                fetch(`${this.config.apiBasePath}runtimes.json`)
            ]);

            if (!metricsResponse.ok) throw new Error('Failed to fetch metrics.json');
            if (!runtimesResponse.ok) throw new Error('Failed to fetch runtimes.json');

            const metrics = await metricsResponse.json();
            const runtimes = await runtimesResponse.json();

            this.data.metrics = metrics;
            this.data.runtimes = runtimes;
            this.data.lastUpdated = new Date();

            this.updateSummaryPanel();
            this.renderCharts();
            this.renderDataTable();

            this.showNotification('Data loaded successfully', 'success');

        } catch (error) {
            console.error('Error loading data:', error);
            this.showNotification(`Error loading data: ${error.message}`, 'error');
        }
    },

    // Update summary panel with latest metrics
    updateSummaryPanel() {
        if (!this.data.metrics) return;

        const ready = this.data.metrics.ready || {};
        const label = this._getPrimaryLabel();
        const entry = label ? ready[label] : null;

        document.getElementById('total-runs').textContent = this._distinctRunCount();
        document.getElementById('latest-mean').textContent = entry ? `${entry.mean.toFixed(2)}s` : '--';
        document.getElementById('latest-p95').textContent = entry ? `${entry.p95.toFixed(2)}s` : '--';
        document.getElementById('latest-run').textContent = label || '--';
        document.getElementById('last-updated').textContent = this.data.lastUpdated ? 
            this.data.lastUpdated.toLocaleString() : '--';
    },

    _getPrimaryLabel() {
        const ready = this.data.metrics && this.data.metrics.ready;
        if (!ready) return null;
        const keys = Object.keys(ready);
        const jobTotalKey = keys.find(k => k.endsWith(' / <job total>'));
        return jobTotalKey ? jobTotalKey : keys[0];
    },

    _getPrimaryEntry() {
        const ready = this.data.metrics && this.data.metrics.ready;
        if (!ready) return null;
        const label = this._getPrimaryLabel();
        return label ? ready[label] : null;
    },

    _distinctRunCount() {
        const runs = this.data.runtimes && this.data.runtimes.runs;
        if (!runs) return 0;
        return new Set(runs.map(r => String(r.run_id))).size;
    },

    _groupByJob(ready) {
        const jobs = {};
        for (const [key, val] of Object.entries(ready)) {
            const job = key.split(' / ')[0] || key;
            if (!jobs[job]) jobs[job] = [];
            jobs[job].push({ key, ...val });
        }
        return jobs;
    },

    // Render all charts
    renderCharts() {
        if (!this.data.metrics) return;

        this.renderRollingChart();
        this.renderNormalDistributionChart();
        this.renderHistoricalTrendsChart();
        this.renderJobBreakdownChart();
        this.renderBollingerBandsChart();
    },

    // Render rolling statistics chart
    renderRollingChart() {
        const ctx = document.getElementById('rolling-chart').getContext('2d');
        const entry = this._getPrimaryEntry();
        const rolling = (entry && entry.rolling) || [];

        if (this.charts.rolling) {
            this.charts.rolling.destroy();
        }

        this.charts.rolling = new Chart(ctx, {
            type: 'line',
            data: {
                labels: rolling.map((item, index) => `Run ${item.start}-${item.end}`),
                datasets: [{
                    label: 'Rolling Mean (20-run window)',
                    data: rolling.map(item => item.mean),
                    borderColor: this.config.chartColors.primary,
                    backgroundColor: this.config.chartColors.primary + '20',
                    tension: 0.1,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }, {
                    label: 'Rolling StdDev (20-run window)',
                    data: rolling.map(item => item.stddev),
                    borderColor: this.config.chartColors.secondary,
                    backgroundColor: this.config.chartColors.secondary + '20',
                    tension: 0.1,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Rolling Statistics (20-run window)'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Run Window'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Duration (seconds)'
                        },
                        min: 0
                    },
                    y1: {
                        display: true,
                        title: {
                            display: true,
                            text: 'StdDev (seconds)'
                        },
                        min: 0,
                        position: 'right'
                    }
                }
            }
        });
    },

    // Render normal distribution chart
    renderNormalDistributionChart() {
        const ctx = document.getElementById('normal-distribution').getContext('2d');
        const entry = this._getPrimaryEntry();
        const dist = (entry && entry.distribution) || null;

        if (this.charts.normalDistribution) {
            this.charts.normalDistribution.destroy();
        }

        if (dist && dist.curve && dist.curve.length) {
            this.charts.normalDistribution = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dist.curve.map(p => p.x.toFixed(1)),
                    datasets: [{
                        label: 'Normal Distribution PDF',
                        data: dist.curve.map(p => p.y),
                        borderColor: this.config.chartColors.primary,
                        backgroundColor: this.config.chartColors.primary + '20',
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Normal Distribution Curve'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Duration (seconds)'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Probability Density'
                            },
                            min: 0
                        }
                    }
                }
            });
        }
    },

    // Render historical trends chart
    renderHistoricalTrendsChart() {
        const ctx = document.getElementById('historical-trends').getContext('2d');
        const ready = this.data.metrics && this.data.metrics.ready || {};
        const entries = Object.entries(ready);

        if (this.charts.historicalTrends) {
            this.charts.historicalTrends.destroy();
        }

        this.charts.historicalTrends = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: entries.map(([key]) => key.length > 22 ? key.slice(0,22)+'...' : key),
                datasets: [{
                    type: 'bar',
                    label: 'Mean',
                    data: entries.map(([,v]) => v.mean),
                    backgroundColor: this.generateColors(entries.length),
                    borderColor: this.generateColors(entries.length),
                    borderWidth: 1
                }, {
                    type: 'line',
                    label: 'P95',
                    data: entries.map(([,v]) => v.p95),
                    borderColor: this.config.chartColors.warning,
                    backgroundColor: this.config.chartColors.warning + '20',
                    tension: 0.1,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Historical Trends (P95)'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Job / Step'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Duration (seconds)'
                        },
                        min: 0
                    }
                }
            }
        });
    },

    // Render job breakdown chart
    renderJobBreakdownChart() {
        const ctx = document.getElementById('job-breakdown').getContext('2d');
        const ready = this.data.metrics && this.data.metrics.ready || {};
        const jobs = this._groupByJob(ready);
        const jobNames = Object.keys(jobs);
        const means = jobNames.map(job => {
            const vals = jobs[job].map(v => v.mean);
            return vals.reduce((a,b)=>a+b,0)/vals.length;
        });

        if (this.charts.jobBreakdown) {
            this.charts.jobBreakdown.destroy();
        }

        this.charts.jobBreakdown = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: jobNames,
                datasets: [{
                    label: 'Job Mean Duration',
                    data: means,
                    backgroundColor: this.generateColors(jobNames.length),
                    borderColor: this.generateColors(jobNames.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Job Breakdown (Latest Run)'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Job Name'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Duration (seconds)'
                        },
                        min: 0
                    }
                }
            }
        });
    },

    // Render Bollinger bands chart
    renderBollingerBandsChart() {
        const ctx = document.getElementById('bollinger-bands').getContext('2d');
        const entry = this._getPrimaryEntry();
        const boll = (entry && entry.bollinger) || [];

        if (this.charts.bollingerBands) {
            this.charts.bollingerBands.destroy();
        }

        if (boll.length) {
            this.charts.bollingerBands = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: boll.map((b,i) => `Run ${b.start}-${b.end}`),
                    datasets: [{
                        label: 'Middle Band (Mean)',
                        data: boll.map(b => b.mean),
                        borderColor: this.config.chartColors.primary,
                        backgroundColor: this.config.chartColors.primary + '20',
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }, {
                        label: 'Upper Band (Mean + 2σ)',
                        data: boll.map(b => b.upper),
                        borderColor: this.config.chartColors.success,
                        backgroundColor: this.config.chartColors.success + '20',
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        fill: false
                    }, {
                        label: 'Lower Band (Mean - 2σ)',
                        data: boll.map(b => b.lower),
                        borderColor: this.config.chartColors.danger,
                        backgroundColor: this.config.chartColors.danger + '20',
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Bollinger Bands (20-run window)'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Run Window'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Duration (seconds)'
                            },
                            min: 0
                        }
                    }
                }
            });
        }
    },

    // Render data table
    renderDataTable() {
        if (!this.data.runtimes) return;

        const tbody = document.querySelector('#runs-table tbody');
        tbody.innerHTML = '';

        // Sort runs by run_id numerically
        const sortedRuns = [...this.data.runtimes.runs].sort((a, b) => Number(a.run_id) - Number(b.run_id));

        sortedRuns.forEach(run => {
            const row = tbody.insertRow();

            const runIdCell = row.insertCell(0);
            runIdCell.textContent = run.run_id;

            const prNumberCell = row.insertCell(1);
            prNumberCell.textContent = run.pr_number || '--';

            const createdAtCell = row.insertCell(2);
            createdAtCell.textContent = new Date(run.created_at).toLocaleString();

            const jobNameCell = row.insertCell(3);
            jobNameCell.textContent = run.job_name;

            const durationCell = row.insertCell(4);
            durationCell.textContent = run.duration_s ? run.duration_s.toFixed(2) : '--';

            const conclusionCell = row.insertCell(5);
            conclusionCell.textContent = run.conclusion;
            conclusionCell.style.color = run.conclusion === 'success' ? '#10b981' :
                                          run.conclusion === 'failure' ? '#ef4444' :
                                          run.conclusion === 'cancelled' ? '#f59e0b' : '#64748b';
        });
    },

    // Generate colors for charts
    generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 360 / count) % 360;
            colors.push(`hsl(${hue}, 70%, 50%)`);
        }
        return colors;
    },

    // Setup event listeners
    setupEventListeners() {
        document.getElementById('refresh-data').addEventListener('click', () => {
            this.loadData();
        });
    },

    // Start auto-refresh
    startAutoRefresh() {
        setInterval(() => {
            this.loadData();
        }, this.config.refreshInterval);
    },

    // Show notification
    showNotification(message, type = 'info') {
        const container = document.body;

        const notification = document.createElement('div');
        notification.className = type === 'error' ? 'error' : 
                                 type === 'success' ? 'success' : '';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 16px;
            border-radius: 6px;
            z-index: 1000;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            animation: slideIn 0.3s ease;
        `;

        container.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                container.removeChild(notification);
            }, 300);
        }, 3000);
    }
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    dashboard.init();
});
