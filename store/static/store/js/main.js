document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("themeToggle");
    const menuToggle = document.querySelector(".menu-toggle");
    const mainNav = document.querySelector(".main-nav");

    // Dark / light theme
    const savedTheme = localStorage.getItem("perfume-theme");
    if (savedTheme === "dark") {
        document.body.classList.add("dark-theme");
        if (themeToggle) themeToggle.textContent = "☀";
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const isDark = document.body.classList.toggle("dark-theme");
            themeToggle.textContent = isDark ? "☀" : "☾";
            localStorage.setItem("perfume-theme", isDark ? "dark" : "light");
        });
    }

    // Mobile navigation
    if (menuToggle && mainNav) {
        menuToggle.addEventListener("click", () => {
            const isOpen = mainNav.classList.toggle("is-open");
            menuToggle.setAttribute("aria-expanded", String(isOpen));
        });

        mainNav.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                mainNav.classList.remove("is-open");
                menuToggle.setAttribute("aria-expanded", "false");
            });
        });
    }

});
