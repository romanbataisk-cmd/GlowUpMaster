const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); tg.setHeaderColor?.('#07111f'); tg.setBackgroundColor?.('#07111f'); }

const studios = [
  { id: 1, name: 'Alina Morozova', category: 'hair', cover: 'cover-peach', rating: '4.9', reviews: 126, distance: '0.4 км', walk: '6 мин', tags: ['Стрижки', 'Окрашивание', 'Укладки'], slot: 'Сегодня, 14:30', price: 'от 2 400 ₽', verified: true },
  { id: 2, name: 'Luna Studio', category: 'nails', cover: 'cover-violet', rating: '4.8', reviews: 204, distance: '0.8 км', walk: '11 мин', tags: ['Маникюр', 'Педикюр', 'Дизайн'], slot: 'Сегодня, 16:00', price: 'от 1 900 ₽', verified: true },
  { id: 3, name: 'Nude Office', category: 'brows', cover: 'cover-aqua', rating: '5.0', reviews: 89, distance: '1.2 км', walk: '16 мин', tags: ['Брови', 'Ресницы', 'Макияж'], slot: 'Сегодня, 18:20', price: 'от 1 500 ₽', verified: true },
  { id: 4, name: 'Balance Massage', category: 'massage', cover: 'cover-violet', rating: '4.9', reviews: 71, distance: '1.7 км', walk: '7 мин на авто', tags: ['Массаж', 'SPA', 'Лимфодренаж'], slot: 'Завтра, 10:00', price: 'от 3 200 ₽', verified: false }
];

const saved = new Set(JSON.parse(localStorage.getItem('glowup-favorites') || '[]'));
const savedCity = localStorage.getItem('glowup-city') || 'Москва';
let currentFilter = 'all';
let gridMode = false;

const studioCard = studio => `
  <article class="studio-card" data-category="${studio.category}" data-id="${studio.id}">
    <div class="studio-cover ${studio.cover}">
      <span class="verified">${studio.verified ? '✓ ПРОВЕРЕНО GLOWUP' : 'НОВАЯ СТУДИЯ'}</span>
      <button class="favorite-button ${saved.has(studio.id) ? 'saved' : ''}" type="button" data-favorite="${studio.id}" aria-label="Добавить в избранное">${saved.has(studio.id) ? '♥' : '♡'}</button>
    </div>
    <div class="studio-body">
      <div class="studio-title-row"><div><h3>${studio.name}</h3><div class="studio-meta"><span>${studio.distance}</span><span>${studio.walk}</span><span>${studio.reviews} отзывов</span></div></div><span class="rating">★ ${studio.rating}</span></div>
      <div class="studio-tags">${studio.tags.map(tag => `<span>${tag}</span>`).join('')}</div>
      <div class="studio-bottom"><div class="next-slot"><small>Ближайшее окно · ${studio.price}</small><strong>${studio.slot}</strong></div><a href="/book.html?master=100">Выбрать время</a></div>
    </div>
  </article>`;

function bindFavorites(scope) {
  scope.querySelectorAll('[data-favorite]').forEach(button => button.addEventListener('click', () => {
    const id = Number(button.dataset.favorite);
    if (saved.has(id)) { saved.delete(id); showToast('Удалено из избранного'); }
    else { saved.add(id); showToast('Студия сохранена ♥'); }
    localStorage.setItem('glowup-favorites', JSON.stringify([...saved]));
    renderStudios(); renderFavorites();
  }));
}

function renderStudios() {
  const list = document.getElementById('studio-list');
  const filtered = studios.filter(studio => currentFilter === 'all' || studio.category === currentFilter);
  list.innerHTML = filtered.map(studioCard).join('');
  list.classList.toggle('grid-mode', gridMode);
  document.getElementById('empty-filter').classList.toggle('show', filtered.length === 0);
  bindFavorites(list);
}

function renderFavorites() {
  const list = document.getElementById('favorites-list');
  const favorites = studios.filter(studio => saved.has(studio.id));
  list.innerHTML = favorites.map(studioCard).join('');
  document.getElementById('favorites-empty').style.display = favorites.length ? 'none' : '';
  bindFavorites(list);
}

