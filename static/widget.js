/**
 * Airborne Aviation Academy - Embeddable AI Assistant Widget
 * 24/7 DGCA Pilot Training Doubts | 30-Minute Daily Cap | Escalation to WhatsApp & Phone
 */
(function () {
  if (window.AirborneChatLoaded) return;
  window.AirborneChatLoaded = true;

  // Determine API base url (from script source or current origin)
  const currentScript = document.currentScript;
  let apiBase = "";
  if (currentScript && currentScript.src) {
    try {
      const url = new URL(currentScript.src);
      apiBase = url.origin;
    } catch (e) {
      apiBase = window.location.origin;
    }
  } else {
    apiBase = window.location.origin;
  }

  // Load stylesheet if not already present
  if (!document.getElementById("airborne-widget-css")) {
    const link = document.createElement("link");
    link.id = "airborne-widget-css";
    link.rel = "stylesheet";
    link.href = `${apiBase}/widget.css`;
    document.head.appendChild(link);
  }

  // State Management
  const STORAGE_KEY = "airborne_student_id";
  let studentId = localStorage.getItem(STORAGE_KEY);
  if (!studentId) {
    studentId = "std_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now().toString(36);
    localStorage.setItem(STORAGE_KEY, studentId);
  }

  let isOpen = false;
  let remainingSeconds = 1800; // 30 minutes default
  let isCapped = false;
  let soundEnabled = true;
  let timerInterval = null;
  let heartbeatInterval = null;
  let lastUserActivity = Date.now();

  // Subtle web audio chime for messages
  function playChime(freq = 587.33) {
    if (!soundEnabled) return;
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (e) {}
  }

  // Build Widget DOM Elements
  const container = document.createElement("div");
  container.className = "airborne-widget-root";
  container.innerHTML = `
    <!-- Launcher Button -->
    <div class="airborne-launcher">
      <div class="airborne-launcher-tooltip" id="airborne-tooltip">
        ✈️ <b>Ask Flight AI</b> (DGCA / CPL Doubts)
      </div>
      <button class="airborne-launcher-btn" id="airborne-toggle-btn" aria-label="Open Airborne AI Assistant">
        <div class="airborne-radar-dot"></div>
        <div class="airborne-radar-pulse"></div>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
        </svg>
      </button>
    </div>

    <!-- Chat Window -->
    <div class="airborne-widget-window" id="airborne-window">
      <!-- Header -->
      <div class="airborne-header">
        <div class="airborne-header-top">
          <div class="airborne-brand">
            <div class="airborne-brand-icon">✈️</div>
            <div class="airborne-brand-info">
              <h4>Airborne Flight AI</h4>
              <span><span class="airborne-live-indicator"></span> 24/7 DGCA Doubt Resolution</span>
            </div>
          </div>
          <div class="airborne-header-actions">
            <button class="airborne-header-btn" id="airborne-sound-btn" title="Toggle Sound">
              <svg id="airborne-sound-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
              </svg>
            </button>
            <button class="airborne-header-btn" id="airborne-close-btn" title="Minimize Chat">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        <!-- 30-Minute Usage Cap Bar -->
        <div class="airborne-timer-bar">
          <div class="airborne-timer-left">
            <span>⏱️ Daily AI Cap:</span>
            <span class="airborne-timer-clock" id="airborne-timer-display">30:00</span>
            <span style="font-size: 10px; opacity: 0.8;">left</span>
          </div>
          <div class="airborne-timer-progress" title="Remaining session time today">
            <div class="airborne-timer-fill" id="airborne-timer-fill"></div>
          </div>
        </div>
      </div>

      <!-- Messages Thread -->
      <div class="airborne-messages" id="airborne-messages"></div>

      <!-- Footer / Input -->
      <div class="airborne-footer">
        <div class="airborne-input-row" id="airborne-input-container">
          <input type="text" class="airborne-input" id="airborne-input" placeholder="Ask about CPL fees, DGCA syllabus, medicals..." autocomplete="off" />
          <button class="airborne-send-btn" id="airborne-send-btn" aria-label="Send Message">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div class="airborne-footer-notice">
          Airborne Aviation Academy • 24/7 Live Admissions Desk
        </div>
      </div>

      <!-- Callback Modal -->
      <div class="airborne-modal-overlay" id="airborne-callback-modal">
        <div class="airborne-modal">
          <h4>📞 Request Chief Counselor Callback</h4>
          <p>Get a direct 1-on-1 call with our Senior Flying Instructor within 15 minutes.</p>
          <form id="airborne-callback-form">
            <div class="airborne-form-group">
              <label>Your Full Name *</label>
              <input type="text" id="airborne-cb-name" placeholder="Captain / Student Name" required />
            </div>
            <div class="airborne-form-group">
              <label>Phone / WhatsApp Number *</label>
              <input type="tel" id="airborne-cb-phone" placeholder="+91 98765 43210" required />
            </div>
            <div class="airborne-form-group">
              <label>Current Status</label>
              <input type="text" id="airborne-cb-status" placeholder="e.g. 12th Student / Commerce / Starting CPL" />
            </div>
            <div class="airborne-modal-btns">
              <button type="button" class="airborne-modal-btn-cancel" id="airborne-cb-cancel">Cancel</button>
              <button type="submit" class="airborne-modal-btn-submit">Confirm Callback</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  // DOM Elements
  const windowEl = document.getElementById("airborne-window");
  const toggleBtn = document.getElementById("airborne-toggle-btn");
  const closeBtn = document.getElementById("airborne-close-btn");
  const tooltipEl = document.getElementById("airborne-tooltip");
  const messagesEl = document.getElementById("airborne-messages");
  const inputEl = document.getElementById("airborne-input");
  const sendBtn = document.getElementById("airborne-send-btn");
  const inputContainer = document.getElementById("airborne-input-container");
  const timerDisplay = document.getElementById("airborne-timer-display");
  const timerFill = document.getElementById("airborne-timer-fill");
  const soundBtn = document.getElementById("airborne-sound-btn");
  const soundIcon = document.getElementById("airborne-sound-icon");
  const callbackModal = document.getElementById("airborne-callback-modal");
  const callbackForm = document.getElementById("airborne-callback-form");
  const callbackCancel = document.getElementById("airborne-cb-cancel");

  // Format mm:ss
  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }

  // Update Timer UI
  function updateTimerUI() {
    timerDisplay.innerText = formatTime(remainingSeconds);
    const pct = Math.max(0, Math.min(100, (remainingSeconds / 1800) * 100));
    timerFill.style.width = `${pct}%`;

    timerFill.classList.remove("warning", "danger");
    if (remainingSeconds <= 180) {
      timerFill.classList.add("danger");
    } else if (remainingSeconds <= 600) {
      timerFill.classList.add("warning");
    }

    if (isCapped || remainingSeconds <= 0) {
      handleCapReached();
    }
  }

  function handleCapReached() {
    isCapped = true;
    inputEl.disabled = true;
    sendBtn.disabled = true;
    inputContainer.classList.add("disabled");
    inputEl.placeholder = "Daily 30-min AI cap reached. Connect on WhatsApp below.";

    // Check if cap banner already posted
    if (!document.getElementById("airborne-cap-banner")) {
      const banner = document.createElement("div");
      banner.id = "airborne-cap-banner";
      banner.innerHTML = `
        <div class="airborne-msg bot">
          <div class="airborne-bubble" style="border: 2px solid #ef4444; background: #fff5f5;">
            <h4 style="color: #b91c1c;">⏱️ 30-Minute Daily AI Session Limit Reached</h4>
            <p>You have reached your 30 minutes of free AI interaction for today. 
               Our <b>Senior Admissions Advisors</b> are ready right now to solve your questions directly.</p>
            <div class="airborne-escalation-card">
              <div class="airborne-escalation-header">
                <span class="airborne-escalation-badge">Direct Line</span>
                <span>Connect with Senior Flight Counselor</span>
              </div>
              <div class="airborne-escalation-actions">
                <a href="https://wa.me/919876543210?text=Hi%2C%20I%20have%20utilized%20my%20daily%2030-min%20AI%20chat%20and%20need%20further%20guidance%20on%20DGCA%20pilot%20training." target="_blank" class="airborne-btn-wa">
                  💬 Chat on WhatsApp
                </a>
                <a href="tel:+9118002472676" class="airborne-btn-phone">
                  📞 Call Helpline
                </a>
              </div>
            </div>
          </div>
        </div>
      `;
      messagesEl.appendChild(banner);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  // Initialize Session from Backend
  async function initSession() {
    try {
      const res = await fetch(`${apiBase}/api/session/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId })
      });
      if (res.ok) {
        const data = await res.json();
        remainingSeconds = data.remaining_seconds;
        isCapped = data.is_capped;
        updateTimerUI();
      }
    } catch (err) {
      console.warn("Session init error:", err);
    }
  }

  // Send Heartbeat when active
  async function sendHeartbeat() {
    if (!isOpen || isCapped) return;
    const now = Date.now();
    // Only charge time if student was active in last 45 seconds
    if (now - lastUserActivity > 45000) return;

    try {
      const res = await fetch(`${apiBase}/api/session/heartbeat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId, elapsed_seconds: 15 })
      });
      if (res.ok) {
        const data = await res.json();
        remainingSeconds = data.remaining_seconds;
        isCapped = data.is_capped;
        updateTimerUI();
      }
    } catch (e) {}
  }

  // Local seconds countdown timer
  function startLocalTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      if (isOpen && !isCapped) {
        const now = Date.now();
        if (now - lastUserActivity <= 45000) {
          remainingSeconds = Math.max(0, remainingSeconds - 1);
          updateTimerUI();
        }
      }
    }, 1000);

    if (heartbeatInterval) clearInterval(heartbeatInterval);
    heartbeatInterval = setInterval(sendHeartbeat, 15000);
  }

  // Simple Markdown Parser
  function parseMarkdown(md) {
    if (!md) return "";
    let html = md;
    
    // Escape HTML tags to prevent XSS
    html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    // Markdown tables
    html = html.replace(/\n\|(.+)\|\n\| *[-:| ]+ *\|\n((?:\|.*\|\n?)*)/g, function (match, header, rows) {
      const ths = header.split("|").filter(c => c.trim().length > 0).map(c => `<th>${c.trim()}</th>`).join("");
      const rowLines = rows.trim().split("\n");
      const trs = rowLines.map(r => {
        const tds = r.split("|").filter(c => c.trim().length > 0).map(c => `<td>${c.trim()}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("");
      return `<div style="overflow-x:auto;"><table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table></div>`;
    });

    // Headers
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^#### (.*$)/gim, "<h4>$1</h4>");
    
    // Bold & Italics
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Blockquotes
    html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

    // Bullet points
    html = html.replace(/^\- (.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

    // Ordered points
    html = html.replace(/^\d+\. (.*$)/gim, "<li>$1</li>");

    // Links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:#2563eb;text-decoration:underline;">$1</a>');

    // Paragraph breaks
    html = html.replace(/\n\n/g, "<p></p>");

    return html;
  }

  // Append Message to Thread
  function appendMessage(sender, text, chips = [], escalation = null) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `airborne-msg ${sender}`;

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    let innerContent = `
      <div class="airborne-bubble">
        ${parseMarkdown(text)}
    `;

    // Escalation Prompt (WhatsApp / Phone)
    if (escalation && escalation.needed) {
      innerContent += `
        <div class="airborne-escalation-card">
          <div class="airborne-escalation-header">
            <span class="airborne-escalation-badge">Admissions Desk</span>
            <span>${escalation.reason || "Speak with Senior Flight Instructor"}</span>
          </div>
          <div class="airborne-escalation-desc">
            Direct priority channel for immediate loan sanction, medical assessment review & campus seat reservation.
          </div>
          <div class="airborne-escalation-actions">
            <a href="${escalation.whatsapp_url}" target="_blank" class="airborne-btn-wa">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.301-.15-1.78-.878-2.056-.978-.276-.1-.476-.15-.676.15-.2.3-.776.978-.951 1.178-.175.2-.35.225-.651.075-.3-.15-1.267-.467-2.414-1.489-.893-.796-1.496-1.78-1.671-2.08-.175-.3-.019-.462.131-.611.136-.134.301-.35.451-.525.15-.175.2-.3.3-.5.1-.2.05-.375-.025-.525-.075-.15-.676-1.63-.926-2.232-.244-.585-.492-.505-.676-.514-.175-.009-.376-.01-.576-.01s-.525.075-.801.375c-.276.3-1.052 1.028-1.052 2.508 0 1.48 1.077 2.91 1.228 3.11.15.2 2.119 3.237 5.134 4.54.717.31 1.277.496 1.713.634.72.228 1.375.196 1.893.118.577-.087 1.78-.727 2.03-1.43.25-.702.25-1.304.175-1.43-.075-.125-.276-.2-.576-.35z"/>
                <path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.174L2 22l4.98-1.39A9.957 9.957 0 0 0 12 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18.2c-1.64 0-3.17-.46-4.48-1.27l-.32-.2-2.96.83.84-2.88-.21-.34A8.176 8.176 0 0 1 3.8 12c0-4.52 3.68-8.2 8.2-8.2 4.52 0 8.2 3.68 8.2 8.2 0 4.52-3.68 8.2-8.2 8.2z"/>
              </svg>
              Chat on WhatsApp
            </a>
            <a href="tel:${escalation.phone_helpline || '+9118002472676'}" class="airborne-btn-phone">
              📞 Call ${escalation.phone_helpline || 'Helpline'}
            </a>
            <button type="button" class="airborne-btn-callback" onclick="window.AirborneChat.openCallbackModal()">
              ⚡ Request 15-Min Callback
            </button>
          </div>
        </div>
      `;
    }

    // Quick suggestion chips
    if (chips && chips.length > 0) {
      innerContent += `<div class="airborne-chips">`;
      chips.forEach(chip => {
        innerContent += `<button type="button" class="airborne-chip" onclick="window.AirborneChat.send('${chip.replace(/'/g, "\\'")}')">${chip}</button>`;
      });
      innerContent += `</div>`;
    }

    innerContent += `</div><span class="airborne-msg-time">${timeStr}</span>`;
    msgDiv.innerHTML = innerContent;
    messagesEl.appendChild(msgDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    if (sender === "bot") {
      playChime(659.25);
    }
  }

  // Show Typing Indicator
  function showTypingIndicator() {
    const typing = document.createElement("div");
    typing.className = "airborne-msg bot";
    typing.id = "airborne-typing-indicator";
    typing.innerHTML = `
      <div class="airborne-typing">
        <div class="airborne-dot"></div>
        <div class="airborne-dot"></div>
        <div class="airborne-dot"></div>
      </div>
    `;
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTypingIndicator() {
    const typing = document.getElementById("airborne-typing-indicator");
    if (typing) typing.remove();
  }

  // Send Message
  async function sendMessage(textToSend) {
    const text = (textToSend || inputEl.value).trim();
    if (!text) return;
    if (isCapped) {
      handleCapReached();
      return;
    }

    lastUserActivity = Date.now();
    inputEl.value = "";
    appendMessage("user", text);
    showTypingIndicator();

    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: studentId, message: text })
      });

      hideTypingIndicator();

      if (!res.ok) {
        throw new Error("Chat request failed");
      }

      const data = await res.json();
      if (data.session) {
        remainingSeconds = data.session.remaining_seconds;
        isCapped = data.session.is_capped;
        updateTimerUI();
      }

      appendMessage("bot", data.answer, data.chips, data.escalation);
    } catch (err) {
      hideTypingIndicator();
      appendMessage("bot", "I am having trouble reaching the flight server right now. Please connect directly via WhatsApp or call our 24/7 helpline.", [], {
        needed: true,
        reason: "Offline fallback connection",
        whatsapp_url: "https://wa.me/919876543210",
        phone_helpline: "+91 1800 247 2676"
      });
    }
  }

  // Toggle Widget Window
  function toggleChat(forceOpen) {
    isOpen = typeof forceOpen === "boolean" ? forceOpen : !isOpen;
    if (isOpen) {
      windowEl.classList.add("open");
      tooltipEl.style.display = "none";
      lastUserActivity = Date.now();
      setTimeout(() => inputEl.focus(), 300);

      // Initial greeting if empty
      if (messagesEl.children.length === 0) {
        sendMessage("hello");
      }
    } else {
      windowEl.classList.remove("open");
    }
  }

  // Event Listeners
  toggleBtn.addEventListener("click", () => toggleChat());
  closeBtn.addEventListener("click", () => toggleChat(false));
  tooltipEl.addEventListener("click", () => toggleChat(true));

  sendBtn.addEventListener("click", () => sendMessage());
  inputEl.addEventListener("keydown", (e) => {
    lastUserActivity = Date.now();
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  inputEl.addEventListener("input", () => {
    lastUserActivity = Date.now();
  });

  soundBtn.addEventListener("click", () => {
    soundEnabled = !soundEnabled;
    soundBtn.style.color = soundEnabled ? "#ffffff" : "#64748b";
  });

  // Callback modal handlers
  callbackCancel.addEventListener("click", () => {
    callbackModal.classList.remove("active");
  });

  callbackForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("airborne-cb-name").value.trim();
    const phone = document.getElementById("airborne-cb-phone").value.trim();
    const status = document.getElementById("airborne-cb-status").value.trim();

    try {
      const res = await fetch(`${apiBase}/api/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          phone: phone,
          query: `Lead callback requested. Status: ${status}`,
          student_id: studentId
        })
      });
      if (res.ok) {
        callbackModal.classList.remove("active");
        callbackForm.reset();
        appendMessage("bot", `✅ Thank you, **${name}**! Your request for an immediate callback has been dispatched to our Chief Flight Counselor. We will ring **${phone}** shortly.`);
      }
    } catch (err) {
      alert("Unable to schedule callback right now. Please message directly on WhatsApp.");
    }
  });

  // Public JavaScript API
  window.AirborneChat = {
    open: () => toggleChat(true),
    close: () => toggleChat(false),
    toggle: () => toggleChat(),
    send: (msg) => sendMessage(msg),
    openCallbackModal: () => callbackModal.classList.add("active"),
    resetCap: async () => {
      try {
        const res = await fetch(`${apiBase}/api/session/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: studentId })
        });
        const data = await res.json();
        remainingSeconds = data.remaining_seconds;
        isCapped = false;
        inputEl.disabled = false;
        sendBtn.disabled = false;
        inputContainer.classList.remove("disabled");
        inputEl.placeholder = "Ask about CPL fees, DGCA syllabus, medicals...";
        const capBanner = document.getElementById("airborne-cap-banner");
        if (capBanner) capBanner.remove();
        updateTimerUI();
        appendMessage("bot", "🔄 Your daily 30-minute AI interaction session has been reset for testing!");
      } catch (e) {}
    }
  };

  // Kickoff initialization
  initSession();
  startLocalTimer();
})();
