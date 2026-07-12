let currentRole = 'seeker';
let currentProfile = {};

const sections = document.querySelectorAll('.section');

function showSection(id) {
  sections.forEach(s => s.classList.remove('section--active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('section--active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('[data-nav]').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    showSection(el.dataset.nav);
  });
});

document.getElementById('results-back').addEventListener('click', () => {
  showSection(currentRole === 'seeker' ? 'seeker' : 'employer');
});

function matchBadgeClass(percent) {
  if (percent >= 70) return 'match-badge--high';
  if (percent >= 50) return 'match-badge--mid';
  return 'match-badge--low';
}

function formatSalary(min, max) {
  return `${min.toLocaleString('ru-RU')} – ${max.toLocaleString('ru-RU')} ₽`;
}

function renderVacancyCard(v) {
  return `
    <article class="result-card">
      <div class="result-card__header">
        <div>
          <div class="result-card__title">${v.title}</div>
          <div class="result-card__company">${v.company}</div>
        </div>
        <span class="match-badge ${matchBadgeClass(v.match)}">${v.match}% совпадение</span>
      </div>
      <div class="result-card__meta">
        <span>📍 ${v.city}</span>
        <span>💰 ${formatSalary(v.salary_min, v.salary_max)}</span>
        <span>📋 ${v.experience}</span>
        <span>🏢 ${v.format}</span>
      </div>
      <div class="result-card__skills">
        ${v.skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}
      </div>
      <p class="result-card__desc">${v.description}</p>
    </article>
  `;
}

function renderCandidateCard(c) {
  return `
    <article class="result-card">
      <div class="result-card__header">
        <div>
          <div class="result-card__title">${c.name}</div>
          <div class="result-card__company">${c.title}</div>
        </div>
        <span class="match-badge ${matchBadgeClass(c.match)}">${c.match}% совпадение</span>
      </div>
      <div class="result-card__meta">
        <span>📍 ${c.city}</span>
        <span>💰 от ${c.salary_expectation.toLocaleString('ru-RU')} ₽</span>
        <span>📋 ${c.experience}</span>
        <span>🏢 ${c.format}</span>
      </div>
      <div class="result-card__skills">
        ${c.skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}
      </div>
      <p class="result-card__desc">${c.summary}</p>
    </article>
  `;
}

function renderResults(matches) {
  const list = document.getElementById('results-list');
  const title = document.getElementById('results-title');
  const desc = document.getElementById('results-desc');

  if (currentRole === 'seeker') {
    title.textContent = 'Подобранные вакансии';
    desc.textContent = `Найдено ${matches.length} релевантных предложений`;
  } else {
    title.textContent = 'Подобранные кандидаты';
    desc.textContent = `Найдено ${matches.length} подходящих кандидатов`;
  }

  if (!matches.length) {
    list.innerHTML = '<div class="empty-state">Пока нет подходящих совпадений. Попробуйте изменить навыки или требования.</div>';
    return;
  }

  list.innerHTML = matches
    .map(m => currentRole === 'seeker' ? renderVacancyCard(m) : renderCandidateCard(m))
    .join('');
}

function resetChat() {
  const messages = document.getElementById('chat-messages');
  messages.innerHTML = `
    <div class="chat-msg chat-msg--bot">
      Привет! Я помогу разобраться с рекомендациями. Спросите о лучших вариантах, зарплате или формате работы.
    </div>
  `;
}

async function fetchMatches() {
  const res = await fetch('/api/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role: currentRole, profile: currentProfile }),
  });
  const data = await res.json();
  return data.matches;
}

document.getElementById('seeker-form').addEventListener('submit', async e => {
  e.preventDefault();
  currentRole = 'seeker';
  currentProfile = {
    name: document.getElementById('seeker-name').value,
    city: document.getElementById('seeker-city').value,
    salary: document.getElementById('seeker-salary').value,
    experience: document.getElementById('seeker-experience').value,
    format: document.getElementById('seeker-format').value,
    skills: document.getElementById('seeker-skills').value,
  };

  const matches = await fetchMatches();
  renderResults(matches);
  resetChat();
  showSection('results');
});

document.getElementById('employer-form').addEventListener('submit', async e => {
  e.preventDefault();
  currentRole = 'employer';
  currentProfile = {
    title: document.getElementById('employer-title').value,
    city: document.getElementById('employer-city').value,
    salary_min: document.getElementById('employer-salary-min').value,
    salary_max: document.getElementById('employer-salary-max').value,
    experience: document.getElementById('employer-experience').value,
    format: document.getElementById('employer-format').value,
    skills: document.getElementById('employer-skills').value,
  };

  const matches = await fetchMatches();
  renderResults(matches);
  resetChat();
  showSection('results');
});

document.getElementById('chat-form').addEventListener('submit', async e => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  const messages = document.getElementById('chat-messages');
  messages.innerHTML += `<div class="chat-msg chat-msg--user">${message}</div>`;
  input.value = '';
  messages.scrollTop = messages.scrollHeight;

  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, role: currentRole, profile: currentProfile }),
  });
  const data = await res.json();

  messages.innerHTML += `<div class="chat-msg chat-msg--bot">${data.reply}</div>`;
  messages.scrollTop = messages.scrollHeight;
});
