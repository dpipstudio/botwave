document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

document.querySelectorAll('.scroll-fade').forEach(el => {
    observer.observe(el);
});

document.querySelectorAll('.feature-item').forEach(item => {
    item.addEventListener('mouseenter', () => {
        item.style.background = 'rgba(0, 255, 136, 0.05)';
    });

    item.addEventListener('mouseleave', () => {
        item.style.background = 'transparent';
    });
});

fetch('https://track.dpip.lol?id=botwave') // dpip.lol/privacy for the privacy policy