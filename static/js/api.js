const BASE = '';

function getAuth() {
  const tg = window.Telegram?.WebApp;
  if (tg?.initData) return `tma ${tg.initData}`;
  return `tma dev:${window._devUserId || 0}`;
}

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Authorization': getAuth(),
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': '1'
    }
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Ошибка запроса');
  }
  return res.json();
}

const api = {
  // Master
  getMe: () => request('GET', '/api/master/me'),
  updateProfile: (data) => request('PUT', '/api/master/profile', data),

  // Services
  getServices: () => request('GET', '/api/services'),
  addService: (d) => request('POST', '/api/services', d),
  updateService: (id, d) => request('PUT', `/api/services/${id}`, d),
  deleteService: (id) => request('DELETE', `/api/services/${id}`),

  // Schedule
  getSchedule: () => request('GET', '/api/schedule'),
  saveSchedule: (d) => request('PUT', '/api/schedule', d),
  getDaysOff: () => request('GET', '/api/days-off'),
  toggleDayOff: (date) => request('POST', `/api/days-off/${date}`),

  // Bookings
  getBookings: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([,v]) => v)).toString();
    return request('GET', `/api/bookings${q ? '?' + q : ''}`);
  },
  addBooking: (d) => request('POST', '/api/bookings', d),
  setBookingStatus: (id, status) => request('PUT', `/api/bookings/${id}/status`, { status }),
  getSlots: (date, service_id) => request('GET', `/api/bookings/slots?date=${date}&service_id=${service_id}`),

  // Clients
  getClients: (search = '') => request('GET', `/api/clients${search ? '?search=' + encodeURIComponent(search) : ''}`),
  addClient: (d) => request('POST', '/api/clients', d),
  updateClient: (id, d) => request('PUT', `/api/clients/${id}`, d),
  deleteClient: (id) => request('DELETE', `/api/clients/${id}`),

  // Subscription
  getSubscription: () => request('GET', '/api/subscription'),
};
