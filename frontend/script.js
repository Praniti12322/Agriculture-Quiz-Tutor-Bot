document.addEventListener('DOMContentLoaded', () => {

    // ── JWT Username Decode ──────────────────────────────────────────
    function getUsernameFromToken() {
        const token = localStorage.getItem('token');
        if (!token) return null;
        try {
            let base64Url = token.split('.')[1];
            let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            let padding = base64.length % 4;
            if (padding) base64 += '='.repeat(4 - padding);
            const payload = JSON.parse(atob(base64));
            return payload.sub;
        } catch (e) {
            console.error("JWT Decode Error:", e);
            return null;
        }
    }

    const savedName = getUsernameFromToken() || 'Agri-Student';
    document.querySelectorAll('.user-name-display').forEach(el => { el.innerText = savedName; });

    // ── Auth Handlers ────────────────────────────────────────────────
    const loginForm  = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const logoutBtn  = document.getElementById('logoutBtn');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const btn      = document.getElementById('loginBtn');
            const alertBox = document.getElementById('loginAlert');
            btn.innerHTML  = '<div class="spinner"></div>';
            alertBox.style.display = 'none';
            try {
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);
                const res  = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('token', data.access_token);
                    window.location.href = '/dashboard.html';
                } else {
                    throw new Error(data.detail || 'Login failed');
                }
            } catch (err) {
                alertBox.className = 'alert error';
                alertBox.innerText = err.message;
            } finally {
                btn.innerText = 'Start Learning';
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const email    = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const btn      = document.getElementById('signupBtn');
            const alertBox = document.getElementById('signupAlert');
            btn.innerHTML  = '<div class="spinner"></div>';
            alertBox.style.display = 'none';
            try {
                const res  = await fetch('/signup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, email, password }) });
                const data = await res.json();
                if (res.ok) {
                    alertBox.className = 'alert success';
                    alertBox.innerText = 'Account created successfully! Redirecting...';
                    setTimeout(() => window.location.href = '/login.html', 1500);
                } else {
                    throw new Error(data.detail || 'Signup failed');
                }
            } catch (err) {
                alertBox.className = 'alert error';
                alertBox.innerText = err.message;
            } finally {
                btn.innerText = 'Sign Up';
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/login.html';
        });
    }

    // ── Markdown Renderer ────────────────────────────────────────────
    function renderMarkdown(text) {
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
            .replace(/^[-•]\s(.+)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n?)+/g, match => `<ul>${match}</ul>`)
            .replace(/\n/g, '<br>');
    }

    // ── Text to Speech Utilities ─────────────────────────────────────
    let speechSynth = window.speechSynthesis;
    let currentUtterance = null;

    function speakText(text) {
        if (!speechSynth) return;
        stopSpeech();
        currentUtterance = new SpeechSynthesisUtterance(text);
        currentUtterance.rate = 0.95;
        currentUtterance.pitch = 1.0;
        speechSynth.speak(currentUtterance);
    }

    function stopSpeech() {
        if (speechSynth && speechSynth.speaking) {
            speechSynth.cancel();
        }
    }

    // ── Chat Utilities ───────────────────────────────────────────────
    const chatContent    = document.getElementById('chatContent');
    const scoreDisplay   = document.getElementById('scoreDisplay');
    const mediaDisplay   = document.getElementById('mediaDisplayArea');
    const typeBadge      = document.getElementById('currentQTypeBadge');

    let currentQuestion  = '';
    let currentContext   = '';
    let currentQType     = 'text';
    let score = 0;
    let total = 0;

    const BADGE_CONFIG = {
        text:  { label: '🔤 Text',  cls: 'badge-text'  },
        image: { label: '🖼️ Image', cls: 'badge-image' },
        audio: { label: '🎵 Audio', cls: 'badge-audio' },
        video: { label: '🎬 Video', cls: 'badge-video' },
    };

    function showBadge(q_type) {
        const cfg = BADGE_CONFIG[q_type] || BADGE_CONFIG.text;
        typeBadge.innerText = cfg.label;
        typeBadge.className = `q-badge ${cfg.cls}`;
        typeBadge.style.display = 'inline-block';
    }

    function showMedia(q_type, media_url) {
        // Legacy function — now media is handled inside addMessage
        return;
    }

    function createMediaElement(q_type, media_url) {
        if (!media_url) return null;
        const mediaContainer = document.createElement('div');
        mediaContainer.className = 'media-display';
        mediaContainer.style.display = 'block';
        mediaContainer.style.borderTop = 'none'; // Inside message, no top border needed
        mediaContainer.style.background = 'transparent';
        mediaContainer.style.padding = '0.5rem 0';

        if (q_type === 'image') {
            const img = document.createElement('img');
            img.src = media_url;
            img.alt = 'Quiz Image';
            img.className = 'media-img';
            img.style.marginBottom = '0';
            mediaContainer.appendChild(img);
        } else if (q_type === 'audio') {
            const audio = document.createElement('audio');
            audio.src = media_url;
            audio.controls = true;
            audio.className = 'media-audio';
            mediaContainer.appendChild(audio);
        } else if (q_type === 'video') {
            const video = document.createElement('video');
            video.src = media_url;
            video.controls = true;
            video.className = 'media-video';
            mediaContainer.appendChild(video);
        }
        return mediaContainer;
    }

    function addMessage(text, type, options = null, animate = false, q_type = null, media_url = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}`;
        const textSpan = document.createElement('div');
        textSpan.className = 'msg-text';

        if (animate) {
            msgDiv.appendChild(textSpan);
            chatContent.appendChild(msgDiv);
            chatContent.scrollTop = chatContent.scrollHeight;
            let i = 0, typed = '';
            const interval = setInterval(() => {
                if (i < text.length) {
                    typed += text[i++];
                    textSpan.innerHTML = renderMarkdown(typed);
                    chatContent.scrollTop = chatContent.scrollHeight;
                } else {
                    clearInterval(interval);
                    // After text is typed, add media if any
                    if (media_url) {
                        const mediaEl = createMediaElement(q_type, media_url);
                        if (mediaEl) msgDiv.appendChild(mediaEl);
                    }
                    if (options && options.length > 0) appendOptions(msgDiv, options);
                    chatContent.scrollTop = chatContent.scrollHeight;
                }
            }, 10);
            return msgDiv;
        }

        textSpan.innerHTML = renderMarkdown(text);
        msgDiv.appendChild(textSpan);
        
        // Add Audio Controls if it's an AI-generated scenario (no media_url)
        if (q_type === 'audio' && !media_url) {
            const audioUI = document.createElement('div');
            audioUI.className = 'audio-control-bar';
            const playBtn = document.createElement('button');
            playBtn.className = 'play-btn speak-trigger';
            playBtn.innerHTML = '🔊 Hear AI Scenario';
            playBtn.onclick = () => speakText(text);
            audioUI.appendChild(playBtn);
            msgDiv.appendChild(audioUI);
        }

        // Add Media (Images/Video/REAL Audio files) between text and options
        // Only show media element if media_url exists
        if (media_url) {
            const mediaEl = createMediaElement(q_type, media_url);
            if (mediaEl) msgDiv.appendChild(mediaEl);
        }

        if (options && options.length > 0) appendOptions(msgDiv, options);
        chatContent.appendChild(msgDiv);
        chatContent.scrollTop = chatContent.scrollHeight;
        return msgDiv;
    }

    function appendOptions(container, options) {
        const optsDiv = document.createElement('div');
        optsDiv.className = 'options-container';
        options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerText = opt;
            btn.onclick = () => submitAnswer(opt);
            optsDiv.appendChild(btn);
        });
        container.appendChild(optsDiv);
    }

    function showTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'message eval-msg';
        div.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        chatContent.appendChild(div);
        chatContent.scrollTop = chatContent.scrollHeight;
        return div;
    }

    // ── Question Type Selector ───────────────────────────────────────
    let selectedType = 'random';
    const typeBtns = document.querySelectorAll('.q-type-btn');
    typeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            typeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedType = btn.dataset.type;
        });
    });

    // ── File Upload Logic ────────────────────────────────────────────
    const fileInput       = document.getElementById('mediaFileInput');
    const uploadTrigger   = document.getElementById('uploadTriggerBtn');
    const uploadSubmitBtn = document.getElementById('uploadSubmitBtn');
    const uploadFileName  = document.getElementById('uploadFileName');
    const uploadZone      = document.getElementById('uploadZone');

    let selectedFile = null;

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            selectedFile = fileInput.files[0];
            if (selectedFile) {
                uploadFileName.innerText = `📎 ${selectedFile.name}`;
                uploadSubmitBtn.style.display = 'inline-block';
            }
        });
    }

    // Drag and drop support
    if (uploadZone) {
        uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) {
                selectedFile = file;
                uploadFileName.innerText = `📎 ${file.name}`;
                uploadSubmitBtn.style.display = 'inline-block';
            }
        });
    }

    if (uploadSubmitBtn) {
        uploadSubmitBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            const token = localStorage.getItem('token');
            if (!token) { window.location.href = '/login.html'; return; }

            uploadSubmitBtn.disabled = true;
            uploadSubmitBtn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>';

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const res = await fetch('/upload-media', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                });
                if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login.html'; return; }
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Upload failed');
                }
                const data = await res.json();
                renderQuestion(data);
                uploadFileName.innerText = '';
                uploadSubmitBtn.style.display = 'none';
                selectedFile = null;
                if (fileInput) fileInput.value = '';
            } catch (err) {
                addMessage(`❌ Upload error: ${err.message}`, 'bot-msg');
            } finally {
                uploadSubmitBtn.disabled = false;
                uploadSubmitBtn.innerText = 'Generate from Upload ↑';
            }
        });
    }

    // ── Render Question ──────────────────────────────────────────────
    function renderQuestion(data) {
        currentQuestion = data.question || data.raw_question || '';
        currentContext  = data.media_context || '';
        currentQType    = data.q_type || 'text';

        showBadge(currentQType);
        // showMedia is now integrated into addMessage

        const questionText = data.question || data.raw_question || 'Could not generate question.';
        const options = data.options || [];

        if (options.length > 0) {
            const lines = questionText.split('\n').filter(l => l.trim());
            const optLines = lines.filter(l => /^[A-D][.)]\s/.test(l.trim()));
            const qLines = lines.filter(l => !optLines.includes(l));
            const questionBody = qLines.join('\n') || questionText;
            addMessage(questionBody, 'bot-msg', optLines.length ? optLines : options, false, currentQType, data.media_url);
            
            if (currentQType === 'audio') speakText(questionBody);
        } else {
            addMessage(questionText, 'bot-msg', null, false, currentQType, data.media_url);
            if (currentQType === 'audio') speakText(questionText);
        }
    }

    // ── Generate Button ──────────────────────────────────────────────
    const generateBtn = document.getElementById('generateBtn');

    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            const token = localStorage.getItem('token');
            if (!token) { window.location.href = '/login.html'; return; }

            generateBtn.disabled = true;
            generateBtn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:0.5rem;"></div> Generating…';

            try {
                const typeParam = selectedType === 'random' ? 'random' : selectedType;
                const res = await fetch(`/generate-question-multimodal?type=${typeParam}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login.html'; return; }
                const data = await res.json();
                renderQuestion(data);
            } catch (err) {
                console.error("Generation error:", err);
                addMessage('❌ Failed to generate question. Please try again.', 'bot-msg');
            } finally {
                generateBtn.disabled = false;
                generateBtn.innerText = '⚡ Generate Another';
            }
        });
    }

    // ── Submit Answer ────────────────────────────────────────────────
    async function submitAnswer(ans) {
        if (!ans.trim()) return;

        // Remove option buttons from last message
        const lastMsg = chatContent.lastElementChild;
        if (lastMsg) {
            const opts = lastMsg.querySelector('.options-container');
            if (opts) opts.remove();
            const inp = lastMsg.querySelector('input');
            if (inp) inp.remove();
        }

        addMessage(ans, 'user-msg');
        const token = localStorage.getItem('token');
        const typingMsg = showTypingIndicator();

        try {
            const res = await fetch('/evaluate-multimodal', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: currentQuestion,
                    user_answer: ans,
                    media_context: currentContext
                })
            });
            const data = await res.json();
            typingMsg.remove();

            const evalText = data.evaluation || 'Could not evaluate answer.';
            addMessage(evalText, 'eval-msg', null, true);

            // Score tracking
            total++;
            let isCorrect = false;
            if (evalText.toUpperCase().includes('CORRECT') && !evalText.toUpperCase().includes('INCORRECT')) {
                score++;
                isCorrect = true;
            }
            if (scoreDisplay) scoreDisplay.innerText = `${score}/${total}`;

            // Save attempt
            fetch('/save-attempt', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_correct: isCorrect, question_type: currentQType })
            }).catch(err => console.error("Failed to save attempt", err));

        } catch (err) {
            typingMsg.remove();
            addMessage('❌ Error evaluating answer. Please try again.', 'eval-msg');
        }
    }

    // ── Progress Page ────────────────────────────────────────────────
    const progressCanvas = document.getElementById('progressChart');
    if (progressCanvas) {
        const token = localStorage.getItem('token');
        if (!token) { window.location.href = '/login.html'; return; }

        fetch('/progress-data', { headers: { 'Authorization': `Bearer ${token}` } })
        .then(res => {
            if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login.html'; throw new Error("unauthorized"); }
            return res.json();
        })
        .then(data => {
            const overview = data.overview;
            document.getElementById('totalPlayed').innerText = overview.total_questions || 0;
            document.getElementById('totalCorrect').innerText = overview.total_correct || 0;
            const accuracy = overview.total_questions > 0
                ? ((overview.total_correct / overview.total_questions) * 100).toFixed(1) : 0;
            document.getElementById('accuracy').innerText = `${accuracy}%`;

            const daily = data.daily;
            if (daily.length === 0) return;

            const labels = daily.map(d => d.date);
            const accuracyData = daily.map(d => (d.total_correct / d.total_questions) * 100);

            new Chart(progressCanvas, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Daily Accuracy (%)',
                        data: accuracyData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                    },
                    plugins: { legend: { labels: { color: '#f8fafc' } } }
                }
            });
        })
        .catch(console.error);
    }
});
