<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Anomaly Detection</h3>
      <div class="flex space-x-2">
        <select
          v-model="timeRange"
          class="text-sm border border-gray-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
        <select
          v-model="sensitivity"
          class="text-sm border border-gray-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="low">Low Sensitivity</option>
          <option value="medium">Medium Sensitivity</option>
          <option value="high">High Sensitivity</option>
        </select>
        <button
          @click="refreshAnomalies"
          :disabled="loading"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-else>Scan</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <div v-else-if="error" class="text-center text-red-600 py-8">
      {{ error }}
    </div>

    <div v-else class="space-y-6">
      <!-- Anomaly Summary -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-gradient-to-r from-red-500 to-red-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Critical Anomalies</p>
              <p class="text-2xl font-bold">{{ anomalyData?.critical || 0 }}</p>
              <p class="text-xs opacity-75">Immediate attention</p>
            </div>
            <div class="opacity-80">
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-yellow-500 to-yellow-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Warning Anomalies</p>
              <p class="text-2xl font-bold">{{ anomalyData?.warning || 0 }}</p>
              <p class="text-xs opacity-75">Monitor closely</p>
            </div>
            <div class="opacity-80">
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Info Anomalies</p>
              <p class="text-2xl font-bold">{{ anomalyData?.info || 0 }}</p>
              <p class="text-xs opacity-75">For awareness</p>
            </div>
            <div class="text-3xl opacity-80">ℹ️</div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-green-500 to-green-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">System Health</p>
              <p class="text-2xl font-bold">{{ anomalyData?.healthScore || 0 }}%</p>
              <p class="text-xs opacity-75">Overall score</p>
            </div>
            <div class="text-3xl opacity-80">💚</div>
          </div>
        </div>
      </div>

      <!-- Anomaly Timeline Chart -->
      <div class="bg-gray-50 rounded-lg p-4">
        <h4 class="text-md font-semibold text-gray-900 mb-4">Anomaly Timeline</h4>
        <canvas ref="anomalyChart" class="w-full h-64"></canvas>
      </div>

      <!-- Recent Anomalies List -->
      <div class="border-t pt-6">
        <h4 class="text-md font-semibold text-gray-900 mb-4">Recent Anomalies</h4>
        <div class="space-y-3">
          <div
            v-for="anomaly in anomalyData?.recent || []"
            :key="anomaly.id"
            class="flex items-center justify-between p-4 border rounded-lg"
            :class="getAnomalyBorderColor(anomaly.severity)"
          >
            <div class="flex items-center space-x-4">
              <div
                class="flex-shrink-0 w-3 h-3 rounded-full"
                :class="getAnomalySeverityColor(anomaly.severity)"
              ></div>
              <div>
                <div class="flex items-center space-x-2">
                  <h5 class="text-sm font-medium text-gray-900">{{ anomaly.title }}</h5>
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="getAnomalySeverityBadge(anomaly.severity)"
                  >
                    {{ anomaly.severity }}
                  </span>
                </div>
                <p class="text-sm text-gray-600">{{ anomaly.description }}</p>
                <div class="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                  <span>{{ anomaly.customer }}</span>
                  <span>{{ anomaly.meter }}</span>
                  <span>{{ formatTime(anomaly.timestamp) }}</span>
                </div>
              </div>
            </div>
            <div class="flex items-center space-x-2">
              <span class="text-sm font-medium text-gray-900">
                {{ anomaly.deviation }}
              </span>
              <button
                @click="investigateAnomaly(anomaly)"
                class="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200"
              >
                Investigate
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Anomaly Patterns -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-purple-50 rounded-lg p-4">
          <h4 class="text-md font-semibold text-purple-900 mb-3">🔍 Pattern Analysis</h4>
          <ul class="space-y-2 text-sm text-purple-800">
            <li v-for="pattern in anomalyData?.patterns || []" :key="pattern" class="flex items-start">
              <span class="text-purple-500 mr-2">•</span>
              {{ pattern }}
            </li>
          </ul>
        </div>

        <div class="bg-orange-50 rounded-lg p-4">
          <h4 class="text-md font-semibold text-orange-900 mb-3">🎯 Suggested Actions</h4>
          <ul class="space-y-2 text-sm text-orange-800">
            <li v-for="action in anomalyData?.actions || []" :key="action" class="flex items-start">
              <span class="text-orange-500 mr-2">•</span>
              {{ action }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import axios from 'axios'
import { format } from 'date-fns'

Chart.register(...registerables)

interface Anomaly {
  id: string
  title: string
  description: string
  severity: 'critical' | 'warning' | 'info'
  customer: string
  meter: string
  timestamp: string
  deviation: string
}

interface AnomalyData {
  critical: number
  warning: number
  info: number
  healthScore: number
  recent: Anomaly[]
  timeline: Array<{ timestamp: string; count: number; severity: string }>
  patterns: string[]
  actions: string[]
}

const loading = ref(false)
const error = ref<string | null>(null)
const timeRange = ref('24h')
const sensitivity = ref('medium')
const anomalyData = ref<AnomalyData | null>(null)
const anomalyChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

const apiClient = axios.create({
  baseURL: 'http://localhost:8002/api',
  timeout: 10000,
})

async function fetchAnomalyData() {
  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get('/analytics/anomalies', {
      params: {
        time_range: timeRange.value,
        sensitivity: sensitivity.value
      }
    })

    anomalyData.value = response.data
    await nextTick()
    createChart()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch anomaly data'
  } finally {
    loading.value = false
  }
}

