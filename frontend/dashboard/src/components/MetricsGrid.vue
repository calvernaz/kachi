<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    <!-- Total Customers -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 bg-blue-100 rounded-md flex items-center justify-center">
            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
            </svg>
          </div>
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">Total Customers</dt>
            <dd class="text-lg font-medium text-gray-900">{{ metrics.totalCustomers }}</dd>
          </dl>
        </div>
      </div>
    </div>

    <!-- Monthly Revenue -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 bg-green-100 rounded-md flex items-center justify-center">
            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
            </svg>
          </div>
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">Monthly Revenue</dt>
            <dd class="text-lg font-medium text-gray-900">€{{ formatNumber(metrics.monthlyRevenue) }}</dd>
          </dl>
        </div>
      </div>
    </div>

    <!-- Active Workflows -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 bg-yellow-100 rounded-md flex items-center justify-center">
            <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">Active Workflows</dt>
            <dd class="text-lg font-medium text-gray-900">{{ formatNumber(metrics.activeWorkflows) }}</dd>
          </dl>
        </div>
      </div>
    </div>

    <!-- API Calls Today -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 bg-purple-100 rounded-md flex items-center justify-center">
            <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">API Calls Today</dt>
            <dd class="text-lg font-medium text-gray-900">{{ formatNumber(metrics.apiCallsToday) }}</dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Metrics {
  totalCustomers: number
  monthlyRevenue: number
  activeWorkflows: number
  apiCallsToday: number
}

const metrics = ref<Metrics>({
  totalCustomers: 0,
  monthlyRevenue: 0,
  activeWorkflows: 0,
  apiCallsToday: 0,
})

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString()
}

onMounted(() => {
  // Mock data - in production this would come from API
  metrics.value = {
    totalCustomers: 42,
    monthlyRevenue: 125000,
    activeWorkflows: 1250,
    apiCallsToday: 45000,
  }
})
</script>
