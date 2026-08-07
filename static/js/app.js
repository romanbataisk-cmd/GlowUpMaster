const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const S = {
  master: null,
  services: [],
  clients: [],
  bookings: [],
  schedule: [],
  daysOff: [],
  currentDate: new Date().toISOString().slice(0, 10),
};

// ── Utils ─────────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const DAY_NAMES_SHORT = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
const STATUS_LABELS = { pending: 'Ожидает', confirmed: 'Подтверждено', cancelled: 'Отменено', completed: 'Завершено' };

function showToast(msg, type = 'ok') {
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.classList.add('show'); }, 10);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2500);
}

function fmtDate(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}.${m}.${y}`;
}

function formatPrice(p) { return p ? `${p.toLocaleString('ru')} ₽` : 'Бесплатно'; }

async function shareOpenSlot() {
  const active = document.querySelector('.quick-slot.active');
  const time = active?.dataset.slot || '14:00';
  const masterId = S.master?.telegram_id || window._devUserId || '';
  const bookingUrl = `${window.location.origin}/book.html?master=${masterId}`;
  const text = `Освободилось окно сегодня в ${time} ✨ Записаться: ${bookingUrl}`;
  try {
    if (navigator.share) {
      await navigator.share({ title: 'Свободное окно', text, url: bookingUrl });
      showToast('Окно опубликовано');
      return;
    }
    await navigator.clipboard.writeText(text);
    showToast('Текст и ссылка скопированы');
  } catch (error) {
    if (error?.name !== 'AbortError') showToast('Не удалось поделиться', 'err');
  }
}

function setupQuickSlots() {
  document.querySelectorAll('.quick-slot').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.quick-slot').forEach(item => item.classList.remove('active'));
      button.classList.add('active');
    });
  });
}

// ── Navigation ────────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const page = $(name);
  if (page) page.classList.add('active');
  const btn = document.querySelector(`[data-page="${name}"]`);
  if (btn) btn.classList.add('active');
  loadPage(name);
}

async function loadPage(name) {
  if (name === 'home') renderHome();
  if (name === 'bookings') { await loadBookings(); renderBookings(); }
  if (name === 'clients') { await loadClients(); renderClients(); }
  if (name === 'services') { await loadServices(); renderServices(); }
  if (name === 'profile') renderProfile();
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  try {
    S.master = await api.getMe();
    if (!S.master.full_name || S.master.full_name.trim() === '') {
      showOnboarding();
      return;
    }
    hideOnboarding();
    showPage('home');
  } catch (e) {
    showToast('Ошибка подключения', 'err');
  }
}

// ── Onboarding ────────────────────────────────────────────────────────────────
function showOnboarding() {
  $('onboarding').classList.add('show');
  const name = S.master?.full_name || '';
  if (name) $('ob-name').value = name;
}

function hideOnboarding() {
  $('onboarding').classList.remove('show');
}

async function submitOnboarding() {
  const name = $('ob-name').value.trim();
  const specialty = $('ob-specialty').value.trim();
  const phone = $('ob-phone').value.trim();
  if (!name) { showToast('Введите имя', 'err'); return; }
  try {
    S.master = await api.updateProfile({ full_name: name, specialty, phone });
    hideOnboarding();
    showPage('home');
    showToast('Профиль создан! Добро пожаловать 🎉');
  } catch (e) { showToast(e.message, 'err'); }
}

// ── Home ──────────────────────────────────────────────────────────────────────
async function renderHome() {
  const m = S.master;
  if (!m) return;
  const acc = m.access || {};
  const stats = m.stats || {};

  $('home-greeting').textContent = `Привет, ${m.full_name.split(' ')[0]}! 👋`;

  // Subscription banner
  let bannerHtml = '';
  if (acc.mode === 'trial') {
    bannerHtml = `<div class="sub-banner trial" onclick="showPage('profile')">
      ⭐ Пробный период: осталось ${acc.days_left} дн.
      <p>Нажмите, чтобы оформить подписку</p>
    </div>`;
  } else if (acc.mode === 'subscription') {
    bannerHtml = `<div class="sub-banner">
      👑 GlowUp Master активен · ${acc.days_left} дн.
    </div>`;
  } else {
    bannerHtml = `<div class="sub-banner expired" onclick="showPage('profile')">
      ❌ Подписка истекла — оформите снова
    </div>`;
  }
  $('sub-banner').innerHTML = bannerHtml;

  // Stats
  $('stat-today').textContent = stats.today_bookings ?? 0;
  $('stat-week').textContent = stats.week_bookings ?? 0;
  $('stat-clients').textContent = stats.total_clients ?? 0;
  $('stat-revenue').textContent = stats.week_revenue ? `${stats.week_revenue} ₽` : '0 ₽';

  // Today's bookings
  const today = new Date().toISOString().slice(0, 10);
  const todayBookings = await api.getBookings({ date: today }).catch(() => []);
  const activeBookings = todayBookings
    .filter(b => !['cancelled', 'completed'].includes(b.status))
    .sort((a, b) => String(a.time).localeCompare(String(b.time)));
  const nextBooking = activeBookings.find(b => b.time >= new Date().toTimeString().slice(0, 5)) || activeBookings[0];
  if (nextBooking) {
    $('next-booking-time').textContent = nextBooking.time;
    $('next-client-name').textContent = nextBooking.client_name;
    $('next-client-service').textContent = `${nextBooking.service_name} · ${formatPrice(nextBooking.price)}`;
    $('next-client-avatar').textContent = nextBooking.client_name.trim().charAt(0).toUpperCase();
  } else {
    $('next-booking-time').textContent = 'Свободно';
    $('next-client-name').textContent = 'Записей больше нет';
    $('next-client-service').textContent = 'Поделитесь свободным окном с клиентами';
    $('next-client-avatar').textContent = '↗';
  }
  const container = $('today-bookings');
  if (!todayBookings.length) {
    container.innerHTML = '<div class="empty"><p>Записей на сегодня нет</p></div>';
  } else {
    container.innerHTML = todayBookings.map(b => bookingCard(b)).join('');
  }
}

// ── Bookings ──────────────────────────────────────────────────────────────────
async function loadBookings() {
  S.bookings = await api.getBookings({ date: S.currentDate }).catch(() => []);
}

function renderBookings() {
  // Date strip — 14 days
  const strip = $('date-strip');
  const days = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    days.push(d);
  }
  strip.innerHTML = days.map(d => {
    const iso = d.toISOString().slice(0, 10);
    const active = iso === S.currentDate ? 'active' : '';
    return `<button class="date-chip ${active}" onclick="selectDate('${iso}')">
      <span class="chip-day">${DAY_NAMES_SHORT[d.getDay()]}</span>
      <span class="chip-date">${d.getDate()}</span>
    </button>`;
  }).join('');

  const container = $('bookings-list');
  if (!S.bookings.length) {
    container.innerHTML = `<div class="empty">
      <div class="empty-icon">📅</div>
      <h3>Нет записей</h3><p>На эту дату записей нет</p>
    </div>`;
    return;
  }
  container.innerHTML = `<div class="card-list">${S.bookings.map(b => bookingCard(b, true)).join('')}</div>`;
}

function bookingCard(b, withActions = false) {
  const statusCls = { pending: 'badge-pending', confirmed: 'badge-confirmed', cancelled: 'badge-cancelled', completed: 'badge-completed' };
  const actions = withActions ? `
    <div class="flex gap-8 mt-8">
      ${b.status === 'pending' ? `<button class="btn btn-primary btn-sm" onclick="setStatus(${b.id},'confirmed')">✓ Подтвердить</button>` : ''}
      ${b.status !== 'cancelled' && b.status !== 'completed' ? `<button class="btn btn-secondary btn-sm" onclick="setStatus(${b.id},'completed')">✓ Завершено</button>` : ''}
      ${b.status !== 'cancelled' ? `<button class="btn btn-danger btn-sm" onclick="setStatus(${b.id},'cancelled')">Отменить</button>` : ''}
    </div>` : '';
  return `<div class="card">
    <div class="card-row">
      <div>
        <div class="card-title">${b.client_name}</div>
        <div class="card-sub">${b.service_name} · ${b.time}</div>
        ${b.client_phone ? `<div class="card-sub">📞 ${b.client_phone}</div>` : ''}
      </div>
      <div class="card-meta">
        <span class="badge ${statusCls[b.status] || ''}">${STATUS_LABELS[b.status] || b.status}</span>
        <div class="card-price mt-8">${formatPrice(b.price)}</div>
      </div>
    </div>
    ${actions}
  </div>`;
}

async function selectDate(iso) {
  S.currentDate = iso;
  await loadBookings();
  renderBookings();
}

async function setStatus(id, status) {
  try {
    await api.setBookingStatus(id, status);
    await loadBookings();
    renderBookings();
    showToast('Статус обновлён');
  } catch (e) { showToast(e.message, 'err'); }
}

function showAddBookingModal() {
  openModal('modal-booking');
  loadServicesIntoSelect();
  loadClientsIntoSelect();
  $('booking-date').value = S.currentDate;
}

async function loadServicesIntoSelect() {
  if (!S.services.length) S.services = await api.getServices().catch(() => []);
  const sel = $('booking-service');
  sel.innerHTML = '<option value="">Выберите услугу</option>' +
    S.services.filter(s => s.is_active).map(s => `<option value="${s.id}">${s.name} — ${formatPrice(s.price)}</option>`).join('');
}

async function loadClientsIntoSelect() {
  if (!S.clients.length) S.clients = await api.getClients().catch(() => []);
  const sel = $('booking-client');
  sel.innerHTML = '<option value="">Новый клиент</option>' +
    S.clients.map(c => `<option value="${c.id}">${c.name}${c.phone ? ' · ' + c.phone : ''}</option>`).join('');
  sel.onchange = () => {
    const c = S.clients.find(x => x.id == sel.value);
    if (c) { $('booking-client-name').value = c.name; $('booking-client-phone').value = c.phone || ''; }
    else { $('booking-client-name').value = ''; $('booking-client-phone').value = ''; }
  };
}

async function loadSlotsForBooking() {
  const svcId = $('booking-service').value;
  const date = $('booking-date').value;
  if (!svcId || !date) return;
  const slots = await api.getSlots(date, svcId).catch(() => []);
  const sel = $('booking-time');
  sel.innerHTML = slots.length
    ? slots.map(s => `<option value="${s}">${s}</option>`).join('')
    : '<option value="">Нет свободных слотов</option>';
}

async function submitBooking() {
  const data = {
    client_name: $('booking-client-name').value.trim(),
    client_phone: $('booking-client-phone').value.trim(),
    service_id: parseInt($('booking-service').value),
    date: $('booking-date').value,
    time: $('booking-time').value,
    client_id: $('booking-client').value ? parseInt($('booking-client').value) : null,
  };
  if (!data.client_name || !data.service_id || !data.date || !data.time) {
    showToast('Заполните все поля', 'err'); return;
  }
  try {
    await api.addBooking(data);
    closeModal('modal-booking');
    await loadBookings();
    renderBookings();
    showToast('Запись создана ✓');
  } catch (e) { showToast(e.message, 'err'); }
}

// ── Clients ───────────────────────────────────────────────────────────────────
async function loadClients(search = '') {
  S.clients = await api.getClients(search).catch(() => []);
}

function renderClients() {
  const container = $('clients-list');
  if (!S.clients.length) {
    container.innerHTML = `<div class="empty">
      <div class="empty-icon">👥</div>
      <h3>Нет клиентов</h3><p>Добавьте первого клиента</p>
    </div>`;
    return;
  }
  container.innerHTML = `<div class="card-list">${S.clients.map(c => `
    <div class="card" onclick="showClientDetail(${c.id})">
      <div class="card-row">
        <div>
          <div class="card-title">${c.name}</div>
          ${c.phone ? `<div class="card-sub">📞 ${c.phone}</div>` : ''}
          ${c.notes ? `<div class="card-sub">💬 ${c.notes}</div>` : ''}
        </div>
        <div style="color:var(--hint);font-size:20px">›</div>
      </div>
    </div>`).join('')}</div>`;
}

async function searchClients() {
  const q = $('client-search').value;
  await loadClients(q);
  renderClients();
}

function showAddClientModal() { openModal('modal-client'); }

async function submitClient() {
  const data = {
    name: $('client-name').value.trim(),
    phone: $('client-phone').value.trim(),
    notes: $('client-notes').value.trim(),
  };
  if (!data.name) { showToast('Введите имя клиента', 'err'); return; }
  try {
    await api.addClient(data);
    closeModal('modal-client');
    $('client-name').value = ''; $('client-phone').value = ''; $('client-notes').value = '';
    await loadClients();
    renderClients();
    showToast('Клиент добавлен ✓');
  } catch (e) { showToast(e.message, 'err'); }
}

async function showClientDetail(id) {
  const client = S.clients.find(c => c.id === id);
  if (!client) return;
  const detail = $('client-detail');
  detail.innerHTML = `
    <div class="page-header" style="border-radius:0">
      <button class="btn-ghost" onclick="closeClientDetail()" style="width:auto;margin-bottom:8px">← Назад</button>
      <h1>${client.name}</h1>
      ${client.phone ? `<p>📞 ${client.phone}</p>` : ''}
    </div>
    <div class="card-list">
      ${client.notes ? `<div class="card"><div class="card-sub">💬 ${client.notes}</div></div>` : ''}
    </div>
    <div class="section"><div class="section-title">История записей</div><div id="client-bookings-list"><div class="loading">Загрузка…</div></div></div>`;
  detail.style.display = 'block';
  document.querySelector('.page.active').style.display = 'none';

  const bookings = await api.getClients().catch(() => []);
  // Load all bookings and filter by client_name as fallback
  const all = await api.getBookings({}).catch(() => []);
  const cb = all.filter(b => b.client_id === id || b.client_name === client.name);
  const el = $('client-bookings-list');
  el.innerHTML = cb.length
    ? `<div class="card-list">${cb.map(b => bookingCard(b)).join('')}</div>`
    : '<div class="empty"><p>Записей нет</p></div>';
}

function closeClientDetail() {
  $('client-detail').style.display = 'none';
  document.querySelector('.page.active').style.display = 'block';
}

// ── Services ──────────────────────────────────────────────────────────────────
async function loadServices() {
  S.services = await api.getServices().catch(() => []);
}

function renderServices() {
  const container = $('services-list');
  if (!S.services.length) {
    container.innerHTML = `<div class="empty">
      <div class="empty-icon">💼</div>
      <h3>Нет услуг</h3><p>Добавьте первую услугу</p>
    </div>`;
    return;
  }
  container.innerHTML = `<div class="card-list">${S.services.map(s => `
    <div class="card">
      <div class="card-row">
        <div style="flex:1">
          <div class="card-title">${s.name}</div>
          <div class="card-sub">⏱ ${s.duration} мин${s.description ? ' · ' + s.description : ''}</div>
          ${s.prepay > 0 ? `<div class="card-sub" style="color:#60a5fa;margin-top:2px">💳 Предоплата ${formatPrice(s.prepay)}</div>` : ''}
        </div>
        <div class="flex gap-8" style="align-items:center">
          <div class="card-price">${formatPrice(s.price)}</div>
          <div class="toggle ${s.is_active ? 'on' : ''}" onclick="toggleService(${s.id}, ${s.is_active})"></div>
        </div>
      </div>
      <div class="flex gap-8 mt-8">
        <button class="btn btn-secondary btn-sm" onclick="editService(${s.id})">Изменить</button>
        <button class="btn btn-danger btn-sm" onclick="deleteService(${s.id})">Удалить</button>
      </div>
    </div>`).join('')}</div>`;
}

function showAddServiceModal() {
  $('svc-modal-title').textContent = 'Новая услуга';
  $('svc-id').value = '';
  $('svc-name').value = ''; $('svc-desc').value = '';
  $('svc-duration').value = '60'; $('svc-price').value = ''; $('svc-prepay').value = '';
  openModal('modal-service');
}

function editService(id) {
  const s = S.services.find(x => x.id === id);
  if (!s) return;
  $('svc-modal-title').textContent = 'Редактировать услугу';
  $('svc-id').value = id;
  $('svc-name').value = s.name; $('svc-desc').value = s.description || '';
  $('svc-duration').value = s.duration;
  $('svc-price').value = s.price || '';
  $('svc-prepay').value = s.prepay || '';
  openModal('modal-service');
}

function parseMoney(val) {
  return parseFloat(String(val).replace(',', '.').replace(/\s/g, '')) || 0;
}

async function submitService() {
  const data = {
    name: $('svc-name').value.trim(),
    description: $('svc-desc').value.trim(),
    duration: parseInt($('svc-duration').value) || 60,
    price: parseMoney($('svc-price').value),
    prepay: parseMoney($('svc-prepay').value),
  };
  if (!data.name) { showToast('Введите название', 'err'); return; }
  const id = $('svc-id').value;
  try {
    if (id) await api.updateService(id, data);
    else await api.addService(data);
    closeModal('modal-service');
    await loadServices(); renderServices();
    showToast(id ? 'Услуга обновлена' : 'Услуга добавлена ✓');
  } catch (e) { showToast(e.message, 'err'); }
}

async function toggleService(id, current) {
  await api.updateService(id, { is_active: current ? 0 : 1 });
  await loadServices(); renderServices();
}

async function deleteService(id) {
  if (!confirm('Удалить услугу?')) return;
  await api.deleteService(id);
  await loadServices(); renderServices();
  showToast('Услуга удалена');
}

// ── Profile ───────────────────────────────────────────────────────────────────
async function renderProfile() {
  const m = S.master;
  if (!m) return;
  $('prof-name').value = m.full_name || '';
  $('prof-specialty').value = m.specialty || '';
  $('prof-bio').value = m.bio || '';
  $('prof-phone').value = m.phone || '';

  // Subscription block
  const acc = m.access || {};
  let subHtml = '';
  if (acc.mode === 'trial') {
    subHtml = `<div class="sub-banner trial">
      ⭐ Пробный период: ${acc.days_left} дн.
      <p>После окончания нужна подписка GlowUp Master</p>
      <button class="btn btn-secondary mt-8" onclick="subscribe()">Оформить подписку — 299 ⭐/мес</button>
    </div>`;
  } else if (acc.mode === 'subscription') {
    subHtml = `<div class="sub-banner">
      👑 GlowUp Master активен<p>Осталось ${acc.days_left} дней</p>
    </div>`;
  } else {
    subHtml = `<div class="sub-banner expired">
      ❌ Подписка истекла
      <button class="btn btn-primary mt-8" onclick="subscribe()">Продлить — 299 ⭐/мес</button>
    </div>`;
  }
  $('sub-info').innerHTML = subHtml;

  // Booking links
  const webappUrl = window.location.origin;
  $('booking-link').value = `${webappUrl}/book.html?master=${m.telegram_id}`;

  // Telegram deep link — показываем если знаем bot_username
  const cfg = await fetch('/api/config').then(r => r.json()).catch(() => ({}));
  if (cfg.bot_username) {
    $('tg-booking-link').value = `https://t.me/${cfg.bot_username}?start=book_${m.telegram_id}`;
    $('tg-link-row').style.display = 'block';
  }
}

