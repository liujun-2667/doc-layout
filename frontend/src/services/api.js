import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const taskApi = {
  list: (skip = 0, limit = 100) =>
    api.get('/tasks', { params: { skip, limit } }).then((r) => r.data),

  create: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    return api
      .post('/tasks', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
      })
      .then((r) => r.data);
  },

  get: (taskId) => api.get(`/tasks/${taskId}`).then((r) => r.data),

  retry: (taskId) =>
    api.post(`/tasks/${taskId}/retry`).then((r) => r.data),

  delete: (taskId) =>
    api.delete(`/tasks/${taskId}`).then((r) => r.data),
};

export const pageApi = {
  get: (pageId) => api.get(`/pages/${pageId}`).then((r) => r.data),

  getElements: (pageId) =>
    api.get(`/pages/${pageId}/elements`).then((r) => r.data),

  reprocess: (pageId, rotationAngle) =>
    api
      .post(`/analysis/pages/${pageId}/reprocess`, { rotation_angle: rotationAngle })
      .then((r) => r.data),
};

export const analysisApi = {
  updateElement: (elementId, data) =>
    api.put(`/analysis/elements/${elementId}`, data).then((r) => r.data),

  deleteElement: (elementId) =>
    api.delete(`/analysis/elements/${elementId}`).then((r) => r.data),

  mergeElements: (pageId, elementIds) =>
    api
      .post(`/analysis/pages/${pageId}/merge-elements`, { element_ids: elementIds })
      .then((r) => r.data),

  splitElement: (elementId, splitType, splitPosition) =>
    api
      .post(`/analysis/elements/${elementId}/split`, {
        split_type: splitType,
        split_position: splitPosition,
      })
      .then((r) => r.data),

  reorderElements: (pageId, elementOrder) =>
    api
      .post(`/analysis/pages/${pageId}/reorder-elements`, { element_order: elementOrder })
      .then((r) => r.data),
};

export const outputApi = {
  get: (taskId, format) =>
    api
      .get(`/output/${taskId}`, {
        params: { format },
        responseType: 'blob',
      })
      .then((r) => r.data),
};

export default api;
