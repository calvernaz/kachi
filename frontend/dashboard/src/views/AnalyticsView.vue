<template>
  <div class="min-h-screen bg-slate-50 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-slate-900">Advanced Analytics</h1>
            <p class="mt-2 text-slate-600">
              Deep insights into customer behavior, usage patterns, and system health
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <button
              @click="refreshAllData"
              :disabled="refreshing"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <svg v-if="refreshing" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              <span>Refresh All</span>
            </button>
            <div class="text-sm text-slate-500">
              Last updated: {{ lastUpdated }}
            </div>
          </div>
        </div>
      </div>

      <!-- Analytics Tabs -->
      <div class="mb-8">
        <div class="border-b border-gray-200">
          <nav class="-mb-px flex space-x-8">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2',
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              ]"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path v-if="tab.icon === 'chart-bar'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                <path v-else-if="tab.icon === 'users'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
                <path v-else-if="tab.icon === 'trending-up'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                <path v-else-if="tab.icon === 'exclamation-triangle'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
              <span>{{ tab.name }}</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Tab Content -->
      <div class="space-y-8">
        <!-- Customer Segmentation Tab -->
        <div v-if="activeTab === 'segmentation'">
          <CustomerSegmentation />
        </div>

        <!-- Usage Forecasting Tab -->
        <div v-if="activeTab === 'forecasting'">
          <UsageForecasting />
        </div>

        <!-- Anomaly Detection Tab -->
        <div v-if="activeTab === 'anomalies'">
          <AnomalyDetection />
        </div>

        <!-- Overview Tab - All Components -->
        <div v-if="activeTab === 'overview'" class="space-y-8">
          <!-- Quick Stats Grid -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
                    </svg>
                  </div>
                </div>
                <div class="ml-4">
                  <p class="text-sm font-medium text-gray-600">Total Customers</p>
                  <p class="text-2xl font-bold text-gray-900">{{ overviewStats.totalCustomers }}</p>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                    <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                    </svg>
                  </div>
                </div>
                <div class="ml-4">
                  <p class="text-sm font-medium text-gray-600">Growth Rate</p>
                  <p class="text-2xl font-bold text-gray-900">{{ overviewStats.growthRate }}%</p>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <svg class="h-5 w-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                  </div>
                </div>
                <div class="ml-4">
                  <p class="text-sm font-medium text-gray-600">Active Anomalies</p>
                  <p class="text-2xl font-bold text-gray-900">{{ overviewStats.activeAnomalies }}</p>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                    <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                  </div>
                </div>
                <div class="ml-4">
                  <p class="text-sm font-medium text-gray-600">System Health</p>
                  <p class="text-2xl font-bold text-gray-900">{{ overviewStats.systemHealth }}%</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Compact Analytics Grid -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Mini Customer Segmentation -->
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Customer Segments</h3>
                <button
                  @click="activeTab = 'segmentation'"
                  class="text-sm text-blue-600 hover:text-blue-700"
                >
                  View Details →
                </button>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-3 bg-blue-50 rounded-lg">
                  <p class="text-2xl font-bold text-blue-600">8</p>
                  <p class="text-sm text-blue-800">Enterprise</p>
                </div>
                <div class="text-center p-3 bg-green-50 rounded-lg">
                  <p class="text-2xl font-bold text-green-600">15</p>
                  <p class="text-sm text-green-800">Growth</p>
                </div>
                <div class="text-center p-3 bg-yellow-50 rounded-lg">
                  <p class="text-2xl font-bold text-yellow-600">12</p>
                  <p class="text-sm text-yellow-800">Stable</p>
                </div>
                <div class="text-center p-3 bg-red-50 rounded-lg">
                  <p class="text-2xl font-bold text-red-600">7</p>
                  <p class="text-sm text-red-800">At Risk</p>
                </div>
              </div>
            </div>

            <!-- Mini Forecasting -->
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Usage Forecast</h3>
                <button
                  @click="activeTab = 'forecasting'"
                  class="text-sm text-blue-600 hover:text-blue-700"
                >
                  View Details →
                </button>
              </div>
              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <span class="text-sm text-gray-600">Next 30 Days</span>
                  <span class="text-lg font-semibold text-gray-900">2.4M calls</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-sm text-gray-600">Growth Rate</span>
                  <span class="text-lg font-semibold text-green-600">+5.2%</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-sm text-gray-600">Confidence</span>
                  <span class="text-lg font-semibold text-blue-600">92%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Recent Anomalies -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900">Recent Anomalies</h3>
              <button
                @click="activeTab = 'anomalies'"
                class="text-sm text-blue-600 hover:text-blue-700"
              >
                View All →
              </button>
            </div>
            <div class="space-y-3">
              <div
                v-for="anomaly in recentAnomalies"
                :key="anomaly.id"
                class="flex items-center justify-between p-3 border rounded-lg"
              >
                <div class="flex items-center space-x-3">
                  <div
                    class="w-3 h-3 rounded-full"
                    :class="anomaly.severity === 'critical' ? 'bg-red-500' : anomaly.severity === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'"
                  ></div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ anomaly.title }}</p>
                    <p class="text-xs text-gray-500">{{ anomaly.customer }} • {{ anomaly.time }}</p>
                  </div>
                </div>
                <span class="text-sm font-medium text-gray-600">{{ anomaly.deviation }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { format } from 'date-fns'
import CustomerSegmentation from '../components/CustomerSegmentation.vue'
import UsageForecasting from '../components/UsageForecasting.vue'
import AnomalyDetection from '../components/AnomalyDetection.vue'

const activeTab = ref('overview')
const refreshing = ref(false)
const lastUpdated = ref('')

const tabs = [
  { id: 'overview', name: 'Overview', icon: 'chart-bar' },
  { id: 'segmentation', name: 'Customer Segmentation', icon: 'users' },
  { id: 'forecasting', name: 'Usage Forecasting', icon: 'trending-up' },
  { id: 'anomalies', name: 'Anomaly Detection', icon: 'exclamation-triangle' },
]

const overviewStats = ref({
  totalCustomers: 42,
  growthRate: 5.2,
  activeAnomalies: 3,
  systemHealth: 98,
})

const recentAnomalies = ref([
  {
    id: '1',
    title: 'Unusual API Pattern',
    customer: 'Customer 5',
    time: '2 hours ago',
    severity: 'warning',
    deviation: '+250%'
  },
  {
    id: '2',
    title: 'Response Time Spike',
    customer: 'Customer 12',
    time: '4 hours ago',
    severity: 'critical',
    deviation: '+400%'
  },
  {
    id: '3',
    title: 'Storage Usage Increase',
    customer: 'Customer 8',
    time: '6 hours ago',
    severity: 'info',
    deviation: '+150%'
  }
])

async function refreshAllData() {
  refreshing.value = true
  try {
    // Simulate API calls
    await new Promise(resolve => setTimeout(resolve, 1000))
    lastUpdated.value = format(new Date(), 'MMM dd, HH:mm')
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  lastUpdated.value = format(new Date(), 'MMM dd, HH:mm')
})
</script>
