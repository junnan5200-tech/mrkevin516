/**
 * Bank of AI — Main JavaScript
 */

(function () {
  'use strict';

  // =============================================
  // Header scroll effect
  // =============================================
  const header = document.getElementById('header');

  function handleScroll() {
    if (window.scrollY > 10) {
      header.classList.add('header--scrolled');
    } else {
      header.classList.remove('header--scrolled');
    }
  }

  window.addEventListener('scroll', handleScroll, { passive: true });

  // =============================================
  // Mobile nav toggle
  // =============================================
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');

  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      navMenu.classList.toggle('is-open');
      navToggle.classList.toggle('is-active');
    });

    document.addEventListener('click', (e) => {
      if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
        navMenu.classList.remove('is-open');
        navToggle.classList.remove('is-active');
      }
    });
  }

  // =============================================
  // Scroll-triggered animations
  // =============================================
  const animatedElements = document.querySelectorAll('[data-animate]');

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const delay = parseInt(entry.target.dataset.delay || '0', 10);
          setTimeout(() => {
            entry.target.classList.add('is-visible');
          }, delay);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  animatedElements.forEach((el) => observer.observe(el));

  // =============================================
  // Counter animation for stats
  // =============================================
  function animateCounter(el) {
    const target = parseInt(el.dataset.count, 10);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 2000;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * target);

      el.textContent = prefix + current.toLocaleString() + (progress >= 1 ? suffix.replace('+', '+') : '');

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = prefix + target.toLocaleString() + suffix;
      }
    }

    requestAnimationFrame(update);
  }

  const statElements = document.querySelectorAll('[data-count]');
  const statsObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          statsObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  statElements.forEach((el) => statsObserver.observe(el));

  // =============================================
  // Search hint tags auto-fill
  // =============================================
  const hintTags = document.querySelectorAll('.hero__hint-tag');
  const searchInput = document.querySelector('.hero__search-input');

  hintTags.forEach((tag) => {
    tag.addEventListener('click', () => {
      if (searchInput) {
        searchInput.value = tag.textContent;
        searchInput.focus();
      }
    });
  });

  // =============================================
  // Search form submission
  // =============================================
  const searchBtn = document.querySelector('.hero__search-btn');

  if (searchBtn && searchInput) {
    searchBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const query = searchInput.value.trim();
      if (query) {
        console.log('Search query:', query);
      }
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        searchBtn.click();
      }
    });
  }

  // =============================================
  // Smooth scrolling for anchor links
  // =============================================
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href === '#') return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
})();
