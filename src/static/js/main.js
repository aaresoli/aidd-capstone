// Campus Resource Hub - Main JavaScript helpers
/* global bootstrap */

document.addEventListener('DOMContentLoaded', () => {
    initAutoDismissAlerts();
    initImagePreview();
    initDatetimeMinimums();
    initDeleteConfirmations();
    initSearchReset();
    initSmoothScroll();
    initFormValidation();
    initTextareaCounters();
    initRatingStars();
    initTooltipsAndPopovers();
    initRealtimeMessaging();
    initSkipLinkFocus();
});

function initAutoDismissAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            try {
                const instance = bootstrap.Alert.getOrCreateInstance(alert);
                instance.close();
            } catch (err) {
                console.error('Failed to dismiss alert', err);
            }
        }, 5000);
    });
}

function initImagePreview() {
    const input = document.querySelector('input[type="file"][name="images"]');
    if (!input) return;

    input.addEventListener('change', event => {
        const files = Array.from(event.target.files || []);
        const previewContainer = document.getElementById('image-preview');
        if (!previewContainer) return;
        previewContainer.innerHTML = '';

        files.forEach(file => {
            if (!file.type.startsWith('image/')) return;
            const reader = new FileReader();
            reader.onload = e => {
                const wrapper = document.createElement('div');
                wrapper.className = 'image-preview-item';
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Preview';
                wrapper.appendChild(img);
                previewContainer.appendChild(wrapper);
            };
            reader.readAsDataURL(file);
        });
    });
}

function initDatetimeMinimums() {
    const inputs = document.querySelectorAll('input[type="datetime-local"]');
    if (!inputs.length) return;
    const now = new Date();
    const isoMinutes = now.toISOString().slice(0, 16);
    inputs.forEach(input => {
        input.min = isoMinutes;
    });
}

function initDeleteConfirmations() {
    document.querySelectorAll('[data-confirm-delete]').forEach(button => {
        button.addEventListener('click', event => {
            if (!window.confirm('Are you sure you want to delete this item?')) {
                event.preventDefault();
            }
        });
    });
}

function initSearchReset() {
    const searchForm = document.getElementById('resource-search-form');
    if (!searchForm) return;
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'btn btn-outline-secondary';
    clearBtn.textContent = 'Clear Filters';
    clearBtn.addEventListener('click', () => {
        searchForm.reset();
        searchForm.submit();
    });
    const submitBtn = searchForm.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.parentNode) {
        submitBtn.parentNode.insertBefore(clearBtn, submitBtn);
    }
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', event => {
            const href = anchor.getAttribute('href');
            if (!href || href === '#') return;
            const target = document.querySelector(href);
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
}

function initFormValidation() {
    document.querySelectorAll('.needs-validation').forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

function initTextareaCounters() {
    document.querySelectorAll('textarea[maxlength]').forEach(textarea => {
        const maxLength = parseInt(textarea.getAttribute('maxlength'), 10);
        if (!maxLength) return;
        const counter = document.createElement('small');
        counter.className = 'text-muted float-end';
        textarea.parentNode.appendChild(counter);

        const updateCounter = () => {
            const remaining = maxLength - textarea.value.length;
            counter.textContent = `${remaining} characters remaining`;
        };
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });
}

function initRatingStars() {
    const stars = document.querySelectorAll('.rating-stars .star');
    if (!stars.length) return;
    const ratingInput = document.querySelector('input[name="rating"]');
    if (!ratingInput) return;

    stars.forEach((star, index) => {
        star.addEventListener('click', () => {
            const rating = index + 1;
            ratingInput.value = rating;
            stars.forEach((s, i) => {
                s.classList.toggle('active', i < rating);
            });
        });
    });
}

function initTooltipsAndPopovers() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(el => new bootstrap.Popover(el));
}

