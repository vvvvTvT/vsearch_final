let allStats = {};
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get('query');
    document.title = `${query} - 搜索结果 - vvvvTvTDaBaby`;
    let originalItems = [];
    let currentFilters = { keyword: null, year: null, source: null };
    // 在 res.js 顶部添加错误处理函数
    function showError(message) {
        // 创建错误提示元素
        const errorContainer = document.createElement('div');
        errorContainer.className = 'global-error';
        errorContainer.innerHTML = `
            <div class="error-icon">⚠</div>
            <div class="error-message">${message}</div>
            <button class="error-close" onclick="this.parentElement.remove()">&times;</button>
        `;

        // 添加到页面顶部
        document.body.prepend(errorContainer);

        // 5秒后自动消失
        setTimeout(() => {
            errorContainer.remove();
        }, 5000);
    }
    function showLoading() {
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">正在加载...</div>
        `;
        document.body.appendChild(loader);
    }

    function hideLoading() {
        const loader = document.querySelector('.loading-overlay');
        if (loader) loader.remove();
    }
    // 修改后的 fetch 调用
    showLoading();
    fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误 ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const safeData = data || {};
            const results = Array.isArray(safeData.results) ? safeData.results : [];
            console.log(results)
            const items = results.map(item => ({
                title: item.title || '无标题',
                summary: item.summary || '无摘要内容',
                url: item.url || '#',
                publish_time: item.publish_time || '未知日期',
                source: item.source || '未知来源',
                score: item.score || 0,
                keywords: Array.isArray(item.keywords) ? item.keywords : []
            }));
            console.log(items);
            originalItems = items; // 保存原始数据
            filteredItems = [...originalItems]; // 筛选后数据
            // 生成完整统计
            allStats = generateStats(originalItems);
            initCharts(allStats);
            renderResults(items);


        })
        .catch(error => {
            console.error('完整错误信息:', error);
            showError(`数据加载失败: ${error.message}`);
            renderResults([]); // 确保清空结果列表
            document.getElementById('keywordChart').style.display = 'none'; // 隐藏图表
        })
        .finally(() => hideLoading());
    document.getElementById('resetBtn').addEventListener('click', () => { // 修改选择器为按钮ID
        currentFilters = { keyword: null, year: null, source: null };
        renderResults(originalItems); // 现在可以正确还原数据
        updateChartsHighlight();
    });
    // res.js 中添加
    function generateStats(items) {
        return {
            keywords: countKeywords(items),
            trends: countTrends(items),
            sources: countSources(items)
        };
    }

    function filterResults() {
        return originalItems.filter(item => {
            console.log(item.publish_time.toString())
            // 1. 处理年份筛选
            let yearMatch = true;

            if (currentFilters.year) {
                try{
                    let itemDate = item.publish_time.toString();
                    if (itemDate === "日期格式异常")
                        yearMatch = false;
                    console.log(itemDate.substring(0, 4));
                    yearMatch = itemDate.substring(0, 4) === currentFilters.year;
                } catch (e) {
                    yearMatch = false;
                }
            }
            console.log(yearMatch);
            // 2. 处理来源筛选
            const sourceMatch = !currentFilters.source ||
                item.source === currentFilters.source;

            // 3. 处理关键词筛选
            const keywordMatch = !currentFilters.keyword ||
                (item.keywords || []).includes(currentFilters.keyword);

            return yearMatch && sourceMatch && keywordMatch;
        });
    }

    function renderResults(items) {
        const container = document.getElementById('resultsList');
        container.innerHTML = items.map((item) => `
            <div class="result-card" onclick="window.open('${item.url}', '_blank')">
                <h3>${item.title}</h3>
                <div class="keywords">
                    ${(item.keywords || [])
                        .map(kw => `<span class="keyword-tag">${kw}</span>`)
                        .join('')}
                    </div>
                <p>${item.summary}</p>
                <div class="meta">
                    <span class="score">相关度：${item.score.toFixed(2)}</span>
                    <span>来源：${item.source}</span>
                    <span>发布日期：${item.publish_time}</span>
                    <span>相关关键词：${item.keywords.length}个</span>
                </div>
            </div>
        `).join('');
    }

    function initCharts(stats) {
        console.log('[图表初始化] 统计信息:', stats);
        // 初始化三个图表
        window.keywordChart = new Chart(document.getElementById('keywordChart'), {
            type: 'bar',
            data: {
                labels: stats.keywords.map(k => k[0]),
                datasets: [{
                    label: '出现频次',
                    data: stats.keywords.map(k => k[1]),
                    backgroundColor: '#4a90e2'
                }]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                onClick: (e, elements) => handleChartClick(e, elements, window.keywordChart)}
        });

        window.trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: {
                labels: stats.trends.map(t => t[0]),
                datasets: [{
                    label: '年度趋势',
                    data: stats.trends.map(t => t[1]),
                    borderColor: '#4a90e2',
                    backgroundColor: '#4a90e2',
                    tension: 0.3}]},
            options: { onClick: (e, elements) => handleChartClick(e, elements, window.trendChart) }
        });

        window.sourceChart = new Chart(document.getElementById('sourceChart'), {
            type: 'pie',
            data: {
                labels: stats.sources.map(s => s[0]),
                datasets: [{
                    data: stats.sources.map(s => s[1]),
                    backgroundColor: ['#4a90e2', '#50e3c2', '#f5a623', '#e35050', '#9013fe', '#999']
                }]},
            options: { onClick: (e, elements) => handleChartClick(e, elements, window.sourceChart) }
        });
    }
    function applyFilters() {
        console.log('当前筛选条件:', currentFilters);
        const filteredItems = filterResults();
        console.log('筛选后结果数:', filteredItems.length);
        // 强制更新页面元素
        document.querySelectorAll('.result-card').forEach(el => el.remove());

        renderResults(filteredItems);

    }
    function handleChartClick(event, elements, chart) {
        if (!elements.length) return;

        const element = elements[0];
        const value = chart.data.datasets[0].data[element.index];
        const label = chart.data.labels[element.index];

        switch (chart.canvas.id) {
            case 'keywordChart':
                currentFilters.keyword = currentFilters.keyword === label ? null : label;
                break;
            case 'trendChart':
                currentFilters.year = currentFilters.year === label ? null : label;
                break;
            case 'sourceChart':
                // 修正来源筛选逻辑
                currentFilters.source = (currentFilters.source === label) ? null : label;
                if (label === '其他来源') currentFilters.source = null;
                break;
        }
        applyFilters();
        const filtered = filterResults();
        renderResults(filtered);
        updateChartsHighlight();
    }

    function updateChartsHighlight() {
        updateChartHighlight(window.keywordChart, currentFilters.keyword);
        updateChartHighlight(window.trendChart, currentFilters.year);
        updateChartHighlight(window.sourceChart, currentFilters.source);
    }

    function updateChartHighlight(chart, filterValue) {
        chart.data.datasets.forEach(dataset => {
            dataset.backgroundColor = dataset._originalColors.map((color, index) => {
                return chart.data.labels[index] === filterValue ? '#ff6b6b' : color;
            });
        });
        chart.update();
    }

    function countKeywords(items) {
        const map = {};
        items.forEach(item => {
            // 确保处理数组类型
            (item.keywords || []).forEach(kw => {
                map[kw] = (map[kw] || 0) + 1;
            });
        });
        return Object.entries(map)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8); // 新增截取前8个
    }


    function countTrends(items) {
        const map = {};
        items.forEach(item => {
            let yearStr;
            try {
                const date = new Date(item.publish_time);
                yearStr = isNaN(date) ? '未知年份' : date.getFullYear().toString();
            } catch (e) {
                yearStr = '未知年份';
            }
            map[yearStr] = (map[yearStr] || 0) + 1;
        });
            return Object.entries(map)
        .filter(([year]) => year !== '未知年份' && !isNaN(year))
        .sort(([a], [b]) => parseInt(b, 10) - parseInt(a, 10));
    }

    function countSources(items) {
        const map = {};
        items.forEach(item => map[item.source] = (map[item.source] || 0) + 1);
        const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]);

        // 保留前五，其他归类为"其他"
        const top5 = sorted.slice(0, 5);
        const othersCount = sorted.slice(5).reduce((sum, cur) => sum + cur[1], 0);
        if (othersCount > 0) {
            top5.push(['其他来源', othersCount]);
        }
        return top5;
    }
});

