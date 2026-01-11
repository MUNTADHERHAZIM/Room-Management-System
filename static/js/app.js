// Room Management System - JavaScript

// Auto-refresh dashboard every minute
document.addEventListener('DOMContentLoaded', function () {
    // Auto-refresh for dashboard
    const dashboardContent = document.getElementById('dashboard-content');
    if (dashboardContent) {
        setInterval(function () {
            htmx.trigger(dashboardContent, 'refresh');
        }, 60000);
    }

    // Toast auto-dismiss
    const toasts = document.querySelectorAll('[data-toast]');
    toasts.forEach(function (toast) {
        setTimeout(function () {
            toast.style.opacity = '0';
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 5000);
    });
});

// Dynamic department loading based on college selection
function loadDepartments(collegeId, targetSelect) {
    if (!collegeId) {
        targetSelect.innerHTML = '<option value="">جميع الأقسام</option>';
        return;
    }

    fetch(`/api/departments/${collegeId}/`)
        .then(response => response.json())
        .then(data => {
            let options = '<option value="">جميع الأقسام</option>';
            data.forEach(dept => {
                options += `<option value="${dept.id}">${dept.name}</option>`;
            });
            targetSelect.innerHTML = options;
        });
}

// Print function
function printPage() {
    window.print();
}

// Confirmation dialog
function confirmDelete(message) {
    return confirm(message || 'هل أنت متأكد من الحذف؟');
}
