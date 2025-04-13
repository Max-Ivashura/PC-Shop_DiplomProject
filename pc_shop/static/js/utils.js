// Общие утилиты (вынести в отдельный файл utils.js если нужно)
// ==============================================================
const Utils = {
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        return parts.length === 2 ? parts.pop().split(';').shift() : null;
    },

    showNotification(message, type = 'success', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification alert alert-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            animation: notificationSlide 0.3s ease-out;
        `;

        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), duration);
    },

    animateIcon(selector, animation = 'pulse') {
        const icon = document.querySelector(selector);
        if (!icon) return;

        icon.style.animation = `${animation} 0.3s ease`;
        setTimeout(() => icon.style.animation = '', 300);
    }
};