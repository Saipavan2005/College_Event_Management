// Confirm before destructive actions (delete event, remove user, etc.)
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!confirm(form.getAttribute("data-confirm"))) {
                e.preventDefault();
            }
        });
    });
});
