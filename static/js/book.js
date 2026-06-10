const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const params    = new URLSearchParams(location.search);
const MASTER_ID = params.get('master');

const S = { master: null, services: [], selectedService: null,
            selectedDate: null, selectedTime: null };
const $ = id => document.getElementById(id);
const MONTHS   = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

let calOffset = 0;

// ── Navigation ────────────────────────────────────────────────────────────────

function goStep(n) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('on'));
  $(`step-${n}`).classList.add('on');
  if (n === 5) launchConfetti();
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}.${m}.${y}`;
}

function localIso(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function fmtPrice(p) {
  return p ? `${Number(p).toLocaleString('ru')} ₽` : 'Бесплатно';
}

function successHtml() {
  const prepay = S.selectedService.prepay || 0;
  return `
    <div class="success-row"><span>💼</span><span>${S.selectedService.name}</span></div>
    <div class="success-row"><span>📅</span><span>${fmtDate(S.selectedDate)} в ${S.selectedTime}</span></div>
    <div class="success-row"><span>👤</span><span>${S.master.full_name}</span></div>
    ${prepay > 0 ? `<div class="success-row"><span>💳</span><span>Предоплата ${fmtPrice(prepay)} оплачена</span></div>` : ''}`;
}

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  // Return from YooKassa card payment
  if (params.get('paid') === '1' && MASTER_ID) {
    try {
      const m = await fetch(`/api/public/master/${MASTER_ID}`, { headers: { 'ngrok-skip-browser-warning': '1' } }).then(r => r.json());
      document.body.innerHTML = `
        <div style="min-height:100svh;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;padding:40px 24px;
                    text-align:center;background:#05070f;color:#f0f4ff">
          <div style="font-size:64px;margin-bottom:20px">✅</div>
          <h2 style="font-size:22px;font-weight:800">Оплата получена!</h2>
          <p style="color:#6b7fa8;margin-top:10px;font-size:14px">
            Мастер ${m.full_name} получил уведомление о вашей записи
          </p>
        </div>`;
      if (tg) setTimeout(() => tg.close(), 3500);
    } catch {
      document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#6b7fa8">Оплата прошла!</div>';
    }
    return;
  }

  if (!MASTER_ID) {
    document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#6b7fa8">Ссылка недействительна</div>';
    return;
  }
  try {
    S.master   = await fetch(`/api/public/master/${MASTER_ID}`, { headers: { 'ngrok-skip-browser-warning': '1' } }).then(r => r.json());
    S.services = await fetch(`/api/public/master/${MASTER_ID}/services`, { headers: { 'ngrok-skip-browser-warning': '1' } }).then(r => r.json());
    renderMasterHeader();
    renderServices();
    goStep(1);
  } catch {
    document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#6b7fa8">Мастер не найден</div>';
  }
}

// ── Step 1: Services ──────────────────────────────────────────────────────────

function renderMasterHeader() {
  const m = S.master;
  $('master-name').textContent      = m.full_name;
  $('master-specialty').textContent = m.specialty || '';
  $('master-avatar-letter').textContent = m.full_name[0].toUpperCase();
}

function renderServices() {
  $('services-list').innerHTML = S.services.map(s => `
    <div class="svc-card" onclick="selectService(${s.id})">
      <div class="svc-body">
        <div class="svc-name">${s.name}</div>
        <div class="svc-meta">⏱ ${s.duration} мин${s.description ? ' · ' + s.description : ''}</div>
        ${s.prepay > 0 ? `<div class="svc-prepay">💳 Предоплата ${fmtPrice(s.prepay)}</div>` : ''}
      </div>
      <div class="svc-price">${s.price ? fmtPrice(s.price) : 'Бесплатно'}</div>
      <span class="svc-arr">›</span>
    </div>`).join('');
}

function selectService(id) {
  S.selectedService = S.services.find(s => s.id === id);
  $('selected-svc-name').textContent = S.selectedService.name;
  calOffset = 0;
  renderCalendar();
  goStep(2);
}

// ── Step 2: Calendar ──────────────────────────────────────────────────────────

function renderCalendar() {
  const now  = new Date();
  const base = new Date(now.getFullYear(), now.getMonth() + calOffset, 1);
  const y = base.getFullYear();
  const m = base.getMonth();

  $('cal-month').textContent     = `${MONTHS[m]} ${y}`;
  $('cal-prev').style.visibility = calOffset <= 0 ? 'hidden' : '';
  $('cal-prev').onclick = () => { calOffset--; renderCalendar(); };
  $('cal-next').onclick = () => { calOffset++; renderCalendar(); };

  const grid     = $('cal-grid');
  grid.innerHTML = DAY_NAMES.map(n => `<div class="cal-dn">${n}</div>`).join('');

  const leadDays  = (new Date(y, m, 1).getDay() + 6) % 7;
  const totalDays = new Date(y, m + 1, 0).getDate();
  const todayIso  = localIso(now.getFullYear(), now.getMonth(), now.getDate());

  for (let i = 0; i < leadDays; i++) grid.innerHTML += '<div></div>';
  for (let d = 1; d <= totalDays; d++) {
    const iso    = localIso(y, m, d);
    const isPast = iso < todayIso;
    let cls = 'cal-d';
    if (isPast)            cls += ' past';
    if (iso === todayIso)  cls += ' today';
    if (iso === S.selectedDate) cls += ' sel';
    const onclick = isPast ? '' : `onclick="selectDate('${iso}')"`;
    grid.innerHTML += `<div class="${cls}" ${onclick}>${d}</div>`;
  }
}

async function selectDate(iso) {
  S.selectedDate = iso;
  S.selectedTime = null;
  $('btn-to-confirm').disabled = true;
  $('selected-date').textContent = fmtDate(iso);
  $('slots-section').style.display = 'block';
  renderCalendar();
  await loadSlots();
}

async function loadSlots() {
  if (!S.selectedDate || !S.selectedService) return;
  $('time-grid').innerHTML = '<div class="dots-row"><span></span><span></span><span></span></div>';
  const slots = await fetch(
    `/api/public/master/${MASTER_ID}/slots?date=${S.selectedDate}&service_id=${S.selectedService.id}`,
    { headers: { 'ngrok-skip-browser-warning': '1' } }
  ).then(r => r.json()).catch(() => []);

  if (!slots.length) {
    $('time-grid').innerHTML = '<p style="color:var(--dim);font-size:13px;padding:8px 2px;grid-column:1/-1">Нет свободных слотов на эту дату</p>';
    return;
  }
  $('time-grid').innerHTML = slots.map(t =>
    `<div class="slot${t === S.selectedTime ? ' sel' : ''}" onclick="selectTime('${t}')">${t}</div>`
  ).join('');
}

function selectTime(t) {
  S.selectedTime = t;
  document.querySelectorAll('.slot').forEach(el => el.classList.remove('sel'));
  event.target.classList.add('sel');
  $('btn-to-confirm').disabled = false;
}

// ── Step 3: Confirm + name/phone ─────────────────────────────────────────────

function goToConfirm() {
  if (!S.selectedDate || !S.selectedTime) return;
  const svc    = S.selectedService;
  const prepay = svc.prepay || 0;

  $('confirm-svc').textContent   = svc.name;
  $('confirm-date').textContent  = fmtDate(S.selectedDate);
  $('confirm-time').textContent  = S.selectedTime;
  $('confirm-price').textContent = fmtPrice(svc.price);

  // Show prepay row only if prepay > 0
  if (prepay > 0) {
    $('confirm-prepay').textContent = fmtPrice(prepay);
    $('confirm-prepay-row').style.display = '';
  } else {
    $('confirm-prepay-row').style.display = 'none';
  }

  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    $('book-name').value = [u.first_name, u.last_name].filter(Boolean).join(' ');
  }

  const btn = $('btn-submit');
  btn.textContent = prepay > 0
    ? `Оплатить предоплату ${fmtPrice(prepay)} →`
    : 'Подтвердить запись';
  goStep(3);
}

function proceedFromConfirm() {
  const name  = $('book-name').value.trim();
  const phone = $('book-phone').value.trim();
  if (!name || !phone) { alert('Заполните имя и телефон'); return; }

  const prepay = S.selectedService.prepay || 0;

  if (prepay > 0) {
    const stars = Math.ceil(prepay / 2);
    $('pay-amount-label').textContent = fmtPrice(prepay);
    $('pay-stars-sub').textContent    = `≈ ${stars} ⭐ · Мгновенно через Telegram`;
    goStep(4);
  } else {
    submitFreeBooking();
  }
}

async function submitFreeBooking() {
  const btn = $('btn-submit');
  btn.disabled = true; btn.textContent = 'Отправка…';
  const tgUser = tg?.initDataUnsafe?.user;
  try {
    await fetch(`/api/public/bookings/${MASTER_ID}`, {
      method: 'POST',
      headers: { 'ngrok-skip-browser-warning': '1', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_name:       $('book-name').value.trim(),
        client_phone:      $('book-phone').value.trim(),
        service_id:        S.selectedService.id,
        date:              S.selectedDate,
        time:              S.selectedTime,
        telegram_username: tgUser?.username  || null,
        telegram_user_id:  tgUser?.id        || null,
      })
    }).then(r => { if (!r.ok) throw new Error(); return r.json(); });

    goStep(5);
    $('success-details').innerHTML = successHtml();
    if (tg) setTimeout(() => tg.close(), 3500);
  } catch {
    btn.disabled = false;
    btn.textContent = 'Подтвердить запись';
    alert('Ошибка. Слот уже занят или попробуйте позже.');
  }
}

// ── Step 4: Payment ───────────────────────────────────────────────────────────

async function payWithStars() {
  $('pay-stars-btn').style.pointerEvents = 'none';
  $('pay-card-btn').style.pointerEvents  = 'none';
  $('pay-loading').style.display = 'block';

  const tgUser = tg?.initDataUnsafe?.user;
  const prepay = S.selectedService.prepay || 0;
  try {
    const res = await fetch(`/api/public/bookings/${MASTER_ID}/stars_invoice`, {
      method: 'POST',
      headers: { 'ngrok-skip-browser-warning': '1', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        service_name:      S.selectedService.name,
        service_id:        S.selectedService.id,
        date:              S.selectedDate,
        date_fmt:          fmtDate(S.selectedDate),
        time:              S.selectedTime,
        amount:            prepay,
        client_name:       $('book-name').value.trim(),
        client_phone:      $('book-phone').value.trim(),
        telegram_username: tgUser?.username || null,
        telegram_user_id:  tgUser?.id       || null,
      })
    }).then(r => { if (!r.ok) throw new Error(); return r.json(); });

    $('pay-loading').style.display = 'none';

    if (!tg) { alert('Stars-оплата доступна только в Telegram'); return; }

    tg.openInvoice(res.invoice_url, (status) => {
      if (status === 'paid') {
        goStep(5);
        $('success-details').innerHTML =
          successHtml() +
          `<div class="success-row"><span>⭐</span><span>Оплачено Stars</span></div>`;
        if (tg) setTimeout(() => tg.close(), 4000);
      } else if (status === 'cancelled' || status === 'failed') {
        _resetPayBtns();
      }
    });
  } catch {
    $('pay-loading').style.display = 'none';
    _resetPayBtns();
    alert('Ошибка создания инвойса. Попробуйте позже.');
  }
}

async function payWithCard() {
  $('pay-stars-btn').style.pointerEvents = 'none';
  $('pay-card-btn').style.pointerEvents  = 'none';
  $('pay-loading').style.display = 'block';

  const tgUser = tg?.initDataUnsafe?.user;
  const prepay = S.selectedService.prepay || 0;
  try {
    const res = await fetch(`/api/public/bookings/${MASTER_ID}/pay_yookassa`, {
      method: 'POST',
      headers: { 'ngrok-skip-browser-warning': '1', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_name:       $('book-name').value.trim(),
        client_phone:      $('book-phone').value.trim(),
        service_id:        S.selectedService.id,
        service_name:      S.selectedService.name,
        date:              S.selectedDate,
        time:              S.selectedTime,
        amount:            prepay,
        telegram_username: tgUser?.username || null,
        telegram_user_id:  tgUser?.id       || null,
      })
    }).then(r => { if (!r.ok) throw new Error(); return r.json(); });

    $('pay-loading').style.display = 'none';

    if (tg) {
      tg.openLink(res.payment_url);
    } else {
      window.location.href = res.payment_url;
    }
  } catch {
    $('pay-loading').style.display = 'none';
    _resetPayBtns();
    alert('Ошибка создания платежа. Попробуйте позже.');
  }
}

function _resetPayBtns() {
  $('pay-stars-btn').style.pointerEvents = '';
  $('pay-card-btn').style.pointerEvents  = '';
}

// ── Confetti ──────────────────────────────────────────────────────────────────

function launchConfetti() {
  const box = $('confetti');
  if (!box) return;
  box.innerHTML = '';
  const colors = ['#2563eb','#3b82f6','#60a5fa','#0ea5e9','#06b6d4','#38bdf8'];
  for (let i = 0; i < 60; i++) {
    const el  = document.createElement('div');
    el.className = 'confetto';
    const sz = 5 + Math.random() * 6;
    el.style.cssText = `
      left:${Math.random()*100}%;
      top:${-8-Math.random()*12}px;
      width:${sz}px;height:${sz}px;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-duration:${1.6+Math.random()*2}s;
      animation-delay:${Math.random()*.8}s;
      border-radius:${Math.random()>.5?'50%':'2px'};`;
    box.appendChild(el);
  }
}

document.addEventListener('DOMContentLoaded', init);
