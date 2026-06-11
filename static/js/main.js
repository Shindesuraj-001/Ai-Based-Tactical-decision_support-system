/*
=================================================================
  ATDSS — main.js v2.5.0
  Global JavaScript:
    • Live Clock
    • Sidebar Toggle
    • Fade-up Animations
    • Counter Animation
    • Probability Bars
    • Dashboard PDF Export
    • Keyboard Shortcuts
    • Active Nav Highlight
=================================================================
*/

// ── Topbar Live Clock ─────────────────────────────────────────
(function initClock() {
  const el = document.getElementById('topbarTime');
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }) + ' IST';
  }
  tick();
  setInterval(tick, 1000);
})();

// ── Sidebar Mobile Toggle ─────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
  const sidebar = document.getElementById('sidebar');
  const toggle  = document.querySelector('.mobile-toggle');
  if (!sidebar || !toggle) return;
  if (window.innerWidth > 768) return;
  if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// ── Intersection Observer: fade-up animations ─────────────────
(function initAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el    = entry.target;
        const delay = parseInt(el.dataset.delay) || 0;
        setTimeout(() => el.classList.add('visible'), delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('[data-anim="fade-up"]').forEach(el => observer.observe(el));
})();

// ── Number Counter Animation ──────────────────────────────────
(function initCounters() {
  function animateCounter(el, target) {
    let start = 0;
    const duration  = 1200;
    const step      = 16;
    const increment = target / (duration / step);
    const interval  = setInterval(() => {
      start += increment;
      if (start >= target) { start = target; clearInterval(interval); }
      el.textContent = Math.floor(start);
    }, step);
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        animateCounter(el, parseInt(el.dataset.target) || 0);
        observer.unobserve(el);
      }
    });
  });
  document.querySelectorAll('.counter').forEach(el => observer.observe(el));
})();

// ── Probability Bars: animate width on load ───────────────────
(function initProbBars() {
  const bars = document.querySelectorAll('.prob-bar[data-prob]');
  if (!bars.length) return;
  setTimeout(() => {
    bars.forEach(bar => {
      const prob = parseFloat(bar.dataset.prob) || 0;
      bar.style.width = Math.min(prob, 100) + '%';
    });
  }, 300);
})();

// ── Dashboard PDF Export ──────────────────────────────────────
function exportDashboardPDF() {
  if (typeof window.jspdf === 'undefined') {
    alert('PDF library not loaded. Please refresh and try again.');
    return;
  }
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  // Background
  doc.setFillColor(13, 18, 8);
  doc.rect(0, 0, 210, 297, 'F');

  // Header
  doc.setTextColor(200, 168, 75);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(20);
  doc.text('INDIAN ARMY — ATDSS v2.5.0', 105, 20, { align: 'center' });
  doc.setFontSize(13);
  doc.text('COMMAND CENTRE DASHBOARD REPORT', 105, 30, { align: 'center' });

  doc.setTextColor(200, 216, 180);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.text('Generated: ' + new Date().toLocaleString('en-IN'), 105, 40, { align: 'center' });

  // Feature list
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text('v2.5.0 ACTIVE FEATURES:', 15, 52);
  doc.setFont('helvetica', 'normal');
  const features = [
    '✓ Multi-Strategy Comparison Engine (Aggressive / Defensive / Stealth)',
    '✓ War Simulation Mode with Animated Map Playback',
    '✓ AI Learning System (Self-Improving from Mission Outcomes)',
    '✓ Real-Time Weather Integration (OpenWeatherMap API)',
    '✓ Auto-Generated PDF Mission Reports (ReportLab)',
  ];
  let fy = 60;
  features.forEach(f => { doc.text(f, 18, fy); fy += 7; });

  // Stats
  const statsData = [
    ['Total Simulations', document.querySelector('[data-target]')?.textContent || '—'],
    ['High Risk Ops',     document.querySelectorAll('[data-target]')[1]?.textContent || '—'],
    ['Avg Success',       document.querySelectorAll('.stat-value')[2]?.textContent || '—'],
    ['Ops Cleared',       document.querySelectorAll('[data-target]')[2]?.textContent || '—'],
  ];
  let y = 105;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.text('MISSION STATISTICS', 15, y); y += 8;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  statsData.forEach(([label, val]) => {
    doc.text(`${label}: ${val}`, 20, y); y += 7;
  });

  // Footer
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text('CLASSIFIED — INDIAN ARMY AI DIVISION — ATDSS v2.5.0', 105, 280, { align: 'center' });

  doc.save('ATDSS_Dashboard_Report.pdf');
}

// ── Table Row hover glow (row entry animation) ────────────────
(function initTableHover() {
  document.querySelectorAll('.table-row-anim').forEach((row, i) => {
    row.style.animationDelay = (i * 50) + 'ms';
    row.classList.add('visible');
  });
})();

// ── Keyboard shortcut: N = new simulation ────────────────────
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'n' || e.key === 'N') {
    const link = document.querySelector('a[href*="simulation"]');
    if (link) link.click();
  }
  // H = go to history
  if (e.key === 'h' || e.key === 'H') {
    const link = document.querySelector('a[href*="history"]');
    if (link) link.click();
  }
  // D = go to dashboard
  if (e.key === 'd' || e.key === 'D') {
    const link = document.querySelector('a[href*="dashboard"]');
    if (link) link.click();
  }
});

// ── Active nav link highlight ──────────────────────────────────
(function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
})();

// ── Global utility: format number with commas ─────────────────
window.fmtNum = (n) => n.toLocaleString('en-IN');

// ── Tooltip helper (title attr based) ────────────────────────
(function initTooltips() {
  document.querySelectorAll('[title]').forEach(el => {
    el.addEventListener('mouseenter', function() {
      const tip = document.createElement('div');
      tip.className   = 'atdss-tooltip';
      tip.textContent = this.getAttribute('title');
      tip.style.cssText = `
        position:fixed; z-index:9999;
        background:#1a2a10; border:1px solid #3d5a2a;
        color:#c8d8b4; font-family:'Share Tech Mono',monospace;
        font-size:0.72rem; padding:0.3rem 0.6rem; border-radius:4px;
        pointer-events:none; white-space:nowrap;
      `;
      document.body.appendChild(tip);
      const r = this.getBoundingClientRect();
      tip.style.top  = (r.bottom + 4) + 'px';
      tip.style.left = r.left + 'px';
      this._tip = tip;
    });
    el.addEventListener('mouseleave', function() {
      if (this._tip) { this._tip.remove(); this._tip = null; }
    });
  });
})();