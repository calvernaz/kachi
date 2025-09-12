import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/customers',
      name: 'customers',
      component: () => import('../views/CustomersView.vue'),
    },
    {
      path: '/customers/:id',
      name: 'customer-detail',
      component: () => import('../views/CustomerDetailView.vue'),
    },
    {
      path: '/usage',
      name: 'usage',
      component: () => import('../views/AboutView.vue'), // Placeholder for now
    },
  ],
})

export default router