function initRealtimeMessaging() {
    const threadEl = document.querySelector('[data-message-thread]');
    if (!threadEl) return;

    const feedUrl = threadEl.dataset.feedUrl;
    const currentUserId = Number(threadEl.dataset.currentUser || 0);
    let lastMessageId = Number(threadEl.dataset.lastMessageId || 0);
    const pollIntervalMs = 4000;

    const scrollToBottom = () => {
        threadEl.scrollTop = threadEl.scrollHeight;
    };

    const removeEmptyState = () => {
        const emptyState = threadEl.querySelector('.message-empty');
        if (emptyState) {
            emptyState.remove();
        }
    };

    const formatTimestamp = isoString => {
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) {
            return isoString;
        }
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short'
        }).format(date);
    };

    const appendMessage = message => {
        if (!message || !message.message_id) return;
        if (threadEl.querySelector(`[data-message-id="${message.message_id}"]`)) {
            return;
        }
        removeEmptyState();
        const wrapper = document.createElement('div');
        const isCurrentUser = message.sender_id === currentUserId;
        wrapper.className = `message-item ${isCurrentUser ? 'sent' : 'received'}`;
        wrapper.dataset.messageId = message.message_id;

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const name = document.createElement('strong');
        name.textContent = isCurrentUser ? 'You' : (message.sender_name || 'Participant');
        const time = document.createElement('span');
        time.className = 'text-muted';
        time.textContent = formatTimestamp(message.timestamp);
        meta.appendChild(name);
        meta.appendChild(time);

        const body = document.createElement('p');
        body.className = 'mb-0';
        body.textContent = message.content;

        wrapper.appendChild(meta);
        wrapper.appendChild(body);
        threadEl.appendChild(wrapper);
        lastMessageId = Math.max(lastMessageId, message.message_id);
        threadEl.dataset.lastMessageId = String(lastMessageId);
        scrollToBottom();
    };

    const fetchMessages = async () => {
        if (!feedUrl) return;
        const url = new URL(feedUrl, window.location.origin);
        if (lastMessageId) {
            url.searchParams.set('after_id', lastMessageId);
        }
        try {
            const response = await fetch(url, {
                headers: { 'Accept': 'application/json' }
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            if (payload && Array.isArray(payload.messages)) {
                payload.messages.forEach(appendMessage);
            }
        } catch (error) {
            console.warn('Message polling failed', error);
        }
    };

    // Initial state
    scrollToBottom();
    fetchMessages();
    const pollHandle = window.setInterval(fetchMessages, pollIntervalMs);

    // Enhance reply form for instant sends
    const replyForm = document.querySelector('[data-message-reply-form]');
    if (!replyForm) return;
    const textarea = replyForm.querySelector('textarea[name="content"]');

    const showInlineFeedback = message => {
        let feedback = replyForm.querySelector('.inline-message');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'alert alert-warning inline-message mt-3';
            replyForm.appendChild(feedback);
        }
        feedback.textContent = message;
        setTimeout(() => feedback.remove(), 4000);
    };

    replyForm.addEventListener('submit', async event => {
        if (!textarea) return;
        const messageText = textarea.value.trim();
        if (!messageText) {
            showInlineFeedback('Please enter a message before sending.');
            event.preventDefault();
            return;
        }

        event.preventDefault();
        const formData = new FormData(replyForm);
        try {
            const response = await fetch(replyForm.action, {
                method: 'POST',
                body: formData,
                headers: { 'Accept': 'application/json' }
            });
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            const payload = await response.json();
            if (payload.success && payload.message) {
                appendMessage(payload.message);
                textarea.value = '';
            } else if (payload.error) {
                showInlineFeedback(payload.error);
            }
        } catch (error) {
            console.error('Realtime reply failed, falling back to full submission', error);
            window.clearInterval(pollHandle);
            replyForm.submit();
        }
    });
}

function initSkipLinkFocus() {
    const skipLink = document.querySelector('.skip-link');
    const mainContent = document.getElementById('main-content');
    if (!skipLink || !mainContent) return;
    skipLink.addEventListener('click', () => {
        setTimeout(() => {
            mainContent.focus();
        }, 0);
    });
}
