// static/js/online.js
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");

    searchInput.focus();

    function performOnlineSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            alert("请输入要搜索的内容");
            return;
        }

        // 跳转到在线搜索结果页
        window.location.href = `/onlineres?query=${encodeURIComponent(query)}`;
    }

    searchButton.addEventListener("click", performOnlineSearch);
    searchInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            performOnlineSearch();
        }
    });
});
// 在online.js中添加
window.__gcse || (window.__gcse = {});
window.__gcse.searchCallbacks = {
    web: {
        ready: function (result) {
            document.querySelector('.main-content').classList.remove('searching');
            // 这里可以添加自定义分析逻辑
            analyzeResults(result);
        }
    }
};

function analyzeResults(results) {
    // 实现自定义结果分析逻辑
    console.log('搜索完成:', results);
}

function showError(message = '无法访问Google搜索服务') {
    document.querySelector('.error-overlay').style.display = 'block';
    const errorBox = document.querySelector('.cse-error');
    errorBox.querySelector('p').textContent = message;
    errorBox.style.display = 'block';
}

function hideError() {
    document.querySelector('.error-overlay').style.display = 'none';
    document.querySelector('.cse-error').style.display = 'none';
}

function createSaveButton(resultElement) {
    const btn = document.createElement('button');
    btn.className = 'save-btn';
    btn.innerHTML = '💾 保存';

    btn.onclick = function () {
        // 获取标题中的<b>标签内容作为关键词
        const titleElement = resultElement.querySelector('.gs-title');
        const snippetElement = resultElement.querySelector('.gs-snippet');
        const urlElement = resultElement.querySelector('.gs-visibleUrl');
        const keywords = Array.from(titleElement.querySelectorAll('b'))
            .map(b => b.textContent)
            .join(',');
        const resultData = {
            title: titleElement?.textContent?.replace(/›/g, '').trim() || '',
            content: snippetElement?.textContent || '',
            url: titleElement?.href || '',
            source: urlElement?.textContent || '',
            keywords: keywords
        };
        const xmlContent = `<?xml version='1.0' encoding='utf-8'?>
<doc>
    <search_word>${escapeXML(resultData.keywords)}</search_word>
    <title>${escapeXML(resultData.title)}</title>
    <publish_time>${getPublishTime(resultElement)}</publish_time>
    <summary>${escapeXML(resultData.content)}</summary>
    <source>${escapeXML(resultData.source)}</source>
    <url>${escapeXML(resultData.url)}</url>
</doc>`;

        downloadXML(xmlContent, `search_${keywords || 'result'}_${Date.now()}.xml`);
    };

    return btn;
}

function escapeXML(str) {
    return str ? str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;') : '';
}

function getPublishTime(result) {
    try {
        return result.richSnippet?.metatags?.date ||
            result.richSnippet?.cseDate ||
            new Date().toISOString().split('T')[0];
    } catch {
        return new Date().toISOString().split('T')[0];
    }
}

function downloadXML(content, filename) {
    const blob = new Blob([content], {type: 'application/xml'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 100);
}

// 搜索结果渲染后插入按钮
document.addEventListener('DOMContentLoaded', () => {
    // 动态加载CSE
    const loadCSE = () => {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.async = true;
            script.src = 'https://cse.google.com/cse.js?cx=7326f1ded5ef6410e';

            // 成功加载
            script.onload = () => {
                console.log('CSE loaded');
                let renderAttempts = 0;

                const checkRender = () => {
                    const cseContainer = document.querySelector('.gsc-control-cse');
                    if (cseContainer) {
                        cseContainer.style.display = 'block';
                        resolve();
                    } else if (renderAttempts < 20) { // 最多尝试1秒
                        renderAttempts++;
                        setTimeout(checkRender, 50);
                    } else {
                        console.error('CSE容器在1秒后仍未渲染');
                        reject(new Error('CSE渲染超时'));
                    }
                };

                checkRender();
            };


            // 错误捕获（包括ERR_CONNECTION_REFUSED）
            script.onerror = (error) => {
                showError(`连接被拒绝 (${error.type})`);
            };
            document.head.querySelectorAll('script[src*="cse.google.com"]').forEach(s => s.remove());

            document.head.appendChild(script);

            // 15秒超时捕获
            setTimeout(() => {
                if (!window.__gcse) {
                    script.onerror(new Error('Timeout'));
                }
            }, 15000);
        });
    };

    // 初始化加载
    loadCSE().catch(error => {
        console.warn('搜索服务初始化失败:', error);
        showError(`连接被拒绝 (${error.type})`);
    });
    const observer = new MutationObserver(() => {
        document.querySelectorAll('.gsc-webResult').forEach(resultElement => {
            if (!resultElement.querySelector('.save-btn')) {
                const extraTitle = resultElement.querySelector('.gsc-table-result .gs-title');
                if (extraTitle) extraTitle.remove();
                const saveBtn = createSaveButton(resultElement);
                const thumbnailDiv = resultElement.querySelector('.gsc-thumbnail-inside');
                if (thumbnailDiv) {
                    thumbnailDiv.appendChild(saveBtn);
                }
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
    // 自定义搜索交互逻辑
document.addEventListener('DOMContentLoaded', function() {
// 绑定自定义按钮点击事件
document.getElementById('customSearchButton').addEventListener('click', function () {
    const input = document.querySelector('.gsc-input');
    if (input) input.focus();
});

    // 重试按钮点击事件
document.querySelector('.retry-btn').addEventListener('click', () => {
    hideError();
    loadCSE(); // 重新执行加载逻辑
});

    // 点击遮罩层关闭
    document.querySelector('.error-overlay').addEventListener('click', hideError);
        // 监听键盘事件
    document.querySelector('.gsc-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
        // 添加自定义加载状态
        document.querySelector('.main-content').classList.add('searching');
        }
    });
});
