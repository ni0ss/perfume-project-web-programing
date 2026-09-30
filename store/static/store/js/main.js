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

    const language = document.querySelector("#perfumeAssistant")?.dataset.language || document.documentElement.lang || "ar";
    const labels = language === "ar" ? {
        saved: "تم الحفظ.",
        saveFailed: "تعذر الحفظ. راجع البيانات وحاول مرة أخرى.",
        deleteConfirm: "هل تريد حذف هذا العطر؟",
        deleteFailed: "تعذر حذف العطر.",
        orderSaved: "تم تحديث حالة الطلب.",
        orderFailed: "تعذر تحديث حالة الطلب.",
        newProduct: "إضافة عطر جديد",
        editProduct: "تعديل بيانات العطر",
        loading: "أفكر في إجابة...",
        assistantFailed: "تعذر الحصول على إجابة الآن. حاول مرة أخرى.",
    } : {
        saved: "Changes saved.",
        saveFailed: "Could not save. Check the fields and try again.",
        deleteConfirm: "Delete this perfume?",
        deleteFailed: "Could not delete the perfume.",
        orderSaved: "Order status updated.",
        orderFailed: "Could not update the order.",
        newProduct: "Add a perfume",
        editProduct: "Edit perfume",
        loading: "Thinking...",
        assistantFailed: "I could not get an answer. Please try again.",
    };

    const csrfToken = () => document.querySelector("#csrfTokenSource input[name='csrfmiddlewaretoken']")?.value
        || document.querySelector("input[name='csrfmiddlewaretoken']")?.value
        || "";

    async function apiRequest(url, method, body, json = false) {
        const headers = { "X-CSRFToken": csrfToken(), "Accept": "application/json" };
        if (json) headers["Content-Type"] = "application/json";
        const response = await fetch(url, {
            method,
            credentials: "same-origin",
            headers,
            body: json ? JSON.stringify(body) : body,
        });
        let data = {};
        if (response.status !== 204) {
            try { data = await response.json(); } catch (_) { data = {}; }
        }
        if (!response.ok) {
            const message = Object.values(data).flatMap(value => Array.isArray(value) ? value : [value])
                .filter(value => typeof value === "string").join(" ");
            throw new Error(message || `HTTP ${response.status}`);
        }
        return data;
    }

    const dashboard = document.querySelector(".admin-dashboard-shell");
    const feedback = document.getElementById("dashboardFeedback");
    const showFeedback = (message, isError = false) => {
        if (!feedback) return;
        feedback.textContent = message;
        feedback.classList.toggle("is-error", isError);
    };

    if (dashboard) {
        const productApi = dashboard.dataset.apiProducts;
        const orderApi = dashboard.dataset.apiOrders;
        const dialog = document.getElementById("productEditorDialog");
        const productForm = document.getElementById("productEditorForm");
        const productId = document.getElementById("productRecordId");
        const productError = document.getElementById("productEditorError");
        const editorTitle = document.getElementById("productEditorTitle");

        const openProductEditor = (product = null) => {
            productForm.reset();
            productError.textContent = "";
            productId.value = product?.id || "";
            editorTitle.textContent = product ? labels.editProduct : labels.newProduct;
            for (const field of ["name", "name_en", "description", "description_en", "price", "stock"]) {
                productForm.elements[field].value = product?.[field.replaceAll("_", "-")] || product?.[field] || "";
            }
            productForm.elements.available.checked = product ? product.available === "true" : true;
            if (dialog?.showModal) dialog.showModal();
        };

        document.getElementById("newProductButton")?.addEventListener("click", () => openProductEditor());
        document.getElementById("newProductButtonSecondary")?.addEventListener("click", () => openProductEditor());
        document.getElementById("closeProductDialog")?.addEventListener("click", () => dialog?.close());
        document.getElementById("cancelProductDialog")?.addEventListener("click", () => dialog?.close());
        dialog?.addEventListener("click", event => {
            if (event.target === dialog) dialog.close();
        });

        document.querySelectorAll(".edit-product-button").forEach(button => {
            button.addEventListener("click", () => openProductEditor({
                id: button.dataset.id,
                name: button.dataset.name,
                name_en: button.dataset.nameEn,
                description: button.dataset.description,
                description_en: button.dataset.descriptionEn,
                price: button.dataset.price,
                stock: button.dataset.stock,
                available: button.dataset.available,
            }));
        });

        productForm?.addEventListener("submit", async event => {
            event.preventDefault();
            productError.textContent = "";
            const id = productId.value;
            const url = id ? `${productApi}${id}/` : productApi;
            const payload = new FormData(productForm);
            payload.delete("id");
            if (!productForm.elements.image.files.length) payload.delete("image");
            payload.set("available", productForm.elements.available.checked ? "true" : "false");
            try {
                await apiRequest(url, id ? "PATCH" : "POST", payload);
                dialog.close();
                window.location.reload();
            } catch (error) {
                productError.textContent = error.message || labels.saveFailed;
            }
        });

        document.querySelectorAll(".delete-product-button").forEach(button => {
            button.addEventListener("click", async () => {
                if (!window.confirm(labels.deleteConfirm)) return;
                try {
                    await apiRequest(`${productApi}${button.dataset.id}/`, "DELETE");
                    window.location.reload();
                } catch (error) {
                    showFeedback(error.message || labels.deleteFailed, true);
                }
            });
        });

        document.querySelectorAll(".dashboard-order-status").forEach(select => {
            select.dataset.previousStatus = select.value;
            select.addEventListener("change", async () => {
                const nextStatus = select.value;
                select.disabled = true;
                try {
                    await apiRequest(`${orderApi}${select.dataset.orderId}/`, "PATCH", { status: nextStatus }, true);
                    select.dataset.previousStatus = nextStatus;
                    ["pending", "processing", "shipped", "delivered", "cancelled"].forEach(status => select.classList.remove(`status-${status}`));
                    select.classList.add(`status-${nextStatus}`);
                    showFeedback(labels.orderSaved);
                } catch (error) {
                    select.value = select.dataset.previousStatus;
                    showFeedback(error.message || labels.orderFailed, true);
                } finally {
                    select.disabled = false;
                }
            });
        });

        const contentForm = document.getElementById("storeContentForm");
        contentForm?.addEventListener("submit", async event => {
            event.preventDefault();
            const content = Object.fromEntries(new FormData(contentForm).entries());
            delete content.csrfmiddlewaretoken;
            try {
                await apiRequest(dashboard.dataset.apiContent, "PATCH", content, true);
                showFeedback(labels.saved);
            } catch (error) {
                showFeedback(error.message || labels.saveFailed, true);
            }
        });
    }

    const assistant = document.getElementById("perfumeAssistant");
    const assistantToggle = document.getElementById("assistantToggle");
    const assistantPanel = document.getElementById("assistantPanel");
    const assistantMessages = document.getElementById("assistantMessages");
    const assistantForm = document.getElementById("assistantForm");
    const assistantInput = document.getElementById("assistantInput");

    const addAssistantMessage = (message, isUser = false) => {
        const bubble = document.createElement("p");
        bubble.className = `assistant-message ${isUser ? "assistant-message-user" : "assistant-message-bot"}`;
        bubble.textContent = message;
        assistantMessages.appendChild(bubble);
        assistantMessages.scrollTop = assistantMessages.scrollHeight;
        return bubble;
    };

    const closeAssistant = () => {
        assistantPanel.hidden = true;
        assistantToggle.setAttribute("aria-expanded", "false");
    };
    assistantToggle?.addEventListener("click", () => {
        assistantPanel.hidden = !assistantPanel.hidden;
        assistantToggle.setAttribute("aria-expanded", String(!assistantPanel.hidden));
        if (!assistantPanel.hidden) assistantInput.focus();
    });
    document.getElementById("assistantClose")?.addEventListener("click", closeAssistant);

    assistantForm?.addEventListener("submit", async event => {
        event.preventDefault();
        const message = assistantInput.value.trim();
        if (!message) return;
        addAssistantMessage(message, true);
        assistantInput.value = "";
        assistantInput.disabled = true;
        const pending = addAssistantMessage(labels.loading);
        try {
            const result = await apiRequest(assistant.dataset.apiUrl, "POST", {
                message,
                language: assistant.dataset.language,
            }, true);
            pending.textContent = result.answer || labels.assistantFailed;
        } catch (_) {
            pending.textContent = labels.assistantFailed;
        } finally {
            assistantInput.disabled = false;
            assistantInput.focus();
        }
    });

});
