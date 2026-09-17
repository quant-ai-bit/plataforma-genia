document.addEventListener('DOMContentLoaded', () => {

    // --- THEME TOGGLE (DARK/LIGHT MODE) -----------------------
    const themeBtns = document.querySelectorAll('.theme-toggle');
    const htmlElement = document.documentElement;

    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Apply initial theme. Default is dark (HTML doesn't have light-mode class initially),
    if (savedTheme === 'light' || (!savedTheme && !prefersDark)) {
        htmlElement.classList.add('light-mode');
    }

    if (themeBtns.length > 0) {
        themeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                htmlElement.classList.toggle('light-mode');
                const isLight = htmlElement.classList.contains('light-mode');
                localStorage.setItem('theme', isLight ? 'light' : 'dark');
            });
        });
    }

    // --- MOUSE GLOW -------------------------------------------
    const mouseGlow = document.getElementById('mouse-glow');
    document.addEventListener('mousemove', (e) => {
        mouseGlow.style.setProperty('--mx', `${e.clientX}px`);
        mouseGlow.style.setProperty('--my', `${e.clientY}px`);
        if (!mouseGlow.classList.contains('visible')) {
            mouseGlow.classList.add('visible');
        }
    });

    // --- NAVBAR SCROLL ----------------------------------------
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 30) {
            navbar.classList.add('scrolled');
            navbar.classList.remove('glass');
        } else {
            navbar.classList.remove('scrolled');
            navbar.classList.add('glass');
        }
    }, { passive: true });

    // --- MOBILE MENU ------------------------------------------
    const menuBtn = document.getElementById('menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    menuBtn.addEventListener('click', () => {
        const isOpen = mobileMenu.classList.toggle('open');
        menuBtn.classList.toggle('open', isOpen);
        menuBtn.setAttribute('aria-expanded', isOpen);
    });

    // Close mobile menu on link click
    document.querySelectorAll('.mobile-link').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.remove('open');
            menuBtn.classList.remove('open');
        });
    });

    // --- REVEAL ON SCROLL -------------------------------------
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const delay = entry.target.dataset.delay || 0;
                setTimeout(() => {
                    entry.target.classList.add('active');
                }, parseInt(delay));
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // --- SMOOTH SCROLL ----------------------------------------
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const offset = target.getBoundingClientRect().top + window.scrollY - 80;
                window.scrollTo({ top: offset, behavior: 'smooth' });
            }
        });
    });

    // --- FAQ ACCORDION ----------------------------------------
    document.querySelectorAll('.faq-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const item = btn.closest('.faq-item');
            const isOpen = item.classList.contains('open');
            const icon = btn.querySelector('.faq-icon');

            if (isOpen) {
                item.classList.remove('open');
                btn.setAttribute('aria-expanded', 'false');
                if (icon) icon.textContent = '+';
            } else {
                item.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
                if (icon) icon.textContent = '-';
            }
        });
    });

    // --- COUNTER ANIMATION ------------------------------------
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.dataset.target);
                animateCounter(el, target);
                counterObserver.unobserve(el);
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.stat-num[data-target]').forEach(el => {
        counterObserver.observe(el);
    });

    function animateCounter(el, target) {
        const duration = 1800;
        const start = performance.now();
        const easeOut = (t) => 1 - Math.pow(1 - t, 3);

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            el.textContent = Math.round(easeOut(progress) * target);
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    }

    // --- ACTIVE NAV LINK ON SCROLL ----------------------------
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                navLinks.forEach(link => {
                    link.style.color = link.getAttribute('href') === `#${id}`
                        ? 'white'
                        : '';
                });
            }
        });
    }, { threshold: 0.4 });

    sections.forEach(s => sectionObserver.observe(s));

    // --- MARQUEE PAUSE ON HOVER -------------------------------
    const marqueeTrack = document.querySelector('.marquee-track');
    if (marqueeTrack) {
        marqueeTrack.addEventListener('mouseenter', () => {
            marqueeTrack.style.animationPlayState = 'paused';
        });
        marqueeTrack.addEventListener('mouseleave', () => {
            marqueeTrack.style.animationPlayState = 'running';
        });
    }

    // --- SERVICE CARDS MOUSE GLOW -----------------------------
    document.querySelectorAll('.service-card, .process-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            card.style.setProperty('--card-x', `${x}%`);
            card.style.setProperty('--card-y', `${y}%`);
        });
    });

    // --- SCROLL PROGRESS BAR ----------------------------------
    const scrollProgress = document.getElementById('scroll-progress');
    window.addEventListener('scroll', () => {
        const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        if (windowHeight > 0) {
            const scrolled = (window.scrollY / windowHeight) * 100;
            if (scrollProgress) {
                scrollProgress.style.width = scrolled + '%';
            }
        }
    }, { passive: true });

});