function createChart() {
  if (!anomalyChart.value || !anomalyData.value) return

  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = anomalyChart.value.getContext('2d')
  if (!ctx) return

  const timeline = anomalyData.value.timeline

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: timeline.map(t => format(new Date(t.timestamp), 'MMM dd HH:mm')),
      datasets: [
        {
          label: 'Critical',
          data: timeline.map(t => t.severity === 'critical' ? t.count : 0),
          backgroundColor: '#EF4444',
          borderColor: '#DC2626',
          borderWidth: 1,
        },
        {
          label: 'Warning',
          data: timeline.map(t => t.severity === 'warning' ? t.count : 0),
          backgroundColor: '#F59E0B',
          borderColor: '#D97706',
          borderWidth: 1,
        },
        {
          label: 'Info',
          data: timeline.map(t => t.severity === 'info' ? t.count : 0),
          backgroundColor: '#3B82F6',
          borderColor: '#2563EB',
          borderWidth: 1,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          title: {
            display: true,
            text: 'Time'
          }
        },
        y: {
          stacked: true,
          beginAtZero: true,
          title: {
            display: true,
            text: 'Anomaly Count'
          }
        }
      },
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          mode: 'index',
          intersect: false,
        }
      }
    }
  })
}

function getAnomalySeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-500'
    case 'warning': return 'bg-yellow-500'
    case 'info': return 'bg-blue-500'
    default: return 'bg-gray-500'
  }
}

function getAnomalySeverityBadge(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800'
    case 'warning': return 'bg-yellow-100 text-yellow-800'
    case 'info': return 'bg-blue-100 text-blue-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

function getAnomalyBorderColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'border-red-200'
    case 'warning': return 'border-yellow-200'
    case 'info': return 'border-blue-200'
    default: return 'border-gray-200'
  }
}

function formatTime(timestamp: string): string {
  return format(new Date(timestamp), 'MMM dd, HH:mm')
}

function investigateAnomaly(anomaly: Anomaly) {
  // TODO: Open detailed anomaly investigation modal
  console.log('Investigating anomaly:', anomaly)
}

function refreshAnomalies() {
  fetchAnomalyData()
}

watch([timeRange, sensitivity], () => {
  fetchAnomalyData()
})

onMounted(() => {
  fetchAnomalyData()
})
</script>
