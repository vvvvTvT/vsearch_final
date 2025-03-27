document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");

    // 自动聚焦到搜索框
    searchInput.focus();

    // 搜索功能
    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            alert("请输入搜索内容");
            return;
        }

        window.location.href = `/search?query=${encodeURIComponent(query)}`;

    }

    // 监听按钮点击事件
    searchButton.addEventListener("click", performSearch);

    // 监听输入框的回车键事件
    searchInput.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            performSearch();
        }
    });

});

