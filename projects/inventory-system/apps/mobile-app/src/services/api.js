/**
 * API Service
 * Handles all API communication with the backend
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getApiUrl, API_ENDPOINTS } from '../config/api';

const api = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  async login(username, password, deviceId) {
    try {
      const response = await api.post(getApiUrl(API_ENDPOINTS.LOGIN), {
        username,
        password,
        device_id: deviceId,
      });
      
      if (response.data.success) {
        await AsyncStorage.setItem('auth_token', response.data.token);
        await AsyncStorage.setItem('username', response.data.username);
        await AsyncStorage.setItem('franchise', response.data.franchise);
        await AsyncStorage.setItem('role', response.data.role);
      }
      
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },
  
  async validateToken() {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      if (!token) return { valid: false };
      
      const response = await api.post(getApiUrl(API_ENDPOINTS.VALIDATE), {
        token,
      });
      
      return response.data;
    } catch (error) {
      return { valid: false };
    }
  },
  
  async logout() {
    await AsyncStorage.multiRemove(['auth_token', 'username', 'franchise', 'role']);
  },
};

export const restockService = {
  async detectPhoto(photoUri) {
    try {
      const formData = new FormData();
      formData.append('photo', {
        uri: photoUri,
        type: 'image/jpeg',
        name: 'photo.jpg',
      });
      
      const response = await axios.post(
        getApiUrl(API_ENDPOINTS.DETECT),
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            Authorization: `Bearer ${await AsyncStorage.getItem('auth_token')}`,
          },
        }
      );
      
      return response.data;
    } catch (error) {
      console.error('Detection error:', error);
      throw error;
    }
  },
  
  async uploadSubmission(photos, station, product, notes, location) {
    try {
      const formData = new FormData();
      
      // Add photos
      photos.forEach((photo, index) => {
        formData.append(`photo_${index}`, {
          uri: photo.uri,
          type: 'image/jpeg',
          name: `photo_${index}.jpg`,
        });
      });
      
      // Add metadata
      formData.append('station', station);
      formData.append('product', product);
      if (notes) formData.append('notes', notes);
      if (location) {
        formData.append('latitude', location.latitude.toString());
        formData.append('longitude', location.longitude.toString());
      }
      
      const token = await AsyncStorage.getItem('auth_token');
      const response = await axios.post(
        getApiUrl(API_ENDPOINTS.UPLOAD),
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  },
  
  async getSubmissions() {
    try {
      const response = await api.get(getApiUrl(API_ENDPOINTS.SUBMISSIONS));
      return response.data;
    } catch (error) {
      console.error('Get submissions error:', error);
      throw error;
    }
  },
};

export const notificationService = {
  async getNotifications() {
    try {
      const response = await api.get(getApiUrl(API_ENDPOINTS.NOTIFICATIONS));
      return response.data;
    } catch (error) {
      console.error('Get notifications error:', error);
      throw error;
    }
  },
  
  async getNotificationCount() {
    try {
      const response = await api.get(getApiUrl(API_ENDPOINTS.NOTIFICATION_COUNT));
      return response.data;
    } catch (error) {
      return { count: 0 };
    }
  },
  
  async markAsRead(notificationId) {
    try {
      const response = await api.post(getApiUrl(API_ENDPOINTS.NOTIFICATION_READ), {
        notification_id: notificationId,
      });
      return response.data;
    } catch (error) {
      console.error('Mark read error:', error);
      throw error;
    }
  },
};