async function saveProfile() {
  const data = {
    full_name: $('prof-name').value.trim(),
    specialty: $('prof-specialty').value.trim(),
    bio: $('prof-bio').value.trim(),
    phone: $('prof-phone').value.trim(),
  };
  if (!data.full_name) { showToast('Введите имя', 'err'); return; }
  try {
    S.master = await api.updateProfile(data);
    showToast('Профиль сохранён ✓');
  } catch (e) { showToast(e.message, 'err'); }
}

function copyBookingLink() {
  const link = $('booking-link').value;
  navigator.clipboard.writeText(link).then(() => showToast('Ссылка скопирована!'));
}

function copyTgBookingLink() {
  const link = $('tg-booking-link').value;
  navigator.clipboard.writeText(link).then(() => showToast('Telegram-ссылка скопирована!'));
}

async function subscribe() {
  // Load current price and show modal
  const price = await fetch('/api/subscription/price').then(r => r.json()).catch(() => ({}));
  const rubEl = $('sub-rub-price');
  if (rubEl && price.rub) rubEl.textContent = `${price.rub} ₽`;
  openModal('modal-subscribe');
}

async function subscribeStars() {
  closeModal('modal-subscribe');
  const cfg = await fetch('/api/config').then(r => r.json()).catch(() => ({}));
  if (tg && cfg.bot_username) {
    tg.openTelegramLink(`https://t.me/${cfg.bot_username}?start=subscribe`);
  } else {
    showToast('Откройте бот и отправьте /subscribe');
  }
}

async function subscribeYookassa() {
  closeModal('modal-subscribe');
  try {
    const res = await request('POST', '/api/subscription/yookassa');
    if (tg) {
      tg.openLink(res.payment_url);
    } else {
      window.open(res.payment_url, '_blank');
    }
  } catch (e) {
    showToast('Ошибка: ' + e.message, 'err');
  }
}

// ── Modals ────────────────────────────────────────────────────────────────────
function openModal(id) {
  const el = $(id);
  el.classList.add('open');
}

function closeModal(id) {
  $(id).classList.remove('open');
}

// ── Toast (inject styles) ─────────────────────────────────────────────────────
const toastStyle = document.createElement('style');
toastStyle.textContent = `
.toast { position:fixed; bottom:90px; left:50%; transform:translateX(-50%) translateY(20px);
  background:#333; color:#fff; padding:10px 20px; border-radius:20px;
  font-size:14px; z-index:9999; opacity:0; transition:all .25s; white-space:nowrap; }
.toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
.toast.err { background:#ff3b30; }
`;
document.head.appendChild(toastStyle);

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupQuickSlots();
  init();
});
