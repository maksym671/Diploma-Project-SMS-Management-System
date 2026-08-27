/* ============================================================
   Student Management System — JavaScript
   ============================================================ */

/* Chart.js and this file live in <head>, so Turbo does not re-evaluate them.
   The IIFE + run-once guard still matter: a hard refresh is fine, but a
   service-worker or a second include would otherwise bind listeners twice. */
(function () {
    'use strict';

    if (window.__smsAppLoaded) return;
    window.__smsAppLoaded = true;

/* Turbo fires `turbo:load` on the initial load too. Chart.js lives in <head>
   (evaluated once); this file also lives there, so listeners register once.
   Page widgets re-run on every visit because the main column is replaced. */

function navKey(path) {
    if (path === '/') return 'dashboard';
    if (path.startsWith('/attendance/mark')) return 'attendance-bulk';
    if (path.startsWith('/attendance')) return 'attendance';
    if (path.startsWith('/students')) return 'students';
    if (path.startsWith('/courses')) return 'courses';
    if (path.startsWith('/enrollments')) return 'enrollments';
    if (path.startsWith('/grades')) return 'grades';
    if (path.startsWith('/teachers')) return 'teachers';
    if (path.startsWith('/profile')) return 'profile';
    return '';
}

function syncSidebar() {
    const key = navKey(location.pathname);
    document.querySelectorAll('.sidebar-link[data-nav]').forEach(link => {
        link.classList.toggle('active', link.dataset.nav === key);
    });
}

function initPageWidgets() {
    syncSidebar();
    initAlerts();
    initAnimatedCounters();
    // Prefetch snapshots should not spin up Chart.js — the real visit will.
    if (document.documentElement.hasAttribute('data-turbo-preview')) return;
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(initCharts);
    } else {
        initCharts();
    }
}

document.addEventListener('click', function (event) {
    const themeToggle = event.target.closest('#theme-toggle');
    if (themeToggle) {
        const html = document.documentElement;
        const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('sms-theme', next);
        return;
    }

    const sidebarToggle = event.target.closest('#sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebarToggle && sidebar) {
        sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
        return;
    }
    if (overlay && event.target === overlay && sidebar) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        return;
    }
    // Permanent sidebar keeps `.active` across Turbo visits — close it on nav.
    if (event.target.closest('.sidebar-link, .sidebar-user') && sidebar) {
        sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
    }

    const closeBtn = event.target.closest('.alert-close');
    if (closeBtn) {
        const alert = closeBtn.closest('.alert');
        if (!alert) return;
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(40px)';
        setTimeout(() => alert.remove(), 300);
    }
});

document.addEventListener('turbo:load', initPageWidgets);
document.addEventListener('turbo:before-render', destroyCharts);
if (typeof Turbo !== 'undefined' && typeof Turbo.setProgressBarDelay === 'function') {
    Turbo.setProgressBarDelay(80);
}

function initAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
        if (alert.dataset.smsBound) return;
        alert.dataset.smsBound = '1';
        setTimeout(() => {
            if (!alert.isConnected) return;
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(40px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
}


/* ─── Animated Counters ─────────────────────────────────────── */
function initAnimatedCounters() {
    const counters = document.querySelectorAll('.stat-value[data-target]');
    // data-target is always written with a dot (see the unlocalize filter),
    // while the displayed number follows the interface language.
    const locale = document.documentElement.lang || 'en';
    const instant = document.documentElement.hasAttribute('data-turbo-preview');

    counters.forEach(counter => {
        const target = parseFloat(counter.dataset.target);
        const isFloat = target % 1 !== 0;
        const format = new Intl.NumberFormat(locale, isFloat
            ? { minimumFractionDigits: 2, maximumFractionDigits: 2 }
            : { maximumFractionDigits: 0 });

        if (instant) {
            counter.textContent = format.format(target);
            return;
        }

        const duration = 500;
        const startTime = performance.now();

        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = format.format(target * eased);
            if (progress < 1) requestAnimationFrame(updateCounter);
        }

        requestAnimationFrame(updateCounter);
    });
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
const chartInstances = [];

function destroyCharts() {
    while (chartInstances.length) {
        chartInstances.pop().destroy();
    }
}

function createChart(canvas, config) {
    const existing = typeof Chart.getChart === 'function' ? Chart.getChart(canvas) : null;
    if (existing) existing.destroy();

    const chart = new Chart(canvas, config);
    chartInstances.push(chart);
    return chart;
}

function initCharts() {
    if (typeof Chart === 'undefined') return;
    initGradeDistributionChart();
    initCourseEnrollmentChart();
    initProgramChart();
}


function initGradeDistributionChart() {
    const canvas = document.getElementById('gradeChart');
    if (!canvas) return;

    const data = JSON.parse(canvas.dataset.grades || '{}');

    createChart(canvas, {
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

    createChart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: canvas.dataset.seriesLabel || 'Active Enrollments',
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
                    // Course codes are categories, so vertical rules add noise.
                    grid: { display: false },
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

    // Horizontal bars: programme names need the room, and bar length is read
    // far more accurately than the slice area of a pie or polar chart.
    createChart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: getCSSVar('--chart-grid'),
                        drawBorder: false,
                    },
                    ticks: {
                        color: getCSSVar('--chart-tick'),
                        font: { family: 'Inter', size: 11 },
                        precision: 0,
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: {
                        color: getCSSVar('--chart-tick'),
                        font: { family: 'Inter', size: 12 },
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
                }
            }
        }
    });
}

})();
