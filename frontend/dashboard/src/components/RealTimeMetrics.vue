<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    <!-- Total Customers -->
    <div class="bg-white rounded-lg shadow p-6 relative overflow-hidden">
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
            <dd class="text-lg font-medium text-gray-900">
              <AnimatedNumber :value="metrics?.total_customers || 0" />
            </dd>
            <dd class="text-xs text-gray-400">
              {{ metrics?.active_customers || 0 }} active
            </dd>
          </dl>
        </div>
      </div>
      <div v-if="loading" class="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
      </div>
    </div>

    <!-- Monthly Revenue -->
    <div class="bg-white rounded-lg shadow p-6 relative overflow-hidden">
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
            <dd class="text-lg font-medium text-gray-900">
              €<AnimatedNumber :value="Number(metrics?.monthly_revenue || 0)" :decimals="0" />
            </dd>
            <dd class="text-xs text-gray-400">
              €{{ formatNumber(Number(metrics?.daily_revenue || 0)) }} today
            </dd>
          </dl>
        </div>
      </div>
      <div v-if="loading" class="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
      </div>
    </div>

    <!-- API Calls Today -->
    <div class="bg-white rounded-lg shadow p-6 relative overflow-hidden">
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
            <dd class="text-lg font-medium text-gray-900">
              <AnimatedNumber :value="metrics?.total_api_calls_today || 0" />
            </dd>
            <dd class="text-xs text-gray-400">
              {{ formatNumber(metrics?.total_workflows_today || 0) }} workflows
            </dd>
          </dl>
        </div>
      </div>
      <div v-if="loading" class="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
      </div>
    </div>

    <!-- System Health -->
    <div class="bg-white rounded-lg shadow p-6 relative overflow-hidden">
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
            <dt class="text-sm font-medium text-gray-500 truncate">System Health</dt>
            <dd class="text-lg font-medium text-gray-900">
              <AnimatedNumber :value="metrics?.system_health_score || 0" :decimals="1" />%
            </dd>
            <dd class="text-xs text-gray-400">
              {{ formatNumber(metrics?.average_response_time || 0) }}ms avg
            </dd>
          </dl>
        </div>
      </div>
      <!-- Health indicator -->
      <div class="absolute top-2 right-2">
        <div
          class="w-3 h-3 rounded-full"
          :class="healthIndicatorColor"
        ></div>
      </div>
      <div v-if="loading" class="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AnimatedNumber from './AnimatedNumber.vue'

interface DashboardMetrics {
  total_customers: number
  active_customers: number
  monthly_revenue: string
  daily_revenue: string
  total_api_calls_today: number
  total_workflows_today: number
  average_response_time: number
  system_health_score: number
}

const metrics = ref<DashboardMetrics>()
const loading = ref(true)
const refreshInterval = ref<number>()

const healthIndicatorColor = computed(() => {
  const score = metrics.value?.system_health_score || 0
  if (score >= 95) return 'bg-green-400 animate-pulse'
  if (score >= 85) return 'bg-yellow-400'
  return 'bg-red-400 animate-pulse'
})

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString()
}

async function fetchMetrics() {
  try {
    const response = await fetch('http://localhost:8002/api/metrics/dashboard')
    if (!response.ok) throw new Error('Failed to fetch metrics')

    metrics.value = await response.json()
  } catch (error) {
    console.error('Error fetching dashboard metrics:', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchMetrics()

  // Set up auto-refresh every 30 seconds
  refreshInterval.value = setInterval(fetchMetrics, 30000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>
