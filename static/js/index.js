// Плавний скрол
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

function closeBanner() {
    const banner = document.getElementById('promoBanner');
    banner.style.display = 'none';
}

// Optional: Show banner again after 24 hours using localStorage
// This is a simple implementation without expiration
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('bannerClosed')) {
        document.getElementById('promoBanner').style.display = 'none';
    }
});

function closeBanner() {
    const banner = document.getElementById('promoBanner');
    banner.style.display = 'none';
    localStorage.setItem('bannerClosed', 'true');
}