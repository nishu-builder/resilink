import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/',
});

console.log('api', api.defaults.baseURL);

export default api; 