document.addEventListener("DOMContentLoaded", () => {
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const audiencePills = document.querySelectorAll("#audience-pills .pill-btn");
  const chipsContainer = document.getElementById("chips-container");
  const inspectorContent = document.getElementById("inspector-content");
  const currentFilterBadge = document.getElementById("current-filter-badge");
  const statDocs = document.getElementById("stat-docs");
  const statChunks = document.getElementById("stat-chunks");

  let currentAudience = "both";

  // 1. Fetch System Stats
  fetch("/api/stats")
    .then(r => r.json())
    .then(stats => {
      if (statDocs) statDocs.textContent = stats.total_docs || 10;
      if (statChunks) statChunks.textContent = stats.total_chunks || 858;
    })
    .catch(err => console.error("Error loading stats:", err));

  // 2. Fetch & Render Preset Query Chips
  fetch("/api/queries")
    .then(r => r.json())
    .then(queries => {
      chipsContainer.innerHTML = "";
      queries.forEach(q => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "query-chip";
        
        const isIrr = q.category === "irrelevant";
        const tagSpan = document.createElement("span");
        tagSpan.className = isIrr ? "chip-tag-irr" : "chip-tag-bench";
        tagSpan.textContent = isIrr ? "🛡️ Guardrail" : `Q#${q.id}`;
        
        const textSpan = document.createElement("span");
        textSpan.textContent = q.query.length > 40 ? q.query.slice(0, 40) + "..." : q.query;
        
        btn.appendChild(tagSpan);
        btn.appendChild(textSpan);

        btn.addEventListener("click", () => {
          userInput.value = q.query;
          if (q.audience && q.audience !== "both") {
            setAudience(q.audience);
          }
          chatForm.dispatchEvent(new Event("submit"));
        });

        chipsContainer.appendChild(btn);
      });
    })
    .catch(err => console.error("Error loading queries:", err));

  // 3. Audience Pill Switcher
  audiencePills.forEach(pill => {
    pill.addEventListener("click", () => {
      const aud = pill.getAttribute("data-audience");
      setAudience(aud);
    });
  });

  function setAudience(aud) {
    currentAudience = aud;
    audiencePills.forEach(p => {
      if (p.getAttribute("data-audience") === aud) {
        p.classList.add("active");
      } else {
        p.classList.remove("active");
      }
    });
    if (currentFilterBadge) {
      currentFilterBadge.textContent = `Filter: ${aud}`;
    }
  }

  // 4. Form Submit & Chat Handler
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    // Append User Message
    appendUserMessage(query);
    userInput.value = "";
    userInput.focus();

    // Append Typing Indicator
    const typingId = appendTypingIndicator();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          audience: currentAudience,
          top_k: 3
        })
      });

      const data = await res.json();
      removeElement(typingId);

      if (!data.is_relevant) {
        // Guardrail Refusal
        appendGuardrailRefusalMessage(data.answer);
        renderGuardrailInspector(query);
      } else {
        // Standard in-domain answer
        appendBotMessage(data.answer);
        renderChunksInspector(data.chunks, query);
      }

    } catch (err) {
      console.error(err);
      removeElement(typingId);
      appendBotMessage("Đã xảy ra lỗi kết nối với máy chủ. Vui lòng kiểm tra lại dịch vụ.");
    }
  });

  function appendUserMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message-bubble user-message";
    msgDiv.innerHTML = `
      <div class="avatar-col">
        <div class="small-avatar">👤</div>
      </div>
      <div class="content-col">
        <div class="sender-name">Bạn</div>
        <div class="message-body">${escapeHtml(text)}</div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
  }

  function appendBotMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message-bubble bot-message";
    
    // Format text into html paragraphs & lists
    const formattedHtml = formatMarkdownText(text);

    msgDiv.innerHTML = `
      <div class="avatar-col">
        <div class="small-avatar">🤖</div>
      </div>
      <div class="content-col">
        <div class="sender-name">Shopee Assistant</div>
        <div class="message-body">${formattedHtml}</div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
  }

  function appendGuardrailRefusalMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message-bubble bot-message";
    msgDiv.innerHTML = `
      <div class="avatar-col">
        <div class="small-avatar">🛡️</div>
      </div>
      <div class="content-col">
        <div class="sender-name">Shopee Policy Guardrail</div>
        <div class="message-body guardrail-card">
          <div class="guardrail-badge">⚠️ PHÁT HIỆN CÂU HỎI LẠC ĐỀ (OUT-OF-DOMAIN)</div>
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
  }

  function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "message-bubble bot-message";
    div.innerHTML = `
      <div class="avatar-col">
        <div class="small-avatar">🤖</div>
      </div>
      <div class="content-col">
        <div class="message-body typing-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
    return id;
  }

  function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function renderChunksInspector(chunks, query) {
    if (!chunks || chunks.length === 0) {
      inspectorContent.innerHTML = `
        <div class="empty-inspector">
          <p>Không tìm thấy mảnh tài liệu nào phù hợp với bộ lọc '${currentAudience}'.</p>
        </div>
      `;
      return;
    }

    let html = `
      <div style="font-size:0.8rem; color:#475569; margin-bottom:6px;">
        Truy vấn: <strong>"${escapeHtml(query.slice(0, 45))}..."</strong>
      </div>
    `;

    chunks.forEach((c, idx) => {
      const scorePct = Math.min(100, Math.max(10, Math.round(c.score * 200)));
      html += `
        <div class="chunk-card">
          <div class="chunk-top-row">
            <span class="chunk-rank">Top #${idx + 1}</span>
            <span class="score-badge">
              ⚡ Cosine: ${c.score.toFixed(4)}
            </span>
          </div>
          <div class="chunk-doc-title">${escapeHtml(c.title)}</div>
          <div class="chunk-meta-row">
            <span>Tệp: <a href="${escapeHtml(c.source_url)}" target="_blank" class="doc-link">${escapeHtml(c.doc_id)}</a></span>
            <span>• Đối tượng: <strong>${escapeHtml(c.audience)}</strong></span>
          </div>
          <div class="chunk-snippet">${escapeHtml(c.content.slice(0, 220))}...</div>
        </div>
      `;
    });

    inspectorContent.innerHTML = html;
  }

  function renderGuardrailInspector(query) {
    inspectorContent.innerHTML = `
      <div class="chunk-card" style="border-color:#FF8A80; background:#FFFBFB;">
        <div class="chunk-top-row">
          <span class="chunk-rank" style="background:#FFEBEE; color:#C62828;">🛡️ Guardrail Refusal</span>
          <span class="score-badge" style="background:#FFEBEE; color:#C62828;">Chặn truy xuất</span>
        </div>
        <div class="chunk-doc-title" style="color:#C62828;">Nội dung nằm ngoài phạm vi Shopee</div>
        <p style="font-size:0.82rem; color:#64748B; margin-bottom:10px; line-height:1.45;">
          Câu hỏi: <em>"${escapeHtml(query)}"</em> không thuộc bất kỳ nhóm chủ đề chính sách nào trong 10 tài liệu đã lập chỉ mục (Đổi trả, Hoàn tiền, Khiếu nại, Bảo hành, Hủy đơn).
        </p>
        <div style="padding:8px 12px; background:#F1F5F9; border-radius:6px; font-size:0.75rem; color:#334155;">
          <strong>Trạng thái bảo vệ:</strong> Kích hoạt từ chối (Domain Guardrail) để ngăn ngừa sinh ảo giác thông tin ngoài sàn.
        </div>
      </div>
    `;
  }

  function formatMarkdownText(text) {
    if (!text) return "";
    let lines = text.split("\n");
    let inList = false;
    let htmlParts = [];

    lines.forEach(line => {
      let trimmed = line.trim();
      if (!trimmed) {
        if (inList) {
          htmlParts.push("</ul>");
          inList = false;
        }
        return;
      }

      if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ")) {
        if (!inList) {
          htmlParts.push("<ul>");
          inList = true;
        }
        let itemText = trimmed.replace(/^[-*•]\s+/, "");
        htmlParts.push(`<li>${formatInlineStyles(itemText)}</li>`);
      } else {
        if (inList) {
          htmlParts.push("</ul>");
          inList = false;
        }
        htmlParts.push(`<p>${formatInlineStyles(trimmed)}</p>`);
      }
    });

    if (inList) htmlParts.push("</ul>");
    return htmlParts.join("");
  }

  function formatInlineStyles(str) {
    let escaped = escapeHtml(str);
    // Bold: **text**
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    return escaped;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