function showView(name) {
  document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
  document.querySelectorAll('.client-nav button').forEach(button => button.classList.toggle('active', button.dataset.view === name));
  document.getElementById(`${name}-view`)?.classList.add('active');
  if (name === 'favorites') renderFavorites();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  tg?.HapticFeedback?.selectionChanged();
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message; toast.classList.add('show');
  clearTimeout(showToast.timer); showToast.timer = setTimeout(() => toast.classList.remove('show'), 1800);
}

function setSheet(open) {
  document.getElementById('city-sheet').classList.remove('open');
  document.getElementById('match-sheet').classList.toggle('open', open);
  document.getElementById('sheet-backdrop').classList.toggle('show', open);
}

function setCitySheet(open) {
  document.getElementById('match-sheet').classList.remove('open');
  document.getElementById('city-sheet').classList.toggle('open', open);
  document.getElementById('sheet-backdrop').classList.toggle('show', open);
  if (open) setTimeout(() => document.getElementById('city-search').focus(), 220);
}

function selectCity(city, count) {
  localStorage.setItem('glowup-city', city);
  document.getElementById('current-location').textContent = city;
  document.getElementById('online-studios').innerHTML = `<i></i> ${Math.max(8, Math.round(Number(count) / 5))} студий онлайн`;
  document.querySelectorAll('[data-city]').forEach(button => button.classList.toggle('selected', button.dataset.city === city));
  setCitySheet(false);
  showToast(`Теперь ищем в городе ${city}`);
  tg?.HapticFeedback?.notificationOccurred('success');
}

document.querySelectorAll('.client-nav button').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => showView(button.dataset.go)));
document.querySelectorAll('.category').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.category').forEach(item => item.classList.remove('active'));
  button.classList.add('active'); currentFilter = button.dataset.filter; renderStudios();
}));
document.getElementById('view-switch').addEventListener('click', event => { gridMode = !gridMode; event.currentTarget.textContent = gridMode ? '☷' : '▦'; showToast(gridMode ? 'Компактный вид' : 'Большие карточки'); });
document.getElementById('smart-match-button').addEventListener('click', () => setSheet(true));
document.getElementById('sheet-close').addEventListener('click', () => setSheet(false));
document.getElementById('sheet-backdrop').addEventListener('click', () => { setSheet(false); setCitySheet(false); });
document.querySelectorAll('[data-match]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-match]').forEach(item => item.classList.remove('selected'));
  button.classList.add('selected'); document.getElementById('match-next').disabled = false;
}));
document.getElementById('match-next').addEventListener('click', () => {
  currentFilter = document.querySelector('[data-match].selected')?.dataset.match || 'all';
  document.querySelectorAll('.category').forEach(item => item.classList.toggle('active', item.dataset.filter === currentFilter));
  renderStudios(); setSheet(false); showToast('Нашли идеальные варианты ✦');
  document.getElementById('studio-list').scrollIntoView({ behavior: 'smooth', block: 'start' });
});
document.getElementById('location-button').addEventListener('click', () => setCitySheet(true));
document.getElementById('city-close').addEventListener('click', () => setCitySheet(false));
document.querySelectorAll('[data-city]').forEach(button => button.addEventListener('click', () => selectCity(button.dataset.city, button.dataset.count)));
document.getElementById('city-search').addEventListener('input', event => {
  const query = event.target.value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('[data-city]').forEach(button => {
    const matches = button.dataset.city.toLowerCase().includes(query);
    button.hidden = !matches; if (matches) visible += 1;
  });
  document.getElementById('city-empty').classList.toggle('show', visible === 0);
});
document.getElementById('map-toggle').addEventListener('click', () => showToast('Карта появится в следующем обновлении'));
document.querySelectorAll('.studio-pin').forEach(pin => pin.addEventListener('click', () => document.querySelector(`[data-id="${pin.dataset.studio}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })));

document.getElementById('current-location').textContent = savedCity;
document.querySelectorAll('[data-city]').forEach(button => button.classList.toggle('selected', button.dataset.city === savedCity));
renderStudios(); renderFavorites();
