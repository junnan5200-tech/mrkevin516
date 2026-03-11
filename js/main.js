/**
 * Bank of AI — Main JavaScript
 * Handles: Navigation, scroll effects, canvas animation, reveal-on-scroll
 */

(function () {
  'use strict';

  // --- Navbar scroll effect ---
  const navbar = document.getElementById('navbar');
  let lastScroll = 0;

  function handleNavbarScroll() {
    const scrollY = window.scrollY;
    navbar.classList.toggle('navbar--scrolled', scrollY > 40);
    lastScroll = scrollY;
  }

  // --- Mobile nav toggle ---
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');
  const navActions = document.querySelector('.navbar__actions');

  if (navToggle) {
    navToggle.addEventListener('click', () => {
      const isOpen = mainNav.classList.toggle('active');
      navToggle.classList.toggle('active');
      navActions.classList.toggle('active');
      navToggle.setAttribute('aria-expanded', isOpen);
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });

    mainNav.querySelectorAll('.navbar__link').forEach((link) => {
      link.addEventListener('click', () => {
        mainNav.classList.remove('active');
        navToggle.classList.remove('active');
        navActions.classList.remove('active');
        navToggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      });
    });
  }

  // --- Scroll reveal ---
  function initScrollReveal() {
    const revealEls = document.querySelectorAll(
      '.section-header, .feature-card, .protocol-block, .defi-card, ' +
      '.mcp-card, .openclaw__inner, .chain-card, .dev-card, .cta__inner, ' +
      '.hero__stats'
    );

    const grids = document.querySelectorAll(
      '.features__grid, .defi__grid, .mcp__grid, .chains__grid, .dev__grid'
    );

    revealEls.forEach((el) => el.classList.add('reveal'));
    grids.forEach((el) => el.classList.add('reveal-stagger'));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );

    revealEls.forEach((el) => observer.observe(el));
    grids.forEach((el) => observer.observe(el));
  }

  // --- Hero canvas animation (particle grid) ---
  function initHeroCanvas() {
    const canvas = document.getElementById('heroCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animFrame;
    let particles = [];
    const PARTICLE_COUNT = 60;
    const CONNECTION_DISTANCE = 150;
    let mouseX = -1000;
    let mouseY = -1000;

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.scale(dpr, dpr);
    }

    function createParticles() {
      const rect = canvas.parentElement.getBoundingClientRect();
      particles = [];
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
          x: Math.random() * rect.width,
          y: Math.random() * rect.height,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          radius: Math.random() * 1.5 + 0.5,
        });
      }
    }

    function draw() {
      const rect = canvas.parentElement.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(99, 102, 241, 0.4)';
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < CONNECTION_DISTANCE) {
            const alpha = 0.08 * (1 - dist / CONNECTION_DISTANCE);
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }

        const dxM = p.x - mouseX;
        const dyM = p.y - mouseY;
        const distM = Math.sqrt(dxM * dxM + dyM * dyM);
        if (distM < 200) {
          const alpha = 0.2 * (1 - distM / 200);
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius + 1, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(6, 182, 212, ${alpha})`;
          ctx.fill();
        }
      }

      animFrame = requestAnimationFrame(draw);
    }

    canvas.parentElement.addEventListener('mousemove', (e) => {
      const rect = canvas.parentElement.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    });

    canvas.parentElement.addEventListener('mouseleave', () => {
      mouseX = -1000;
      mouseY = -1000;
    });

    resize();
    createParticles();
    draw();

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        cancelAnimationFrame(animFrame);
        resize();
        createParticles();
        draw();
      }, 200);
    });

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      cancelAnimationFrame(animFrame);
    }
  }

  // --- Smooth scroll for anchor links ---
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // --- Active nav link highlight ---
  function initNavHighlight() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.navbar__link');

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            navLinks.forEach((link) => {
              const href = link.getAttribute('href').slice(1);
              link.classList.toggle(
                'navbar__link--active',
                href === id ||
                  (id === 'protocols' && (href === 'protocols')) ||
                  (id === 'defi-section' && href === 'defi')
              );
            });
          }
        });
      },
      { threshold: 0.3 }
    );

    sections.forEach((section) => observer.observe(section));
  }

  // --- Init ---
  window.addEventListener('scroll', handleNavbarScroll, { passive: true });
  handleNavbarScroll();

  document.addEventListener('DOMContentLoaded', () => {
    initScrollReveal();
    initHeroCanvas();
    initNavHighlight();
  });
})();
