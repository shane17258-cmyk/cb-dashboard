// js/app.js
const DATA_URL = 'data.json';

const RANGE_LABELS = {
  noBid: '無委買',
  lt95: '<95',
  '95to100': '95~100',
  '100to105': '100~105',
  '105to110': '105~110',
  '110to120': '110~120',
  gte120: '>=120'
};

const RANGE_KEYS = ['noBid', 'lt95', '95to100', '100to105', '105to110', '110to120', 'gte120'];

async function loadData() {
  const resp = await fetch(DATA_URL + '?t=' + Date.now());
  return resp.json();
}

function renderStats(data) {
  const grid = document.getElementById('statsGrid');
  const items = [
    { label: '有效樣本數', value: data.validSamples, cls: 'blue' },
    { label: 'CB 總數', value: data.totalCB, cls: 'yellow' },
    { label: 'CB 委買平均價', value: data.avgBidPrice, cls: 'green' },
    { label: 'PR75 最高價', value: data.pr75, cls: '' },
    { label: 'PR90 最高價', value: data.pr90, cls: 'red' },
    { label: 'CB 平均轉換價值', value: data.avgConversionValue, cls: 'green' },
    { label: 'CB 平均轉換溢價率 (%)', value: data.avgConversionPremium, cls: 'yellow' },
    { label: '轉換價值>100 平均溢價率', value: data.conversionValueGt100AvgPremium, cls: 'blue' }
  ];
  grid.innerHTML = items.map(i =>
    `<div class="stat-card">
       <div class="label">${i.label}</div>
       <div class="value ${i.cls}">${i.value}</div>
     </div>`
  ).join('');
}

function renderRangeTable(data) {
  const r = data.bidPriceRanges;
  const counts = RANGE_KEYS.map(k => r[k].count);
  const cumPcts = RANGE_KEYS.map(k => r[k].cumPct);

  document.getElementById('rangeRow').innerHTML =
    '<tr>' +
    counts.map(c => `<td>${c}</td>`).join('') +
    `<td style="font-weight:bold;color:#ffd740;">${data.totalCB}</td>` +
    '</tr>';

  document.getElementById('cumRow').innerHTML =
    cumPcts.map((p, i) =>
      `<tr><td>${RANGE_LABELS[RANGE_KEYS[i]]}</td><td>${p}</td></tr>`
    ).join('');
}

function renderPremiumTable(data) {
  const rows = [
    ['CB 轉換價值 >= 100 數量', data.conversionValueGte100],
    ['CB 轉換價值 >= 120 數量', data.conversionValueGte120],
    ['CB 轉換溢價率 > 0% 數量', data.conversionPremiumGt0],
    ['CB 轉換溢價率 >= 50% 數量', data.conversionPremiumGte50],
    ['CB 轉換溢價率 >= 100% 數量', data.conversionPremiumGte100]
  ];
  document.getElementById('premiumRow').innerHTML =
    rows.map(([label, val]) => {
      const cls = label.includes('100%') ? ' style="color:#e94560;font-weight:bold;"' : '';
      return `<tr><td>${label}</td><td${cls}>${val}</td></tr>`;
    }).join('');
}

function renderBarChart(data) {
  const r = data.bidPriceRanges;
  const labels = ['<95', '95~100', '100~105', '105~110', '110~120', '>=120'];
  const keys = ['lt95', '95to100', '100to105', '105to110', '110to120', 'gte120'];
  const values = keys.map(k => r[k].count);

  const ctx = document.getElementById('barChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'CB 數量',
        data: values,
        backgroundColor: [
          '#5c6bc0', '#42a5f5', '#26c6da', '#66bb6a', '#ffa726', '#e94560'
        ],
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const total = values.reduce((a, b) => a + b, 0);
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return `佔比：${pct}%`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#333' },
          ticks: { color: '#a0a0a0' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#e0e0e0', font: { size: 13 } }
        }
      }
    }
  });
}

function renderLineChart(data) {
  if (!data.history || data.history.length === 0) return;

  const h = data.history.slice().reverse();
  const labels = h.map(x => x.date);

  const ctx = document.getElementById('lineChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: '委買平均價',
          data: h.map(x => x.avgBidPrice),
          borderColor: '#e94560',
          backgroundColor: 'rgba(233,69,96,0.1)',
          fill: true,
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: '平均溢價率 (%)',
          data: h.map(x => x.avgConversionPremium),
          borderColor: '#ffd740',
          backgroundColor: 'rgba(255,215,64,0.1)',
          fill: false,
          tension: 0.3,
          borderDash: [5, 5],
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#e0e0e0' } }
      },
      scales: {
        y: {
          type: 'linear',
          position: 'left',
          grid: { color: '#333' },
          ticks: { color: '#e94560' },
          title: { display: true, text: '平均價', color: '#e94560' }
        },
        y1: {
          type: 'linear',
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: '#ffd740' },
          title: { display: true, text: '溢價率 (%)', color: '#ffd740' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#e0e0e0' }
        }
      }
    }
  });
}

async function init() {
  const data = await loadData();
  document.getElementById('dataDate').textContent = data.dataDate;
  document.getElementById('dataSource').textContent = data.dataSource;
  renderStats(data);
  renderRangeTable(data);
  renderPremiumTable(data);
  renderBarChart(data);
  renderLineChart(data);
}

init();
