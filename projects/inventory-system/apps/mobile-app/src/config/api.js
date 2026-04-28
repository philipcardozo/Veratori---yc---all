/**
 * API Configuration
 * Update API_BASE_URL with your server address
 */

export const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8080'  // Development
  : 'http://your-server-ip:8080';  // Production - UPDATE THIS

export const API_ENDPOINTS = {
  // Authentication
  LOGIN: '/api/restock/login',
  VALIDATE: '/api/restock/validate',
  
  // Submissions
  UPLOAD: '/api/restock/upload',
  DETECT: '/api/restock/detect',
  SUBMISSIONS: '/api/restock/submissions',
  
  // Notifications
  NOTIFICATIONS: '/api/restock/notifications',
  NOTIFICATION_COUNT: '/api/restock/notifications/count',
  NOTIFICATION_READ: '/api/restock/notifications/read',
  
  // Photos
  PHOTO: '/api/restock/photo',
};

export const getApiUrl = (endpoint) => {
  return `${API_BASE_URL}${endpoint}`;
};


