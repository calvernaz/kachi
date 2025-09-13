<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Usage Forecasting</h3>
      <div class="flex space-x-2">
        <select
          v-model="forecastPeriod"
          class="text-sm border border-gray-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="7">7 Days</option>
          <option value="30">30 Days</option>
          <option value="90">90 Days</option>
        </select>
        <select
          v-model="selectedMeter"
          class="text-sm border border-gray-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="all">All Meters</option>
          <option value="api.calls">API Calls</option>
          <option value="workflows">Workflows</option>
          <option value="llm.tokens">LLM Tokens</option>
          <option value="storage">Storage</option>
        </select>
        <button
          @click="refreshForecast"
          :disabled="loading"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-else>Forecast</span>
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
      <!-- Forecast Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Predicted Usage</p>
              <p class="text-2xl font-bold">{{ formatNumber(forecastData?.predictedUsage || 0) }}</p>
              <p class="text-xs opacity-75">Next {{ forecastPeriod }} days</p>
            </div>
            <div class="opacity-80">
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              </svg>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-green-500 to-green-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Confidence</p>
              <p class="text-2xl font-bold">{{ forecastData?.confidence || 0 }}%</p>
              <p class="text-xs opacity-75">Model accuracy</p>
            </div>
            <div class="text-3xl opacity-80">🎯</div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-yellow-500 to-yellow-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Growth Rate</p>
              <p class="text-2xl font-bold">{{ forecastData?.growthRate || 0 }}%</p>
              <p class="text-xs opacity-75">vs previous period</p>
            </div>
            <div class="opacity-80">
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-4 rounded-lg text-white">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">Peak Day</p>
              <p class="text-2xl font-bold">{{ formatDate(forecastData?.peakDay) }}</p>
              <p class="text-xs opacity-75">Highest usage expected</p>
            </div>
            <div class="text-3xl opacity-80">⚡</div>
          </div>
        </div>
      </div>

      <!-- Forecast Chart -->
      <div class="bg-gray-50 rounded-lg p-4">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-md font-semibold text-gray-900">Usage Forecast</h4>
          <div class="flex items-center space-x-4 text-sm">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
              <span>Historical</span>
            </div>
            <div class="flex items-center">
              <div class="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
              <span>Forecast</span>
            </div>
            <div class="flex items-center">
              <div class="w-3 h-3 bg-gray-300 rounded-full mr-2"></div>
              <span>Confidence Band</span>
            </div>
          </div>
        </div>
        <canvas ref="forecastChart" class="w-full h-80"></canvas>
      </div>

      <!-- Forecast Insights -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="flex items-center mb-3">
            <svg class="h-5 w-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
            </svg>
            <h4 class="text-md font-semibold text-blue-900">Key Insights</h4>
          </div>
          <ul class="space-y-2 text-sm text-blue-800">
            <li v-for="insight in forecastData?.insights || []" :key="insight" class="flex items-start">
              <span class="text-blue-500 mr-2">•</span>
              {{ insight }}
            </li>
          </ul>
        </div>

        <div class="bg-yellow-50 rounded-lg p-4">
          <div class="flex items-center mb-3">
            <svg class="h-5 w-5 text-yellow-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
            </svg>
            <h4 class="text-md font-semibold text-yellow-900">Recommendations</h4>
          </div>
          <ul class="space-y-2 text-sm text-yellow-800">
            <li v-for="recommendation in forecastData?.recommendations || []" :key="recommendation" class="flex items-start">
              <span class="text-yellow-500 mr-2">•</span>
              {{ recommendation }}
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

interface ForecastData {
  predictedUsage: number
  confidence: number
  growthRate: number
  peakDay: string
  historical: Array<{ date: string; value: number }>
  forecast: Array<{ date: string; value: number; upper: number; lower: number }>
  insights: string[]
  recommendations: string[]
}

const loading = ref(false)
const error = ref<string | null>(null)
const forecastPeriod = ref('30')
const selectedMeter = ref('all')
const forecastData = ref<ForecastData | null>(null)
const forecastChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

const apiClient = axios.create({
  baseURL: 'http://localhost:8002/api',
  timeout: 10000,
})

async function fetchForecastData() {
  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get('/analytics/forecast', {
      params: {
        period: forecastPeriod.value,
        meter_key: selectedMeter.value
      }
    })

    forecastData.value = response.data
    await nextTick()
    createChart()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch forecast data'
  } finally {
    loading.value = false
  }
}

function createChart() {
  if (!forecastChart.value || !forecastData.value) return

  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = forecastChart.value.getContext('2d')
  if (!ctx) return

  const historical = forecastData.value.historical
  const forecast = forecastData.value.forecast

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [...historical.map(h => h.date), ...forecast.map(f => f.date)],
      datasets: [
        {
          label: 'Historical Usage',
          data: [...historical.map(h => h.value), ...Array(forecast.length).fill(null)],
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Forecast',
          data: [...Array(historical.length).fill(null), ...forecast.map(f => f.value)],
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0.4,
        },
        {
          label: 'Upper Confidence',
          data: [...Array(historical.length).fill(null), ...forecast.map(f => f.upper)],
          borderColor: 'rgba(156, 163, 175, 0.5)',
          backgroundColor: 'rgba(156, 163, 175, 0.1)',
          borderWidth: 1,
          fill: '+1',
          tension: 0.4,
        },
        {
          label: 'Lower Confidence',
          data: [...Array(historical.length).fill(null), ...forecast.map(f => f.lower)],
          borderColor: 'rgba(156, 163, 175, 0.5)',
          backgroundColor: 'rgba(156, 163, 175, 0.1)',
          borderWidth: 1,
          fill: false,
          tension: 0.4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            filter: (item) => item.text !== 'Upper Confidence' && item.text !== 'Lower Confidence'
          }
        },
        tooltip: {
          callbacks: {
            title: (context) => {
              return format(new Date(context[0].label), 'MMM dd, yyyy')
            },
            label: (context) => {
              if (context.dataset.label === 'Upper Confidence' || context.dataset.label === 'Lower Confidence') {
                return ''
              }
              return `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: 'Date'
          }
        },
        y: {
          display: true,
          title: {
            display: true,
            text: 'Usage'
          },
          beginAtZero: true
        }
      }
    }
  })
}

function formatNumber(value: number): string {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + 'M'
  } else if (value >= 1000) {
    return (value / 1000).toFixed(1) + 'K'
  }
  return value.toString()
}

function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A'
  return format(new Date(dateString), 'MMM dd')
}

function refreshForecast() {
  fetchForecastData()
}

watch([forecastPeriod, selectedMeter], () => {
  fetchForecastData()
})

onMounted(() => {
  fetchForecastData()
})
</script>
