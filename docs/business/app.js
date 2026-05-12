// AgentForge — Business Pitch Deck
// Slide navigation: progress dots + keyboard arrows + section separators

const slides = document.querySelectorAll('.slide');
const dotsContainer = document.getElementById('navDots');

// Build progress dots, inserting a separator before each section divider
slides.forEach((slide, i) => {
  if (i > 0 && slide.classList.contains('divider')) {
    const sep = document.createElement('div');
    sep.className = 'nav-dot separator';
    dotsContainer.appendChild(sep);
  }
  const dot = document.createElement('button');
  dot.className = 'nav-dot';
  dot.setAttribute('aria-label', `Slide ${i}`);
  dot.addEventListener('click', () => slide.scrollIntoView({ behavior: 'smooth' }));
  dotsContainer.appendChild(dot);
});

// Highlight active dot as slides scroll into view
const dots = dotsContainer.querySelectorAll('.nav-dot:not(.separator)');
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const idx = Array.from(slides).indexOf(entry.target);
        dots.forEach((d, i) => d.classList.toggle('active', i === idx));
      }
    });
  },
  { threshold: 0.5 }
);
slides.forEach((s) => observer.observe(s));

// Keyboard navigation (arrow keys, page up/down, space)
document.addEventListener('keydown', (e) => {
  const current = Array.from(slides).findIndex((s) => {
    const r = s.getBoundingClientRect();
    return r.top >= -window.innerHeight / 2 && r.top < window.innerHeight / 2;
  });

  if (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ') {
    e.preventDefault();
    slides[Math.min(current + 1, slides.length - 1)]?.scrollIntoView({ behavior: 'smooth' });
  }
  if (e.key === 'ArrowUp' || e.key === 'PageUp') {
    e.preventDefault();
    slides[Math.max(current - 1, 0)]?.scrollIntoView({ behavior: 'smooth' });
  }
});
