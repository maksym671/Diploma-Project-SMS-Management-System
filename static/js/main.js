/* ============================================================
   Student Management System — JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initSidebar();
    initAlerts();
    initAnimatedCounters();
    initCharts();
});


/* ─── Theme Toggle ──────────────────────────────────────────── */
function initThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('sms-theme', next);
    });
}


/* ─── Sidebar Toggle (Mobile) ───────────────────────────────── */
function initSidebar() {
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            if (overlay) overlay.classList.toggle('active');
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
            });
        }
    }
}


/* ─── Auto-dismiss Alerts ───────────────────────────────────── */
function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(40px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);

        // Close button
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateX(40px)';
                setTimeout(() => alert.remove(), 300);
            });
        }
    });
}


/* ─── Animated Counters ─────────────────────────────────────── */
function initAnimatedCounters() {
    const counters = document.querySelectorAll('.stat-value[data-target]');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseFloat(counter.dataset.target);
                const isFloat = target % 1 !== 0;
                const duration = 1200;
                const startTime = performance.now();

                function updateCounter(currentTime) {
                    const elapsed = currentTime - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    // Ease out cubic
                    const eased = 1 - Math.pow(1 - progress, 3);
                    const current = target * eased;

                    if (isFloat) {
                        counter.textContent = current.toFixed(2);
                    } else {
                        counter.textContent = Math.round(current).toLocaleString();
                    }

                    if (progress < 1) {
                        requestAnimationFrame(updateCounter);
                    }
                }

                requestAnimationFrame(updateCounter);
                observer.unobserve(counter);
            }
        });
    }, { threshold: 0.3 });

    counters.forEach(counter => observer.observe(counter));
}


/* ─── Helper: read CSS variable from :root ──────────────────── */
function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
/* ─── Custom HTML Legend Plugin ───────────────────────────── */
const htmlLegendPlugin = {
    id: 'htmlLegend',
    afterUpdate(chart, args, options) {
        const ul = document.getElementById(options.containerID);
        if (!ul) return;

        // Clear existing
        while (ul.firstChild) {
            ul.firstChild.remove();
        }

        const items = chart.options.plugins.legend.labels.generateLabels(chart);

        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'custom-chart-legend-item';
            if (item.hidden) div.classList.add('hidden');

            div.onclick = () => {
                const {type} = chart.config;
                if (type === 'doughnut' || type === 'polarArea') {
                    chart.toggleDataVisibility(item.index);
                } else {
                    chart.setDatasetVisibility(item.datasetIndex, !chart.isDatasetVisible(item.datasetIndex));
                }
                chart.update();
            };

            const colorSpan = document.createElement('div');
            colorSpan.className = 'custom-chart-legend-color';
            colorSpan.style.backgroundColor = item.fillStyle;

            const textNode = document.createTextNode(item.text);

            div.appendChild(colorSpan);
            div.appendChild(textNode);
            ul.appendChild(div);
        });
    }
};


/* ─── Charts (Chart.js) ─────────────────────────────────────── */
function initCharts() {
    initGradeDistributionChart();
    initCourseEnrollmentChart();
    initProgramChart();
}


function initGradeDistributionChart() {
    const canvas = document.getElementById('gradeChart');
    if (!canvas) return;

    const data = JSON.parse(canvas.dataset.grades || '{}');

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['A (4.5-5.0)', 'B (4.0-4.5)', 'C (3.5-4.0)', 'D (3.0-3.5)', 'F (<3.0)'],
            datasets: [{
                data: [data.A || 0, data.B || 0, data.C || 0, data.D || 0, data.F || 0],
                backgroundColor: [
                    getCSSVar('--grade-a'),
                    getCSSVar('--grade-b'),
                    getCSSVar('--grade-c'),
                    getCSSVar('--grade-d'),
                    getCSSVar('--grade-f'),
                ],
                borderColor: 'transparent',
                borderWidth: 0,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: {
                    display: false,
                },
                htmlLegend: {
                    containerID: 'gradeChartLegend'
                },
                tooltip: {
                    backgroundColor: getCSSVar('--chart-tooltip-bg'),
                    titleColor: getCSSVar('--chart-tooltip-title'),
                    bodyColor: getCSSVar('--chart-tooltip-body'),
                    borderColor: getCSSVar('--chart-tooltip-border'),
                    borderWidth: 1,
                    cornerRadius: 6,
                    padding: 10,
                    titleFont: { family: 'Inter', weight: '600', size: 12 },
                    bodyFont: { family: 'Inter', size: 12 },
                }
            }
        },
        plugins: [htmlLegendPlugin]
    });
}


function initCourseEnrollmentChart() {
    const canvas = document.getElementById('enrollmentChart');
    if (!canvas) return;

    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const values = JSON.parse(canvas.dataset.values || '[]');

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Active Enrollments',
                data: values,
                backgroundColor: getCSSVar('--chart-1'),
                borderColor: getCSSVar('--accent'),
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: getCSSVar('--chart-grid'),
                        drawBorder: false,
                    },
                    ticks: {
                        color: getCSSVar('--chart-tick'),
                        font: { family: 'Inter', size: 11 },
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: getCSSVar('--chart-grid'),
                        drawBorder: false,
                    },
                    ticks: {
                        color: getCSSVar('--chart-tick'),
                        font: { family: 'Inter', size: 11 },
                        stepSize: 1,
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: getCSSVar('--chart-tooltip-bg'),
                    titleColor: getCSSVar('--chart-tooltip-title'),
                    bodyColor: getCSSVar('--chart-tooltip-body'),
                    borderColor: getCSSVar('--chart-tooltip-border'),
                    borderWidth: 1,
                    cornerRadius: 6,
                    padding: 10,
                }
            }
        }
    });
}


function initProgramChart() {
    const canvas = document.getElementById('programChart');
    if (!canvas) return;

    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const values = JSON.parse(canvas.dataset.values || '[]');

    const colors = [
        getCSSVar('--chart-1'),
        getCSSVar('--chart-2'),
        getCSSVar('--chart-3'),
        getCSSVar('--chart-4'),
        getCSSVar('--chart-5'),
        getCSSVar('--chart-6'),
    ];

    new Chart(canvas, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'transparent',
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    grid: { color: getCSSVar('--chart-grid') },
                    ticks: { display: false },
                }
            },
            plugins: {
                legend: {
                    display: false,
                },
                htmlLegend: {
                    containerID: 'programChartLegend'
                },
                tooltip: {
                    backgroundColor: getCSSVar('--chart-tooltip-bg'),
                    titleColor: getCSSVar('--chart-tooltip-title'),
                    bodyColor: getCSSVar('--chart-tooltip-body'),
                    borderColor: getCSSVar('--chart-tooltip-border'),
                    borderWidth: 1,
                    cornerRadius: 6,
                }
            }
        },
        plugins: [htmlLegendPlugin]
    });
}
