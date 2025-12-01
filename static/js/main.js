/**
 * GurgelHub - Interactive Features
 * Reading progress, code copy, TOC navigation, and more
 */

(function() {
  'use strict';

  // ============================================
  // Reading Progress Bar
  // ============================================

  function initReadingProgress() {
    const progressBar = document.querySelector('.reading-progress');
    const article = document.querySelector('.markdown-body');

    if (!progressBar || !article) return;

    function updateProgress() {
      const articleRect = article.getBoundingClientRect();
      const articleTop = articleRect.top + window.scrollY;
      const articleHeight = article.offsetHeight;
      const windowHeight = window.innerHeight;
      const scrollY = window.scrollY;

      // Calculate progress based on how much of the article has been scrolled past
      const start = articleTop - windowHeight;
      const end = articleTop + articleHeight - windowHeight;
      const current = scrollY - start;
      const total = end - start;

      let progress = (current / total) * 100;
      progress = Math.max(0, Math.min(100, progress));

      progressBar.style.width = `${progress}%`;
    }

    // Throttle scroll events
    let ticking = false;
    window.addEventListener('scroll', function() {
      if (!ticking) {
        window.requestAnimationFrame(function() {
          updateProgress();
          ticking = false;
        });
        ticking = true;
      }
    });

    // Initial update
    updateProgress();
  }

  // ============================================
  // Code Block Enhancement
  // ============================================

  function initCodeBlocks() {
    const codeBlocks = document.querySelectorAll('.codehilite, .markdown-body > pre');

    codeBlocks.forEach((block, index) => {
      // Skip if already enhanced
      if (block.parentElement.classList.contains('code-block')) return;

      // Detect language from class
      let language = 'code';
      const classes = block.className.split(' ');

      for (const cls of classes) {
        if (cls.startsWith('language-')) {
          language = cls.replace('language-', '');
          break;
        }
      }

      // Try to detect from code element
      const codeEl = block.querySelector('code');
      if (codeEl) {
        const codeClasses = codeEl.className.split(' ');
        for (const cls of codeClasses) {
          if (cls.startsWith('language-')) {
            language = cls.replace('language-', '');
            break;
          }
        }
      }

      // Create wrapper
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block';

      // Create header
      const header = document.createElement('div');
      header.className = 'code-block-header';
      header.innerHTML = `
        <span class="code-block-lang">${language}</span>
        <button class="code-block-copy" data-index="${index}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>Copy</span>
        </button>
      `;

      // Wrap the code block
      block.parentNode.insertBefore(wrapper, block);
      wrapper.appendChild(header);
      wrapper.appendChild(block);

      // Add copy functionality
      const copyBtn = header.querySelector('.code-block-copy');
      copyBtn.addEventListener('click', function() {
        const code = block.querySelector('pre')?.textContent || block.textContent;
        copyToClipboard(code, copyBtn);
      });
    });
  }

  function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(function() {
      const originalHTML = button.innerHTML;
      button.classList.add('copied');
      button.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>Copied!</span>
      `;

      setTimeout(function() {
        button.classList.remove('copied');
        button.innerHTML = originalHTML;
      }, 2000);
    }).catch(function(err) {
      console.error('Failed to copy: ', err);
    });
  }

  // ============================================
  // Table of Contents
  // ============================================

  function initTableOfContents() {
    const tocWrapper = document.querySelector('.toc-wrapper');
    const tocList = document.querySelector('.toc-list');
    const article = document.querySelector('.markdown-body');

    if (!tocWrapper || !tocList || !article) return;

    const headings = article.querySelectorAll('h2, h3');

    if (headings.length < 2) {
      tocWrapper.style.display = 'none';
      return;
    }

    // Build TOC
    headings.forEach((heading, index) => {
      // Add ID if not present
      if (!heading.id) {
        heading.id = `heading-${index}`;
      }

      const li = document.createElement('li');
      li.className = `toc-item level-${heading.tagName.toLowerCase()}`;

      const a = document.createElement('a');
      a.className = 'toc-link';
      a.href = `#${heading.id}`;
      a.textContent = heading.textContent;

      li.appendChild(a);
      tocList.appendChild(li);
    });

    // Highlight current section on scroll
    const tocLinks = tocList.querySelectorAll('.toc-link');

    function updateActiveLink() {
      let currentSection = null;
      const scrollPos = window.scrollY + 150;

      headings.forEach((heading) => {
        if (heading.offsetTop <= scrollPos) {
          currentSection = heading.id;
        }
      });

      tocLinks.forEach((link) => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${currentSection}`) {
          link.classList.add('active');
        }
      });
    }

    let ticking = false;
    window.addEventListener('scroll', function() {
      if (!ticking) {
        window.requestAnimationFrame(function() {
          updateActiveLink();
          ticking = false;
        });
        ticking = true;
      }
    });

    // Smooth scroll to sections
    tocLinks.forEach((link) => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').slice(1);
        const target = document.getElementById(targetId);

        if (target) {
          const offset = 100;
          const targetPosition = target.offsetTop - offset;

          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });

          // Update URL without scrolling
          history.pushState(null, null, `#${targetId}`);
        }
      });
    });

    updateActiveLink();
  }

  // ============================================
  // External Link Handler
  // ============================================

  function initExternalLinks() {
    const links = document.querySelectorAll('.markdown-body a[href^="http"]');

    links.forEach((link) => {
      // Skip internal links
      if (link.hostname === window.location.hostname) return;

      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener noreferrer');

      // Add external link indicator
      if (!link.querySelector('.external-icon')) {
        const icon = document.createElement('span');
        icon.className = 'external-icon';
        icon.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 4px; vertical-align: middle; opacity: 0.5;">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        `;
        link.appendChild(icon);
      }
    });
  }

  // ============================================
  // Image Lightbox (Optional Enhancement)
  // ============================================

  function initImageLightbox() {
    const images = document.querySelectorAll('.markdown-body img');

    images.forEach((img) => {
      img.style.cursor = 'zoom-in';

      img.addEventListener('click', function() {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          cursor: zoom-out;
          animation: fadeIn 0.2s ease;
        `;

        const imgClone = document.createElement('img');
        imgClone.src = this.src;
        imgClone.alt = this.alt;
        imgClone.style.cssText = `
          max-width: 90%;
          max-height: 90%;
          object-fit: contain;
          border-radius: 8px;
          animation: zoomIn 0.2s ease;
        `;

        overlay.appendChild(imgClone);
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        overlay.addEventListener('click', function() {
          overlay.style.animation = 'fadeOut 0.2s ease';
          setTimeout(() => {
            document.body.removeChild(overlay);
            document.body.style.overflow = '';
          }, 150);
        });

        // Close on escape
        function handleEscape(e) {
          if (e.key === 'Escape') {
            overlay.click();
            document.removeEventListener('keydown', handleEscape);
          }
        }
        document.addEventListener('keydown', handleEscape);
      });
    });
  }

  // ============================================
  // Reading Time Calculator
  // ============================================

  function calculateReadingTime() {
    const article = document.querySelector('.markdown-body');
    const readingTimeEl = document.querySelector('.reading-time-value');

    if (!article || !readingTimeEl) return;

    const text = article.textContent || '';
    const wordsPerMinute = 200;
    const wordCount = text.trim().split(/\s+/).length;
    const readingTime = Math.ceil(wordCount / wordsPerMinute);

    readingTimeEl.textContent = `${readingTime} min read`;
  }

  // ============================================
  // Mobile Navigation Toggle
  // ============================================

  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (!toggle || !navLinks) return;

    toggle.addEventListener('click', function() {
      navLinks.classList.toggle('open');

      // Update aria-expanded
      const isOpen = navLinks.classList.contains('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ============================================
  // Keyboard Navigation
  // ============================================

  function initKeyboardNav() {
    document.addEventListener('keydown', function(e) {
      // Press 's' to focus search
      if (e.key === '/' && !isInputFocused()) {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input, .search-input-large');
        if (searchInput) {
          searchInput.focus();
        }
      }

      // Press 'h' to go home
      if (e.key === 'h' && !isInputFocused()) {
        window.location.href = '/';
      }
    });
  }

  function isInputFocused() {
    const activeEl = document.activeElement;
    return activeEl && (
      activeEl.tagName === 'INPUT' ||
      activeEl.tagName === 'TEXTAREA' ||
      activeEl.isContentEditable
    );
  }

  // ============================================
  // Smooth Fade-in Animation for Articles
  // ============================================

  function initAnimations() {
    const cards = document.querySelectorAll('.article-card');

    if (!cards.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.classList.add('fade-in-up');
          }, index * 50);
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1
    });

    cards.forEach((card) => {
      card.style.opacity = '0';
      observer.observe(card);
    });
  }

  // ============================================
  // Callout/Admonition Parser
  // ============================================

  function initCallouts() {
    const blockquotes = document.querySelectorAll('.markdown-body blockquote');

    blockquotes.forEach((bq) => {
      const firstParagraph = bq.querySelector('p');
      if (!firstParagraph) return;

      const text = firstParagraph.textContent;

      // Check for callout syntax: [!NOTE], [!TIP], [!WARNING], [!DANGER], [!INFO]
      const calloutMatch = text.match(/^\[!(NOTE|TIP|WARNING|DANGER|INFO)\]/i);

      if (calloutMatch) {
        const type = calloutMatch[1].toLowerCase();

        // Create callout div
        const callout = document.createElement('div');
        callout.className = `callout callout-${type === 'note' ? 'info' : type}`;

        // Create title
        const title = document.createElement('div');
        title.className = 'callout-title';
        title.textContent = type.charAt(0).toUpperCase() + type.slice(1);

        // Create content (remove the callout marker)
        const content = document.createElement('div');
        content.className = 'callout-content';

        // Clone blockquote children and modify first paragraph
        const children = Array.from(bq.children);
        children.forEach((child, index) => {
          if (index === 0 && child === firstParagraph) {
            const newP = document.createElement('p');
            newP.innerHTML = firstParagraph.innerHTML.replace(/^\[!(NOTE|TIP|WARNING|DANGER|INFO)\]\s*/i, '');
            if (newP.textContent.trim()) {
              content.appendChild(newP);
            }
          } else {
            content.appendChild(child.cloneNode(true));
          }
        });

        callout.appendChild(title);
        callout.appendChild(content);

        bq.parentNode.replaceChild(callout, bq);
      }
    });
  }

  // ============================================
  // Initialize All Features
  // ============================================

  function init() {
    initReadingProgress();
    initCodeBlocks();
    initTableOfContents();
    initExternalLinks();
    initImageLightbox();
    calculateReadingTime();
    initMobileNav();
    initKeyboardNav();
    initAnimations();
    initCallouts();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-run for HTMX updates
  document.body.addEventListener('htmx:afterSwap', function(e) {
    initCodeBlocks();
    initCallouts();
    initExternalLinks();
    initAnimations();
  });

  // Add CSS for lightbox animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
    @keyframes zoomIn {
      from { transform: scale(0.8); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }
  `;
  document.head.appendChild(style);

})();

