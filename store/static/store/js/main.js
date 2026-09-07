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

    // Temporary visual feedback for cart button.
    // We will replace this with the real Django cart backend in the cart phase.
    document.querySelectorAll(".product-action").forEach(button => {
        button.addEventListener("click", () => {
            const originalText = button.textContent;
            button.textContent = document.documentElement.lang === "ar" ? "قريباً" : "Coming soon";
            button.disabled = true;

            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 1200);
        });
    });
});
