(() => {
  const isLocal = ['localhost', '127.0.0.1'].includes(location.hostname);
  if (!isLocal) return;

  const originalFetch = window.fetch.bind(window);
  const today = new Date().toISOString().slice(0, 10);
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  const state = {
    master: {
      telegram_id: 100, full_name: 'Алина Морозова', specialty: 'Стилист по волосам · частная студия',
      bio: 'Естественные формы и цвет, которые легко носить каждый день.', phone: '+7 (999) 248-16-04',
      access: { mode: 'trial', days_left: 12 },
      stats: { today_bookings: 4, week_bookings: 18, total_clients: 126, week_revenue: 48600 }
    },
    services: [
      { id: 1, name: 'Стрижка + укладка', description: 'Форма, мытьё и лёгкая укладка', duration: 75, price: 3200, prepay: 500, is_active: true },
      { id: 2, name: 'Окрашивание в один тон', description: 'Материалы включены', duration: 150, price: 6800, prepay: 1000, is_active: true },
      { id: 3, name: 'Экспресс-укладка', description: 'На встречу или событие', duration: 45, price: 2400, prepay: 0, is_active: true }
    ],
    clients: [
      { id: 1, name: 'Мария Крылова', phone: '+7 916 808-42-11', notes: 'Предпочитает утро' },
      { id: 2, name: 'Лера Соколова', phone: '+7 985 110-32-80', notes: 'Формула цвета 8.13' },
      { id: 3, name: 'Ксения Белова', phone: '+7 903 614-09-17', notes: 'Новый клиент' }
    ],
    bookings: [
      { id: 1, client_id: 1, client_name: 'Мария Крылова', client_phone: '+7 916 808-42-11', service_name: 'Стрижка + укладка', service_id: 1, date: today, time: '10:00', price: 3200, status: 'confirmed' },
      { id: 2, client_id: 2, client_name: 'Лера Соколова', client_phone: '+7 985 110-32-80', service_name: 'Окрашивание в один тон', service_id: 2, date: today, time: '12:00', price: 6800, status: 'confirmed' },
      { id: 3, client_id: 3, client_name: 'Ксения Белова', client_phone: '+7 903 614-09-17', service_name: 'Экспресс-укладка', service_id: 3, date: today, time: '16:30', price: 2400, status: 'pending' },
      { id: 4, client_name: 'Настя Воронова', client_phone: '+7 926 701-55-24', service_name: 'Стрижка + укладка', service_id: 1, date: today, time: '18:00', price: 3200, status: 'pending' },
      { id: 5, client_id: 1, client_name: 'Мария Крылова', client_phone: '+7 916 808-42-11', service_name: 'Экспресс-укладка', service_id: 3, date: tomorrow, time: '11:30', price: 2400, status: 'confirmed' }
    ]
  };

  const json = data => new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  const bodyOf = async options => options?.body ? JSON.parse(options.body) : {};

  async function demoResponse(input, options = {}) {
    const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
    const path = url.pathname;
    const method = (options.method || 'GET').toUpperCase();
    const body = await bodyOf(options);
    if (path === '/api/config') return json({ bot_username: '', webapp_url: location.origin });
    if (path === '/api/master/me') return json(state.master);
    if (path === '/api/master/profile' && method === 'PUT') { Object.assign(state.master, body); return json(state.master); }
    if (/^\/api\/public\/master\/\d+$/.test(path)) return json(state.master);
    if (/^\/api\/public\/master\/\d+\/services$/.test(path)) return json(state.services.filter(s => s.is_active));
    if (path.includes('/slots')) return json(['09:30', '11:00', '12:30', '14:00', '16:30', '18:00']);
    if (path === '/api/services' && method === 'GET') return json(state.services);
    if (path === '/api/services' && method === 'POST') { const item = { id: Date.now(), is_active: true, ...body }; state.services.push(item); return json(item); }
    const serviceMatch = path.match(/^\/api\/services\/(\d+)$/);
    if (serviceMatch) {
      const index = state.services.findIndex(s => s.id === Number(serviceMatch[1]));
      if (method === 'DELETE') { if (index >= 0) state.services.splice(index, 1); return json({ ok: true }); }
      if (index >= 0) { Object.assign(state.services[index], body); return json(state.services[index]); }
    }
    if (path === '/api/clients' && method === 'GET') {
      const query = (url.searchParams.get('search') || '').toLowerCase();
      return json(state.clients.filter(c => !query || `${c.name} ${c.phone}`.toLowerCase().includes(query)));
    }
    if (path === '/api/clients' && method === 'POST') { const item = { id: Date.now(), ...body }; state.clients.push(item); return json(item); }
    if (path === '/api/bookings' && method === 'GET') {
      const date = url.searchParams.get('date'); return json(state.bookings.filter(b => !date || b.date === date));
    }
    if ((path === '/api/bookings' || /^\/api\/public\/bookings\/\d+$/.test(path)) && method === 'POST') {
      const service = state.services.find(s => s.id === body.service_id) || {};
      const item = { id: Date.now(), status: 'pending', service_name: service.name, price: service.price || 0, ...body };
      state.bookings.push(item); return json(item);
    }
    const statusMatch = path.match(/^\/api\/bookings\/(\d+)\/status$/);
    if (statusMatch && method === 'PUT') { const item = state.bookings.find(b => b.id === Number(statusMatch[1])); if (item) item.status = body.status; return json(item || {}); }
    if (path === '/api/subscription' || path === '/api/subscription/price') return json({ mode: 'trial', days_left: 12, rub: 299 });
    return json({ ok: true });
  }

  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
    if (!url.pathname.startsWith('/api/')) return originalFetch(input, options);
    try {
      const response = await originalFetch(input, options);
      if (response.status !== 404) return response;
    } catch (_) {
      // Local static preview intentionally falls through to deterministic demo data.
    }
    return demoResponse(input, options);
  };
})();
