const USER_ID = 1;
const fmt = (n) => `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const els = {
  balanceCards: document.getElementById('balanceCards'),
  scheduleList: document.getElementById('scheduleList'),
  nudgeFeed: document.getElementById('nudgeFeed'),
  traceLog: document.getElementById('traceLog'),
  feedbackStats: document.getElementById('feedbackStats'),
  runBtn: document.getElementById('runPipelineBtn'),
  resetBtn: document.getElementById('resetBtn'),
  userName: document.getElementById('userName'),
  agentNodes: document.querySelectorAll('.agent-node'),
};

async function loadDashboard() {
  const res = await fetch(`/api/dashboard/${USER_ID}`);
  const data = await res.json();
  els.userName.textContent = data.user.name.split(' ')[0];

  els.balanceCards.innerHTML = data.accounts.map(acc => `
    <div class="balance-card">
      <div class="type">${acc.account_type}</div>
      <div class="amount ${acc.balance_available < 0 ? 'negative' : ''}">${fmt(acc.balance_available)}</div>
    </div>
  `).join('');

  els.scheduleList.innerHTML = data.schedules.map(s => `
    <div class="schedule-item ${s.status === 'paused' ? 'paused' : ''}">
      <div>
        <div class="label">${s.label}</div>
        <div class="due">${s.status === 'paused' ? 'Paused' : 'Due ' + s.due_date}</div>
      </div>
      <div class="amt">${fmt(s.amount)}</div>
    </div>
  `).join('');
}

async function loadActiveNudges() {
  const res = await fetch(`/api/nudges/${USER_ID}`);
  const nudges = await res.json();
  if (nudges.length === 0) return;
  els.nudgeFeed.innerHTML = '';
  nudges.forEach(n => els.nudgeFeed.appendChild(renderNudgeCard(n)));
}

function renderNudgeCard(n) {
  const div = document.createElement('div');
  div.className = 'nudge-card';
  div.dataset.id = n.id;
  const urgent = n.urgency_score >= 0.7;
  div.innerHTML = `
    <div class="nudge-top">
      <span class="nudge-badge ${urgent ? 'urgent' : ''}">${n.category.replace('_', ' ')}</span>
    </div>
    <div class="nudge-title">${n.title}</div>
    <div class="nudge-msg">${n.message}</div>
    <div class="nudge-actions">
      <button class="nudge-btn accept">${actionLabel(n)}</button>
      <button class="nudge-btn dismiss">Dismiss</button>
    </div>
    <div class="nudge-result" style="display:none;"></div>
  `;
  div.querySelector('.accept').addEventListener('click', () => actOnNudge(n.id, 'accept', div));
  div.querySelector('.dismiss').addEventListener('click', () => actOnNudge(n.id, 'dismiss', div));
  return div;
}

function actionLabel(n) {
  const map = { invest: 'Invest Now', start_sip: 'Resume SIP', pay_bill: 'Pay Now', review: 'Move Funds' };
  return map[n.action_type] || 'View';
}

async function actOnNudge(id, kind, cardEl) {
  cardEl.querySelectorAll('button').forEach(b => b.disabled = true);
  const res = await fetch(`/api/nudges/${id}/${kind}`, { method: 'POST' });
  const data = await res.json();
  cardEl.classList.add('done');
  const resultEl = cardEl.querySelector('.nudge-result');
  resultEl.style.display = 'block';
  if (kind === 'accept') {
    resultEl.textContent = data.result?.reference_id
      ? `Done — ref ${data.result.reference_id}`
      : 'Done';
  } else {
    resultEl.style.color = 'var(--ink-400)';
    resultEl.textContent = `Dismissed — this category will surface less often`;
  }
  loadFeedbackStats();
}

async function runPipeline() {
  els.runBtn.disabled = true;
  els.runBtn.textContent = 'Scanning…';
  resetAgentRow();

  const res = await fetch(`/api/run-pipeline/${USER_ID}`, { method: 'POST' });
  const data = await res.json();

  await animateTrace(data.pipeline_trace);
  await loadActiveNudges();
  await loadFeedbackStats();

  els.runBtn.disabled = false;
  els.runBtn.textContent = 'Run Daily Scan';
}

function resetAgentRow() {
  els.agentNodes.forEach(n => {
    n.classList.remove('active', 'done');
    n.querySelector('.agent-status').textContent = 'idle';
  });
  els.traceLog.innerHTML = '';
}

function animateTrace(trace) {
  return new Promise(resolve => {
    let i = 0;
    function step() {
      if (i >= trace.length) { resolve(); return; }
      const entry = trace[i];
      highlightAgent(entry.step);
      appendTraceLine(entry);
      i++;
      setTimeout(step, 550);
    }
    step();
  });
}

function highlightAgent(stepName) {
  els.agentNodes.forEach(node => {
    const name = node.dataset.agent;
    if (stepName.startsWith(name)) {
      node.classList.add('active');
      node.querySelector('.agent-status').textContent = 'running';
    } else if (node.classList.contains('active')) {
      node.classList.remove('active');
      node.classList.add('done');
      node.querySelector('.agent-status').textContent = 'done';
    }
  });
}

function appendTraceLine(entry) {
  if (els.traceLog.querySelector('.trace-empty')) els.traceLog.innerHTML = '';
  const line = document.createElement('div');
  line.className = 'trace-line';
  const detail = Object.entries(entry.payload)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? '[' + v.join(', ') + ']' : v}`)
    .join('  ·  ');
  line.innerHTML = `<span class="step-name">${entry.step}</span><br><span class="step-detail">${detail}</span>`;
  els.traceLog.appendChild(line);
  els.traceLog.scrollTop = els.traceLog.scrollHeight;
}

async function loadFeedbackStats() {
  const res = await fetch(`/api/feedback-stats/${USER_ID}`);
  const rows = await res.json();
  if (rows.length === 0) return;

  const byCategory = {};
  rows.forEach(r => {
    byCategory[r.category] = byCategory[r.category] || { accepted: 0, dismissed: 0 };
    byCategory[r.category][r.user_response] = r.c;
  });

  els.feedbackStats.innerHTML = Object.entries(byCategory).map(([cat, v]) => {
    const total = v.accepted + (v.dismissed || 0);
    const pct = total ? Math.round((v.accepted / total) * 100) : 50;
    return `
      <div class="weight-row">
        <div class="cat">${cat.replace('_', ' ')}</div>
        <div class="weight-bar-track"><div class="weight-bar-fill" style="width:${pct}%"></div></div>
        <div class="weight-val">${pct}%</div>
      </div>
    `;
  }).join('');
}

els.runBtn.addEventListener('click', runPipeline);
els.resetBtn.addEventListener('click', async () => {
  await fetch(`/api/reset/${USER_ID}`, { method: 'POST' });
  els.nudgeFeed.innerHTML = '<div class="empty-state">No nudges yet — tap <strong>Run Daily Scan</strong> to let the agents analyze your account.</div>';
  els.feedbackStats.innerHTML = '<div class="trace-empty">Act on a nudge to see weights adjust.</div>';
  resetAgentRow();
  els.traceLog.innerHTML = '<div class="trace-empty">No run yet.</div>';
  loadDashboard();
});

loadDashboard();
loadActiveNudges();
loadFeedbackStats();
