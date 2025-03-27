// static/js/onlineres.js
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get('query');
    let originalItems = [];
    let currentFilters = { domain: null, freshness: null };

    // 修改后的API端点
    showLoading();
    fetch(`/api/online_search?q=${encodeURIComponent(query)}`)
        .then(handleResponse)
        .then(processOnlineData)
        .catch(handleOnlineError)
        .finally(hideLoading);

    function processOnlineData(data) {
        const items = data.results.map(item => ({
            title: item.title,
            snippet: item.snippet,
            url: item.url,
            domain: extractDomain(item.url),
            freshness: calculateFreshness(item.date),
            keywords: extractOnlineKeywords(item.snippet)
        }));

        originalItems = items;
        allStats = generateOnlineStats(items);
        initOnlineCharts(allStats);
        renderOnlineResults(items);
    }

    function extractOnlineKeywords(text) {
        // 增强的关键词提取逻辑
        const keywords = text.match(/[\u4e00-\u9fa5]{2,5}|[A-Za-z0-9-]{3,}/g) || [];
        return [...new Set(keywords)]
            .sort(() => Math.random() - 0.5) // 随机排序
            .slice(0, 5);
    }

    function generateOnlineStats(items) {
        return {
            domains: countDomains(items),
            freshness: countFreshness(items)
        };
    }

    function initOnlineCharts(stats) {
        // 域名分布图
        window.domainChart = new Chart(document.getElementById('domainChart'), {
            type: 'doughnut',
            data: {
                labels: stats.domains.map(d => d[0]),
                datasets: [{
                    data: stats.domains.map(d => d[1]),
                    backgroundColor: ['#4a90e2', '#50e3c2', '#f5a623', '#e35050', '#9013fe']
                }]
            },
            options: chartClickHandler('domain')
        });

        // 新鲜度图表
        window.freshnessChart = new Chart(document.getElementById('freshnessChart'), {
            type: 'bar',
            data: {
                labels: ['24小时内', '一周内', '一月内', '一年内', '更早'],
                datasets: [{
                    label: '内容时效性',
                    data: stats.freshness,
                    backgroundColor: '#4a90e2'
                }]
            },
            options: chartClickHandler('freshness')
        });
    }

    function chartClickHandler(filterType) {
        return {
            onClick: (e, elements) => {
                if (!elements.length) return;
                const index = elements[0].index;
                const label = this.data.labels[index];
                currentFilters[filterType] = currentFilters[filterType] === label ? null : label;
                applyOnlineFilters();
            }
        };
    }

    function applyOnlineFilters() {
        const filtered = originalItems.filter(item => {
            const domainMatch = !currentFilters.domain ||
                item.domain === currentFilters.domain;
            const freshnessMatch = !currentFilters.freshness ||
                item.freshness === currentFilters.freshness;
            return domainMatch && freshnessMatch;
        });

        renderOnlineResults(filtered);
        highlightCharts();
    }

    function renderOnlineResults(items) {
        const container = document.getElementById('resultsList');
        container.innerHTML = items.map(item => `
            <div class="result-card" onclick="window.open('${item.url}', '_blank')">
                <div class="domain-badge">${item.domain}</div>
                <h3>${item.title}</h3>
                <p class="snippet">${highlightQuery(item.snippet, query)}</p>
                <div class="meta">
                    <span class="freshness">${item.freshness}</span>
                    <span class="url">${shortenUrl(item.url)}</span>
                </div>
            </div>
        `).join('');
    }

    // 实用工具函数
    function extractDomain(url) {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return '未知域名';
        }
    }

    function calculateFreshness(date) {
        // 假设date是ISO格式字符串
        const diffDays = Math.floor((new Date() - new Date(date)) / (1000*60*60*24));
        if (diffDays < 1) return '24小时内';
        if (diffDays < 7) return '一周内';
        if (diffDays < 30) return '一月内';
        if (diffDays < 365) return '一年内';
        return '更早';
    }

    function highlightQuery(text, query) {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    function shortenUrl(url) {
        return url.replace(/https?:\/\/(www\.)?/, '').slice(0, 40) + '...';
    }

    // 重置按钮逻辑
    document.getElementById('onlineResetBtn').addEventListener('click', () => {
        currentFilters = { domain: null, freshness: null };
        renderOnlineResults(originalItems);
        highlightCharts();
    });

    function countDomains(items) {
        const counts = items.reduce((acc, { domain }) => {
            acc[domain] = (acc[domain] || 0) + 1;
            return acc;
        }, {});

        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
    }

    function countFreshness(items) {
        const periods = ['24小时内', '一周内', '一月内', '一年内', '更早'];
        return periods.map(p =>
            items.filter(item => item.freshness === p).length
        );
    }
});
