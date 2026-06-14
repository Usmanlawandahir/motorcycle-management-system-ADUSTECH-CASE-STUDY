const API_BASE = '';

async function apiRequest(endpoint, options = {}) {
  const config = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }
    return data;
  } catch (error) {
    if (error.message === 'Failed to fetch') {
      throw new Error('Unable to connect to server. Please ensure the backend is running.');
    }
    throw error;
  }
}

const API = {
  register: (data) => apiRequest('/api/auth/register', { method: 'POST', body: data }),
  login: (data) => apiRequest('/api/auth/login', { method: 'POST', body: data }),
  logout: () => apiRequest('/api/auth/logout', { method: 'POST' }),
  getMe: () => apiRequest('/api/auth/me'),

  getAvailableRiders: (lat, lng) => {
    let url = '/api/riders/available';
    if (lat && lng) url += `?lat=${lat}&lng=${lng}`;
    return apiRequest(url);
  },
  getRider: (id) => apiRequest(`/api/riders/${id}`),
  toggleAvailability: () => apiRequest('/api/riders/availability', { method: 'PUT' }),
  updateLocation: (data) => apiRequest('/api/riders/location', { method: 'PUT', body: data }),

  createBooking: (data) => apiRequest('/api/bookings', { method: 'POST', body: data }),
  getMyBookings: () => apiRequest('/api/bookings/my'),
  updateBookingStatus: (id, status) => apiRequest(`/api/bookings/${id}/status`, { method: 'PUT', body: { status } }),

  getCampusLocations: () => apiRequest('/api/locations'),

  adminGetRiders: () => apiRequest('/api/admin/riders'),
  adminUpdateRiderStatus: (id, status) => apiRequest(`/api/admin/riders/${id}/status`, { method: 'PUT', body: { status } }),
  adminGetStats: () => apiRequest('/api/admin/stats')
};

function showAlert(container, message, type = 'error') {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  container.prepend(alert);
  setTimeout(() => alert.remove(), 5000);
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString('en-NG', {
    dateStyle: 'medium', timeStyle: 'short'
  });
}

function getInitials(name) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

function checkAuth(requiredRole) {
  const user = JSON.parse(sessionStorage.getItem('user') || 'null');
  if (!user) {
    window.location.href = '/login.html';
    return null;
  }
  if (requiredRole && user.role !== requiredRole) {
    window.location.href = '/';
    return null;
  }
  return user;
}

function saveUser(user) {
  sessionStorage.setItem('user', JSON.stringify(user));
}

function clearUser() {
  sessionStorage.removeItem('user');
}
