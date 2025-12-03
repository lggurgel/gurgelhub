/**
 * GurgelHub Comments System
 *
 * Comprehensive commenting system with:
 * - Confluence-style inline text selection comments
 * - Traditional threaded discussion comments
 * - Anonymous user identity management with localStorage persistence
 * - Real-time UI updates
 *
 * @author GurgelHub
 * @version 1.0.0
 */

(function() {
  'use strict';

  // ============================================
  // Configuration & State
  // ============================================

  const CONFIG = {
    API_BASE: '/api/v1',
    STORAGE_KEY: 'gurgelhub_user_identity',
    TOKEN_LENGTH: 64,
    MAX_COMMENT_LENGTH: 10000,
    COMMENTS_PER_PAGE: 20,
    DEBOUNCE_DELAY: 100, // Reduced from 300ms for faster response
    SELECTION_MIN_LENGTH: 3,
  };

  const state = {
    articleId: null,
    contentHash: null,
    userIdentity: null,
    currentPage: 1,
    totalComments: 0,
    hasMoreComments: false,
    selectedText: null,
    selectedRange: null,
    inlineComments: [],
    activeHighlight: null,
    ownedCommentIds: new Set(), // Track comments created by this user
  };

  // ============================================
  // Utility Functions
  // ============================================

  /**
   * Generate a cryptographically random token for anonymous user identification
   */
  function generateToken() {
    const array = new Uint8Array(CONFIG.TOKEN_LENGTH / 2);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Generate a simple hash from string (for content change detection)
   */
  function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16).padStart(16, '0');
  }

  /**
   * Format relative time (e.g., "2 hours ago")
   */
  function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    const intervals = [
      { label: 'year', seconds: 31536000 },
      { label: 'month', seconds: 2592000 },
      { label: 'week', seconds: 604800 },
      { label: 'day', seconds: 86400 },
      { label: 'hour', seconds: 3600 },
      { label: 'minute', seconds: 60 },
    ];

    for (const interval of intervals) {
      const count = Math.floor(diffInSeconds / interval.seconds);
      if (count >= 1) {
        return `${count} ${interval.label}${count > 1 ? 's' : ''} ago`;
      }
    }

    return 'just now';
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Debounce function execution
   */
  function debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  /**
   * API request helper
   */
  async function apiRequest(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (response.status === 204) {
        return { success: true };
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // ============================================
  // User Identity Management
  // ============================================

  const UserIdentity = {
    /**
     * Load user identity from localStorage or create new one
     */
    load() {
      try {
        const stored = localStorage.getItem(CONFIG.STORAGE_KEY);
        if (stored) {
          const identity = JSON.parse(stored);
          if (identity.token && identity.token.length === CONFIG.TOKEN_LENGTH) {
            state.userIdentity = identity;
            return identity;
          }
        }
      } catch (e) {
        console.error('Failed to load user identity:', e);
      }

      // Create new identity
      const newIdentity = {
        token: generateToken(),
        name: null,
        rememberName: true,
        created: new Date().toISOString(),
      };

      this.save(newIdentity);
      return newIdentity;
    },

    /**
     * Save user identity to localStorage
     */
    save(identity) {
      try {
        localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(identity));
        state.userIdentity = identity;
      } catch (e) {
        console.error('Failed to save user identity:', e);
      }
    },

    /**
     * Update user name
     */
    updateName(name, remember = true) {
      const identity = state.userIdentity || this.load();
      identity.name = name || null;
      identity.rememberName = remember;
      this.save(identity);
    },

    /**
     * Get the current token
     */
    getToken() {
      const identity = state.userIdentity || this.load();
      return identity.token;
    },

    /**
     * Get the current name
     */
    getName() {
      const identity = state.userIdentity || this.load();
      return identity.rememberName ? identity.name : null;
    },

    /**
     * Check if current user owns a comment (by ID since token not in response)
     */
    isOwner(commentId) {
      return state.ownedCommentIds.has(commentId);
    },

    /**
     * Mark a comment as owned by current user
     */
    addOwnedComment(commentId) {
      state.ownedCommentIds.add(commentId);
      // Persist to localStorage
      try {
        const owned = JSON.parse(localStorage.getItem('gurgelhub_owned_comments') || '[]');
        if (!owned.includes(commentId)) {
          owned.push(commentId);
          localStorage.setItem('gurgelhub_owned_comments', JSON.stringify(owned.slice(-100))); // Keep last 100
        }
      } catch (e) {
        console.error('Failed to persist owned comment:', e);
      }
    },

    /**
     * Load owned comments from localStorage
     */
    loadOwnedComments() {
      try {
        const owned = JSON.parse(localStorage.getItem('gurgelhub_owned_comments') || '[]');
        owned.forEach(id => state.ownedCommentIds.add(id));
      } catch (e) {
        console.error('Failed to load owned comments:', e);
      }
    },
  };

  // ============================================
  // General Comments
  // ============================================

  const GeneralComments = {
    /**
     * Initialize general comments section
     */
    async init() {
      this.bindEvents();
      await this.loadComments();
      this.populateForm();
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
      // Submit comment
      const submitBtn = document.getElementById('submit-comment');
      if (submitBtn) {
        submitBtn.addEventListener('click', () => this.submitComment());
      }

      // Character count
      const textarea = document.getElementById('comment-content');
      if (textarea) {
        textarea.addEventListener('input', () => this.updateCharCount());
        textarea.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            this.submitComment();
          }
        });
      }

      // Name input
      const nameInput = document.getElementById('commenter-name');
      if (nameInput) {
        nameInput.addEventListener('change', () => {
          const remember = document.getElementById('remember-name')?.checked ?? true;
          UserIdentity.updateName(nameInput.value, remember);
          this.updateAvatar(nameInput.value);
        });
      }

      // Remember checkbox
      const rememberCheckbox = document.getElementById('remember-name');
      if (rememberCheckbox) {
        rememberCheckbox.addEventListener('change', () => {
          const name = document.getElementById('commenter-name')?.value || null;
          UserIdentity.updateName(name, rememberCheckbox.checked);
        });
      }

      // Load more comments
      const loadMoreBtn = document.getElementById('load-more-comments');
      if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => this.loadMoreComments());
      }

      // Jump to comments
      const commentIndicator = document.getElementById('comment-count-indicator');
      if (commentIndicator) {
        commentIndicator.addEventListener('click', () => {
          document.getElementById('comments-section')?.scrollIntoView({
            behavior: 'smooth'
          });
        });
      }
    },

    /**
     * Populate form with saved user identity
     */
    populateForm() {
      const savedName = UserIdentity.getName();
      const nameInput = document.getElementById('commenter-name');
      const rememberCheckbox = document.getElementById('remember-name');

      if (nameInput && savedName) {
        nameInput.value = savedName;
        this.updateAvatar(savedName);
      }

      if (rememberCheckbox) {
        rememberCheckbox.checked = state.userIdentity?.rememberName ?? true;
      }
    },

    /**
     * Update avatar display
     */
    updateAvatar(name) {
      const avatar = document.getElementById('comment-form-avatar');
      if (avatar) {
        if (name && name.trim()) {
          avatar.textContent = name.trim().charAt(0).toUpperCase();
          avatar.classList.remove('avatar-anon');
        } else {
          avatar.textContent = '?';
          avatar.classList.add('avatar-anon');
        }
      }
    },

    /**
     * Update character count display
     */
    updateCharCount() {
      const textarea = document.getElementById('comment-content');
      const countDisplay = document.getElementById('char-count');
      if (textarea && countDisplay) {
        countDisplay.textContent = textarea.value.length;
      }
    },

    /**
     * Load comments from API
     * @param {boolean} append - Append to existing list (pagination)
     * @param {boolean} silent - Don't show loading spinner (soft refresh)
     */
    async loadComments(append = false, silent = false) {
      console.log('loadComments called:', { append, silent, page: state.currentPage });

      const loadingEl = document.getElementById('comments-loading');
      const emptyEl = document.getElementById('comments-empty');
      const listEl = document.getElementById('comments-list');
      const paginationEl = document.getElementById('comments-pagination');

      if (!listEl) {
        console.error('comments-list element not found!');
        return;
      }

      // Only show loading on initial load, not on soft refresh
      if (!append && !silent && loadingEl) {
        loadingEl.style.display = 'flex';
        if (emptyEl) emptyEl.style.display = 'none';
      }

      try {
        const data = await apiRequest(
          `/articles/${state.articleId}/comments?page=${state.currentPage}&per_page=${CONFIG.COMMENTS_PER_PAGE}`
        );

        console.log('Comments loaded:', { total: data.total, count: data.comments?.length });

        if (loadingEl) loadingEl.style.display = 'none';
        state.totalComments = data.total;
        state.hasMoreComments = (state.currentPage * CONFIG.COMMENTS_PER_PAGE) < data.total;

        // Update counts
        this.updateCommentCount(data.total);

        if (data.comments.length === 0 && !append) {
          if (emptyEl) emptyEl.style.display = 'block';
          if (paginationEl) paginationEl.style.display = 'none';
          listEl.innerHTML = '';
          return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        // Render comments
        const commentsHtml = data.comments.map(comment =>
          this.renderComment(comment)
        ).join('');

        if (append) {
          listEl.insertAdjacentHTML('beforeend', commentsHtml);
        } else {
          // Preserve scroll position on soft refresh
          const scrollY = window.scrollY;
          listEl.innerHTML = commentsHtml;
          if (silent) {
            requestAnimationFrame(() => window.scrollTo(0, scrollY));
          }
        }

        // Show/hide pagination
        if (paginationEl) paginationEl.style.display = state.hasMoreComments ? 'block' : 'none';

        // Bind reply events
        this.bindCommentEvents();

        console.log('Comments rendered successfully');

      } catch (error) {
        console.error('Failed to load comments:', error);
        if (loadingEl) loadingEl.style.display = 'none';
        if (!silent) {
          listEl.innerHTML = `
            <div class="comments-empty">
              <p style="color: var(--danger);">Failed to load comments. Please try again.</p>
            </div>
          `;
        }
      }
    },

    /**
     * Load more comments (pagination)
     */
    async loadMoreComments() {
      state.currentPage++;
      await this.loadComments(true);
    },

    /**
     * Submit a new comment
     */
    async submitComment(parentId = null, replyFormEl = null) {
      const textarea = parentId
        ? replyFormEl?.querySelector('.comment-textarea')
        : document.getElementById('comment-content');

      const nameInput = parentId
        ? replyFormEl?.querySelector('.comment-name-input')
        : document.getElementById('commenter-name');

      const content = textarea?.value?.trim();

      if (!content) {
        textarea?.focus();
        return;
      }

      const submitBtn = parentId
        ? replyFormEl?.querySelector('.btn-primary')
        : document.getElementById('submit-comment');

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Posting...';
      }

      let postSuccess = false;

      try {
        const data = {
          content,
          author_name: nameInput?.value?.trim() || null,
          author_token: UserIdentity.getToken(),
          parent_id: parentId || null,
        };

        const response = await apiRequest(`/articles/${state.articleId}/comments`, {
          method: 'POST',
          body: JSON.stringify(data),
        });

        // Track this comment as owned by current user
        if (response && response.id) {
          UserIdentity.addOwnedComment(response.id);
        }

        postSuccess = true;

        // Clear form
        if (textarea) textarea.value = '';
        this.updateCharCount();

        // Hide reply form if it was a reply
        if (replyFormEl) {
          replyFormEl.remove();
        }

      } catch (error) {
        alert('Failed to post comment. Please try again.');
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = parentId ? 'Reply' : 'Post Comment';
        }
      }

      // Soft refresh comments (no loading spinner, preserve scroll)
      if (postSuccess) {
        try {
          state.currentPage = 1;
          await this.loadComments(false, true); // silent refresh
        } catch (e) {
          console.error('Failed to reload comments:', e);
        }
      }
    },

    /**
     * Render a single comment with nested replies
     */
    renderComment(comment, depth = 0) {
      const isOwner = UserIdentity.isOwner(comment.id);
      const authorName = comment.author_name || 'Anonymous';
      const avatarLetter = comment.author_name
        ? comment.author_name.charAt(0).toUpperCase()
        : '?';
      const avatarClass = comment.author_name ? '' : 'avatar-anon';

      const repliesHtml = comment.replies && comment.replies.length > 0
        ? `<div class="comment-replies">
            ${comment.replies.map(reply => this.renderComment(reply, depth + 1)).join('')}
          </div>`
        : '';

      const actionsHtml = comment.is_deleted
        ? ''
        : `
          <div class="comment-actions">
            <button class="comment-action-btn reply-btn" data-comment-id="${comment.id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 14 4 9 9 4"></polyline>
                <path d="M20 20v-7a4 4 0 0 0-4-4H4"></path>
              </svg>
              Reply
            </button>
            ${isOwner ? `
              <button class="comment-action-btn edit-btn" data-comment-id="${comment.id}">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                Edit
              </button>
              <button class="comment-action-btn danger delete-btn" data-comment-id="${comment.id}">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                Delete
              </button>
            ` : ''}
          </div>
        `;

      return `
        <div class="comment" data-comment-id="${comment.id}">
          <div class="avatar ${depth > 0 ? 'avatar-sm' : ''} ${avatarClass}">${avatarLetter}</div>
          <div class="comment-body">
            <div class="comment-header">
              <span class="comment-author ${!comment.author_name ? 'anonymous' : ''}">${escapeHtml(authorName)}</span>
              <span class="comment-time">${formatRelativeTime(comment.created_at)}</span>
              ${comment.is_edited ? '<span class="comment-edited">(edited)</span>' : ''}
            </div>
            <div class="comment-content ${comment.is_deleted ? 'deleted' : ''}">${escapeHtml(comment.content)}</div>
            ${actionsHtml}
            ${repliesHtml}
          </div>
        </div>
      `;
    },

    /**
     * Bind events for rendered comments (reply, edit, delete)
     */
    bindCommentEvents() {
      // Reply buttons
      document.querySelectorAll('.reply-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const commentId = e.currentTarget.dataset.commentId;
          this.showReplyForm(commentId);
        });
      });

      // Edit buttons
      document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const commentId = e.currentTarget.dataset.commentId;
          this.editComment(commentId);
        });
      });

      // Delete buttons
      document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const commentId = e.currentTarget.dataset.commentId;
          this.deleteComment(commentId);
        });
      });
    },

    /**
     * Show reply form under a comment
     */
    showReplyForm(parentId) {
      // Remove any existing reply forms
      document.querySelectorAll('.reply-form').forEach(el => el.remove());

      const parentComment = document.querySelector(`[data-comment-id="${parentId}"]`);
      if (!parentComment) return;

      const savedName = UserIdentity.getName();
      const replyFormHtml = `
        <div class="reply-form">
          <div class="avatar avatar-sm ${savedName ? '' : 'avatar-anon'}">${savedName ? savedName.charAt(0).toUpperCase() : '?'}</div>
          <div style="flex: 1;">
            <input
              type="text"
              class="comment-name-input"
              placeholder="Your name (optional)"
              value="${escapeHtml(savedName || '')}"
              maxlength="100"
            >
            <textarea
              class="comment-textarea"
              placeholder="Write a reply..."
              rows="2"
              maxlength="10000"
            ></textarea>
            <div class="reply-form-actions">
              <button class="btn btn-ghost btn-sm cancel-reply-btn">Cancel</button>
              <button class="btn btn-primary btn-sm submit-reply-btn">Reply</button>
            </div>
          </div>
        </div>
      `;

      const commentBody = parentComment.querySelector('.comment-body');
      const repliesSection = commentBody.querySelector('.comment-replies');

      if (repliesSection) {
        repliesSection.insertAdjacentHTML('beforebegin', replyFormHtml);
      } else {
        commentBody.insertAdjacentHTML('beforeend', replyFormHtml);
      }

      // Bind events for the new form
      const replyForm = commentBody.querySelector('.reply-form');

      replyForm.querySelector('.cancel-reply-btn').addEventListener('click', () => {
        replyForm.remove();
      });

      replyForm.querySelector('.submit-reply-btn').addEventListener('click', () => {
        this.submitComment(parentId, replyForm);
      });

      replyForm.querySelector('.comment-textarea').focus();
    },

    /**
     * Edit a comment (in-place editing)
     */
    async editComment(commentId) {
      const commentEl = document.querySelector(`[data-comment-id="${commentId}"]`);
      if (!commentEl) return;

      const contentEl = commentEl.querySelector('.comment-content');
      const originalContent = contentEl.textContent;

      // Replace content with textarea
      const editForm = document.createElement('div');
      editForm.className = 'edit-form';
      editForm.innerHTML = `
        <textarea class="comment-textarea" rows="3">${escapeHtml(originalContent)}</textarea>
        <div class="reply-form-actions" style="margin-top: 0.5rem;">
          <button class="btn btn-ghost btn-sm cancel-edit-btn">Cancel</button>
          <button class="btn btn-primary btn-sm save-edit-btn">Save</button>
        </div>
      `;

      contentEl.style.display = 'none';
      contentEl.insertAdjacentElement('afterend', editForm);

      // Bind events
      editForm.querySelector('.cancel-edit-btn').addEventListener('click', () => {
        editForm.remove();
        contentEl.style.display = '';
      });

      editForm.querySelector('.save-edit-btn').addEventListener('click', async () => {
        const newContent = editForm.querySelector('.comment-textarea').value.trim();
        if (!newContent) return;

        const saveBtn = editForm.querySelector('.save-edit-btn');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';

        try {
          await apiRequest(`/comments/${commentId}`, {
            method: 'PUT',
            body: JSON.stringify({
              content: newContent,
              author_token: UserIdentity.getToken(),
            }),
          });

          contentEl.textContent = newContent;
          contentEl.style.display = '';
          editForm.remove();

          // Add edited indicator if not present
          const header = commentEl.querySelector('.comment-header');
          if (!header.querySelector('.comment-edited')) {
            header.insertAdjacentHTML('beforeend', '<span class="comment-edited">(edited)</span>');
          }
        } catch (error) {
          alert('Failed to save changes. Please try again.');
          saveBtn.disabled = false;
          saveBtn.textContent = 'Save';
        }
      });

      editForm.querySelector('.comment-textarea').focus();
    },

    /**
     * Delete a comment
     */
    async deleteComment(commentId) {
      if (!confirm('Are you sure you want to delete this comment?')) {
        return;
      }

      let deleteSuccess = false;

      try {
        await apiRequest(`/comments/${commentId}?author_token=${UserIdentity.getToken()}`, {
          method: 'DELETE',
        });
        deleteSuccess = true;
      } catch (error) {
        alert('Failed to delete comment. Please try again.');
      }

      // Soft refresh comments separately
      if (deleteSuccess) {
        try {
          state.currentPage = 1;
          await this.loadComments(false, true);
        } catch (e) {
          console.error('Failed to reload comments after delete:', e);
        }
      }
    },

    /**
     * Update comment count display
     */
    updateCommentCount(total) {
      const countEl = document.getElementById('general-comments-count');
      const indicatorEl = document.getElementById('comment-count-indicator');
      const totalCountEl = document.getElementById('total-comment-count');

      if (countEl) {
        countEl.textContent = `(${total})`;
      }

      if (indicatorEl && total > 0) {
        indicatorEl.style.display = 'flex';
      }

      if (totalCountEl) {
        totalCountEl.textContent = total;
      }
    },
  };

  // ============================================
  // Inline Comments (Text Selection)
  // ============================================

  const InlineComments = {
    /**
     * Initialize inline comments system
     */
    async init() {
      this.bindEvents();
      await this.loadInlineComments();
    },

    /**
     * Bind event listeners for text selection
     */
    bindEvents() {
      const articleContent = document.getElementById('article-content');
      const tooltip = document.getElementById('comment-tooltip');
      const addBtn = document.getElementById('add-inline-comment-btn');
      const sidebar = document.getElementById('inline-comments-sidebar');
      const closeSidebarBtn = document.getElementById('close-inline-sidebar');
      const modal = document.getElementById('inline-comment-modal');
      const closeModalBtn = document.getElementById('close-inline-modal');
      const cancelBtn = document.getElementById('cancel-inline-comment');
      const submitBtn = document.getElementById('submit-inline-comment');

      if (articleContent) {
        // Handle text selection - use setTimeout to ensure selection is stable
        articleContent.addEventListener('mouseup', (e) => {
          // Small delay to ensure selection is finalized
          setTimeout(() => this.handleTextSelection(e), 10);
        });

        // Hide tooltip on scroll
        document.addEventListener('scroll', () => this.hideTooltip(), { passive: true });

        // Hide tooltip on click outside
        document.addEventListener('mousedown', (e) => {
          if (!tooltip?.contains(e.target) && !e.target.classList?.contains('comment-highlight')) {
            this.hideTooltip();
          }
        });

        // Handle click on existing highlights
        articleContent.addEventListener('click', (e) => {
          const highlight = e.target.closest('.comment-highlight');
          if (highlight) {
            this.showInlineThread(highlight);
          }
        });
      }

      // Add comment button in tooltip
      if (addBtn) {
        addBtn.addEventListener('click', () => this.showCommentModal());
      }

      // Close sidebar
      if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener('click', () => this.closeSidebar());
      }

      // Close modal
      if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => this.closeModal());
      }

      if (cancelBtn) {
        cancelBtn.addEventListener('click', () => this.closeModal());
      }

      // Submit inline comment
      if (submitBtn) {
        submitBtn.addEventListener('click', () => this.submitInlineComment());
      }

      // Close modal on Escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeModal();
          this.closeSidebar();
        }
      });

      // Close modal on overlay click
      if (modal) {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            this.closeModal();
          }
        });
      }
    },

    /**
     * Handle text selection in article content
     */
    handleTextSelection(e) {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) {
        this.hideTooltip();
        return;
      }

      const text = selection.toString().trim();
      console.log('Text selection:', { length: text.length, text: text.substring(0, 50) });

      if (text.length < CONFIG.SELECTION_MIN_LENGTH) {
        this.hideTooltip();
        return;
      }

      // Check if selection is within article content
      const articleContent = document.getElementById('article-content');
      if (!articleContent) {
        console.warn('Article content element not found');
        return;
      }

      const range = selection.getRangeAt(0);
      if (!articleContent.contains(range.commonAncestorContainer)) {
        console.log('Selection not within article content');
        this.hideTooltip();
        return;
      }

      // Store selection info
      state.selectedText = text;
      state.selectedRange = range.cloneRange();

      console.log('Showing tooltip for selection');
      // Show tooltip
      this.showTooltip(range);
    },

    /**
     * Show the add comment tooltip near selection
     */
    showTooltip(range) {
      const tooltip = document.getElementById('comment-tooltip');
      if (!tooltip) {
        console.warn('Tooltip element not found');
        return;
      }

      // Get all client rects for multi-line selections
      const rects = range.getClientRects();
      console.log('Selection rects:', rects.length);

      if (rects.length === 0) {
        // Fallback to getBoundingClientRect
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) {
          console.warn('Empty selection rect');
          this.hideTooltip();
          return;
        }
        this.positionTooltip(tooltip, rect);
        return;
      }

      // Use the last rect (end of selection) for positioning
      const lastRect = rects[rects.length - 1];
      this.positionTooltip(tooltip, lastRect);
    },

    /**
     * Position the tooltip near a rect
     */
    positionTooltip(tooltip, rect) {
      // Make tooltip visible first to get its dimensions
      tooltip.style.display = 'block';
      tooltip.style.visibility = 'hidden';

      const tooltipWidth = tooltip.offsetWidth;
      const tooltipHeight = tooltip.offsetHeight;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // For fixed positioning, use viewport coordinates directly (no scroll offset)
      let left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
      left = Math.max(10, Math.min(left, viewportWidth - tooltipWidth - 10));

      // Position below selection, but flip above if near bottom of viewport
      let top = rect.bottom + 8;
      if (top + tooltipHeight > viewportHeight - 10) {
        top = rect.top - tooltipHeight - 8;
      }

      console.log('Tooltip position:', { left, top, rectBottom: rect.bottom, viewportHeight });

      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
      tooltip.style.visibility = 'visible';
    },

    /**
     * Hide the tooltip
     */
    hideTooltip() {
      const tooltip = document.getElementById('comment-tooltip');
      if (tooltip) {
        tooltip.style.display = 'none';
      }
    },

    /**
     * Show the inline comment modal
     */
    showCommentModal() {
      const modal = document.getElementById('inline-comment-modal');
      const previewEl = document.getElementById('selected-text-preview');
      const nameInput = document.getElementById('inline-commenter-name');
      const contentInput = document.getElementById('inline-comment-content');

      if (!modal || !state.selectedText) return;

      // Populate modal
      if (previewEl) {
        previewEl.textContent = state.selectedText.length > 500
          ? state.selectedText.substring(0, 500) + '...'
          : state.selectedText;
      }

      // Pre-fill name if saved
      if (nameInput) {
        nameInput.value = UserIdentity.getName() || '';
      }

      if (contentInput) {
        contentInput.value = '';
      }

      this.hideTooltip();
      modal.style.display = 'flex';

      setTimeout(() => contentInput?.focus(), 100);
    },

    /**
     * Close the inline comment modal
     */
    closeModal() {
      const modal = document.getElementById('inline-comment-modal');
      if (modal) {
        modal.style.display = 'none';
      }
      state.selectedText = null;
      state.selectedRange = null;
    },

    /**
     * Submit an inline comment
     */
    async submitInlineComment() {
      const contentInput = document.getElementById('inline-comment-content');
      const nameInput = document.getElementById('inline-commenter-name');
      const submitBtn = document.getElementById('submit-inline-comment');

      const content = contentInput?.value?.trim();

      if (!content || !state.selectedText || !state.selectedRange) {
        contentInput?.focus();
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Posting...';

      let postSuccess = false;

      try {
        // Get selector and offsets
        const range = state.selectedRange;
        const selector = this.getRangeSelector(range);
        const offsets = this.getRangeOffsets(range);

        const data = {
          content,
          author_name: nameInput?.value?.trim() || null,
          author_token: UserIdentity.getToken(),
          selector: selector,
          selected_text: state.selectedText,
          start_offset: offsets.start,
          end_offset: offsets.end,
          content_hash: state.contentHash || simpleHash(document.getElementById('article-content')?.textContent || ''),
        };

        // Save name if remember is enabled
        if (nameInput?.value) {
          UserIdentity.updateName(nameInput.value);
        }

        const response = await apiRequest(`/articles/${state.articleId}/inline-comments`, {
          method: 'POST',
          body: JSON.stringify(data),
        });

        // Track this comment as owned by current user
        if (response && response.id) {
          UserIdentity.addOwnedComment(response.id);
        }

        postSuccess = true;
        this.closeModal();

      } catch (error) {
        alert('Failed to post comment. Please try again.');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Post Comment';
      }

      // Soft refresh inline comments
      if (postSuccess) {
        await this.loadInlineComments(true);
      }
    },

    /**
     * Get a CSS selector for the range's container
     */
    getRangeSelector(range) {
      const container = range.commonAncestorContainer;
      const element = container.nodeType === Node.TEXT_NODE
        ? container.parentElement
        : container;

      // Build a simple selector
      const parts = [];
      let el = element;

      while (el && el.id !== 'article-content') {
        let selector = el.tagName.toLowerCase();
        if (el.id) {
          selector += `#${el.id}`;
        } else if (el.className) {
          selector += `.${el.className.split(' ')[0]}`;
        }

        // Add nth-child for uniqueness
        const parent = el.parentElement;
        if (parent) {
          const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
          if (siblings.length > 1) {
            const index = siblings.indexOf(el) + 1;
            selector += `:nth-of-type(${index})`;
          }
        }

        parts.unshift(selector);
        el = el.parentElement;
      }

      return '#article-content > ' + parts.join(' > ');
    },

    /**
     * Get character offsets for the range
     */
    getRangeOffsets(range) {
      const container = range.commonAncestorContainer;
      const element = container.nodeType === Node.TEXT_NODE
        ? container.parentElement
        : container;

      // Simple offset calculation
      const fullText = element.textContent || '';
      const selectedText = range.toString();
      const startOffset = fullText.indexOf(selectedText);

      return {
        start: Math.max(0, startOffset),
        end: startOffset + selectedText.length,
      };
    },

    /**
     * Load inline comments for the article
     * @param {boolean} silent - Don't log errors visibly
     */
    async loadInlineComments(silent = false) {
      try {
        const data = await apiRequest(`/articles/${state.articleId}/inline-comments`);
        state.inlineComments = data.groups || [];

        // Clear existing highlights
        document.querySelectorAll('.comment-highlight').forEach(el => {
          const text = el.textContent;
          el.replaceWith(document.createTextNode(text));
        });

        // Apply highlights for each group
        for (const group of state.inlineComments) {
          this.applyHighlight(group);
        }

        // Update total comment count
        this.updateInlineCommentCount(data.total);

        console.log('Inline comments loaded:', data.total);

      } catch (error) {
        if (!silent) {
          console.error('Failed to load inline comments:', error);
        }
      }
    },

    /**
     * Apply highlight to text in the article
     */
    applyHighlight(group) {
      try {
        const element = document.querySelector(group.selector);
        if (!element) {
          console.warn('Highlight selector not found:', group.selector);
          return;
        }

        const textContent = element.textContent || '';
        const selectedText = group.selected_text;

        // Find the text in the element
        const index = textContent.indexOf(selectedText);
        if (index === -1) {
          console.warn('Selected text not found in element:', selectedText.substring(0, 50));
          return;
        }

        // Create a range for the text
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let currentOffset = 0;
        let startNode = null;
        let startOffset = 0;
        let endNode = null;
        let endOffset = 0;

        while (walker.nextNode()) {
          const node = walker.currentNode;
          const nodeLength = node.textContent.length;

          if (!startNode && currentOffset + nodeLength > index) {
            startNode = node;
            startOffset = index - currentOffset;
          }

          if (startNode && currentOffset + nodeLength >= index + selectedText.length) {
            endNode = node;
            endOffset = index + selectedText.length - currentOffset;
            break;
          }

          currentOffset += nodeLength;
        }

        if (!startNode || !endNode) {
          console.warn('Could not find text nodes for highlight');
          return;
        }

        // Create the highlight
        const range = document.createRange();
        range.setStart(startNode, startOffset);
        range.setEnd(endNode, endOffset);

        const highlight = document.createElement('mark');
        highlight.className = `comment-highlight ${group.comments.some(c => c.is_resolved) ? 'resolved' : ''}`;
        highlight.dataset.selector = group.selector;
        highlight.dataset.commentCount = group.total_count;
        highlight.dataset.groupId = group.selector + '-' + group.start_offset;

        // surroundContents fails if selection spans multiple elements
        // Use extractContents + insertNode instead for better cross-element support
        if (startNode === endNode) {
          // Simple case: same text node
          range.surroundContents(highlight);
        } else {
          // Complex case: spans multiple nodes - wrap extracted content
          try {
            const contents = range.extractContents();
            highlight.appendChild(contents);
            range.insertNode(highlight);
          } catch (e) {
            // Fallback: just highlight the first node
            console.warn('Complex selection, highlighting first segment only');
            const simpleRange = document.createRange();
            simpleRange.setStart(startNode, startOffset);
            simpleRange.setEnd(startNode, startNode.textContent.length);
            simpleRange.surroundContents(highlight);
          }
        }

      } catch (error) {
        console.error('Failed to apply highlight:', error);
      }
    },

    /**
     * Show inline comment thread in sidebar
     */
    showInlineThread(highlightEl) {
      const selector = highlightEl.dataset.selector;
      const group = state.inlineComments.find(g => g.selector === selector);

      if (!group) return;

      // Mark highlight as active
      document.querySelectorAll('.comment-highlight').forEach(el => el.classList.remove('active'));
      highlightEl.classList.add('active');
      state.activeHighlight = highlightEl;

      // Populate sidebar
      const sidebar = document.getElementById('inline-comments-sidebar');
      const content = document.getElementById('inline-comments-content');

      if (!sidebar || !content) return;

      content.innerHTML = this.renderInlineThread(group);

      // Bind events
      this.bindInlineThreadEvents(content, group);

      sidebar.classList.add('open');
    },

    /**
     * Render inline comment thread HTML
     */
    renderInlineThread(group) {
      const commentsHtml = group.comments.map(comment =>
        this.renderInlineComment(comment)
      ).join('');

      const isAnyResolved = group.comments.some(c => c.is_resolved);

      return `
        <div class="inline-thread ${isAnyResolved ? 'resolved' : ''}">
          <div class="inline-thread-header">
            <div class="inline-thread-selection">${escapeHtml(group.selected_text)}</div>
          </div>
          <div class="inline-thread-body">
            ${commentsHtml}
          </div>
          <div class="inline-thread-actions">
            <button class="resolve-btn ${isAnyResolved ? 'resolved' : ''}" data-group-selector="${escapeHtml(group.selector)}">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              ${isAnyResolved ? 'Resolved' : 'Resolve'}
            </button>
            <button class="btn btn-sm btn-secondary add-reply-btn">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              Add Reply
            </button>
          </div>
        </div>
      `;
    },

    /**
     * Render a single inline comment
     */
    renderInlineComment(comment, depth = 0) {
      const isOwner = UserIdentity.isOwner(comment.id);
      const authorName = comment.author_name || 'Anonymous';
      const avatarLetter = comment.author_name
        ? comment.author_name.charAt(0).toUpperCase()
        : '?';

      const repliesHtml = comment.replies && comment.replies.length > 0
        ? comment.replies.map(reply => this.renderInlineComment(reply, depth + 1)).join('')
        : '';

      const actionsHtml = isOwner && !comment.is_deleted
        ? `
          <div class="comment-actions">
            <button class="comment-action-btn danger inline-delete-btn" data-comment-id="${comment.id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        `
        : '';

      return `
        <div class="comment" style="padding: 0.75rem 0; ${depth > 0 ? 'margin-left: 1rem; padding-left: 0.75rem; border-left: 2px solid var(--border-subtle);' : ''}">
          <div class="avatar avatar-sm ${!comment.author_name ? 'avatar-anon' : ''}">${avatarLetter}</div>
          <div class="comment-body">
            <div class="comment-header">
              <span class="comment-author ${!comment.author_name ? 'anonymous' : ''}" style="font-size: 0.8125rem;">${escapeHtml(authorName)}</span>
              <span class="comment-time" style="font-size: 0.75rem;">${formatRelativeTime(comment.created_at)}</span>
            </div>
            <div class="comment-content ${comment.is_deleted ? 'deleted' : ''}" style="font-size: 0.875rem;">${escapeHtml(comment.content)}</div>
            ${actionsHtml}
            ${repliesHtml}
          </div>
        </div>
      `;
    },

    /**
     * Bind events for inline thread sidebar
     */
    bindInlineThreadEvents(container, group) {
      // Add reply button
      container.querySelector('.add-reply-btn')?.addEventListener('click', () => {
        // For simplicity, we'll use the first comment's parent
        const firstComment = group.comments[0];
        this.showInlineReplyForm(container, firstComment);
      });

      // Resolve button
      container.querySelector('.resolve-btn')?.addEventListener('click', async () => {
        const firstComment = group.comments[0];
        if (UserIdentity.isOwner(firstComment.id)) {
          await this.resolveInlineComment(firstComment.id, !firstComment.is_resolved);
        } else {
          alert('Only the original commenter can resolve this thread.');
        }
      });

      // Delete buttons
      container.querySelectorAll('.inline-delete-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const commentId = btn.dataset.commentId;
          await this.deleteInlineComment(commentId);
        });
      });
    },

    /**
     * Show reply form in sidebar
     */
    showInlineReplyForm(container, parentComment) {
      const existingForm = container.querySelector('.reply-form');
      if (existingForm) {
        existingForm.remove();
        return;
      }

      const savedName = UserIdentity.getName();
      const formHtml = `
        <div class="reply-form" style="margin: 0.75rem;">
          <div class="avatar avatar-sm ${savedName ? '' : 'avatar-anon'}">${savedName ? savedName.charAt(0).toUpperCase() : '?'}</div>
          <div style="flex: 1;">
            <input type="text" class="comment-name-input" placeholder="Your name" value="${escapeHtml(savedName || '')}" style="margin-bottom: 0.5rem;">
            <textarea class="comment-textarea" placeholder="Add a reply..." rows="2"></textarea>
            <div class="reply-form-actions">
              <button class="btn btn-ghost btn-sm cancel-inline-reply">Cancel</button>
              <button class="btn btn-primary btn-sm submit-inline-reply">Reply</button>
            </div>
          </div>
        </div>
      `;

      const thread = container.querySelector('.inline-thread-body');
      thread.insertAdjacentHTML('beforeend', formHtml);

      const form = thread.querySelector('.reply-form');

      form.querySelector('.cancel-inline-reply').addEventListener('click', () => form.remove());

      form.querySelector('.submit-inline-reply').addEventListener('click', async () => {
        const content = form.querySelector('.comment-textarea').value.trim();
        const name = form.querySelector('.comment-name-input').value.trim();

        if (!content) return;

        const submitBtn = form.querySelector('.submit-inline-reply');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Posting...';

        let success = false;

        try {
          const response = await apiRequest(`/articles/${state.articleId}/inline-comments`, {
            method: 'POST',
            body: JSON.stringify({
              content,
              author_name: name || null,
              author_token: UserIdentity.getToken(),
              parent_id: parentComment.id,
              selector: parentComment.selector,
              selected_text: parentComment.selected_text,
              start_offset: parentComment.start_offset,
              end_offset: parentComment.end_offset,
              content_hash: parentComment.content_hash,
            }),
          });

          // Track ownership
          if (response && response.id) {
            UserIdentity.addOwnedComment(response.id);
          }

          success = true;
          form.remove();
        } catch (error) {
          alert('Failed to post reply. Please try again.');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Reply';
        }

        // Soft refresh separately
        if (success) {
          try {
            await this.loadInlineComments(true);
            if (state.activeHighlight) {
              this.showInlineThread(state.activeHighlight);
            }
          } catch (e) {
            console.error('Failed to reload after reply:', e);
          }
        }
      });

      form.querySelector('.comment-textarea').focus();
    },

    /**
     * Resolve/unresolve an inline comment
     */
    async resolveInlineComment(commentId, resolved) {
      let success = false;

      try {
        await apiRequest(`/inline-comments/${commentId}/resolve`, {
          method: 'POST',
          body: JSON.stringify({
            author_token: UserIdentity.getToken(),
            resolved,
          }),
        });
        success = true;
      } catch (error) {
        alert('Failed to resolve comment. Please try again.');
      }

      // Soft refresh separately
      if (success) {
        try {
          await this.loadInlineComments(true);
          if (state.activeHighlight) {
            this.showInlineThread(state.activeHighlight);
          }
        } catch (e) {
          console.error('Failed to reload after resolve:', e);
        }
      }
    },

    /**
     * Delete an inline comment
     */
    async deleteInlineComment(commentId) {
      if (!confirm('Delete this comment?')) return;

      let deleteSuccess = false;

      try {
        await apiRequest(`/inline-comments/${commentId}?author_token=${UserIdentity.getToken()}`, {
          method: 'DELETE',
        });
        deleteSuccess = true;
      } catch (error) {
        alert('Failed to delete comment. Please try again.');
      }

      // Soft refresh separately
      if (deleteSuccess) {
        try {
          await this.loadInlineComments(true);
          this.closeSidebar();
        } catch (e) {
          console.error('Failed to reload inline comments after delete:', e);
        }
      }
    },

    /**
     * Close the inline comments sidebar
     */
    closeSidebar() {
      const sidebar = document.getElementById('inline-comments-sidebar');
      if (sidebar) {
        sidebar.classList.remove('open');
      }
      document.querySelectorAll('.comment-highlight').forEach(el => el.classList.remove('active'));
      state.activeHighlight = null;
    },

    /**
     * Update inline comment count
     */
    updateInlineCommentCount(total) {
      // Could be used to show inline comment indicator
      const totalEl = document.getElementById('total-comment-count');
      if (totalEl) {
        const generalCount = state.totalComments || 0;
        totalEl.textContent = generalCount + total;
      }
    },
  };

  // ============================================
  // Main Initialization
  // ============================================

  const GurgelComments = {
    /**
     * Initialize the commenting system
     */
    init(config = {}) {
      state.articleId = config.articleId;
      state.contentHash = config.contentHash || '';

      // Load user identity and owned comments
      UserIdentity.load();
      UserIdentity.loadOwnedComments();

      // Initialize both comment systems
      GeneralComments.init();
      InlineComments.init();

      console.log('GurgelHub Comments System initialized', { articleId: state.articleId });
    },
  };

  // Export to global scope
  window.GurgelComments = GurgelComments;

})();

