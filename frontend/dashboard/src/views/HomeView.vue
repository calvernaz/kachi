<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCustomerStore } from '@/stores/customer'
import RealTimeMetrics from '@/components/RealTimeMetrics.vue'
import UsageTrendChart from '@/components/UsageTrendChart.vue'

const customerStore = useCustomerStore()
const loading = ref(true)

onMounted(async () => {
  try {
    await customerStore.fetchCustomers()
  } catch (error) {
    console.error('Failed to load customers:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow p-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-2">Usage Dashboard</h1>
      <p class="text-gray-600">Monitor customer usage, billing, and system health</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="space-y-6">
      <!-- Real-time Metrics -->
      <RealTimeMetrics />

      <!-- Usage Trends Chart -->
      <UsageTrendChart />

      <!-- Recent Activity -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Customer Usage Overview -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900">Customer Overview</h2>
          </div>
          <div class="p-6">
            <div v-if="customerStore.customers.length === 0" class="text-center py-8">
              <p class="text-gray-500">No customers found</p>
            </div>
            <div v-else class="space-y-4">
              <div
                v-for="customer in customerStore.customers.slice(0, 5)"
                :key="customer.id"
                class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <p class="font-medium text-gray-900">{{ customer.name }}</p>
                  <p class="text-sm text-gray-500">{{ customer.currency }}</p>
                </div>
                <RouterLink
                  :to="`/customers/${customer.id}`"
                  class="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View Details
                </RouterLink>
              </div>
              <RouterLink
                to="/customers"
                class="block text-center text-blue-600 hover:text-blue-800 text-sm font-medium mt-4"
              >
                View All Customers
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- System Status -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-6 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900">System Status</h2>
          </div>
          <div class="p-6">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-gray-600">Ingest API</span>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Healthy
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-600">Rating Engine</span>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Healthy
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-600">Lago Integration</span>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Healthy
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-600">Database</span>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Healthy
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
