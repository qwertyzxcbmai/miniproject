    document.addEventListener('DOMContentLoaded', function() {
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const dots = document.querySelectorAll('.slider-dot');
        const slider = document.getElementById('promoSlider');
        const totalSlides = slides.length;
        let slideInterval;

        function goToSlide(index) {
            if (index < 0) index = totalSlides - 1;
            if (index >= totalSlides) index = 0;

            currentSlide = index;
            slider.style.transform = `translateX(-${currentSlide * 100}%)`;

            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === currentSlide);
            });

            restartAutoSlide();
        }

        function startAutoSlide() {
            slideInterval = setInterval(() => {
                goToSlide(currentSlide + 1);
            }, 5000); 
        }

        function restartAutoSlide() {
            clearInterval(slideInterval);
            startAutoSlide();
        }

        document.getElementById('prevSlide').addEventListener('click', () => {
            goToSlide(currentSlide - 1);
        });

        document.getElementById('nextSlide').addEventListener('click', () => {
            goToSlide(currentSlide + 1);
        });

        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                goToSlide(index);
            });
        });

        startAutoSlide();

        slider.addEventListener('mouseenter', () => {
            clearInterval(slideInterval);
        });
        
        slider.addEventListener('mouseleave', () => {
            startAutoSlide();
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;

                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        const toTopBtn = document.getElementById('toTop');

        function toggleTopButton() {
            toTopBtn.style.display = window.scrollY > 300 ? 'block' : 'none';
        }

        window.addEventListener('scroll', toggleTopButton);
        toggleTopButton();

        toTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        if (localStorage.getItem('cookiesAccepted')) {
            document.getElementById('cookieBanner').style.display = 'none';
        }
    });

    function acceptCookies() {
        const banner = document.getElementById('cookieBanner');
        if (banner) {
            banner.style.display = 'none';
            localStorage.setItem('cookiesAccepted', 'true');
            console.log('Cookies accepted - analytics initialized');
        }
    }
