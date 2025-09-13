<template>
  <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-lg font-semibold text-slate-900">Predictive Billing Forecast</h3>
        <p class="text-sm text-slate-600">AI-powered cost predictions and trend analysis</p>
      </div>
      <div class="flex items-center space-x-3">
        <select
          v-model="selectedTimeframe"
          @change="updateForecast"
          class="px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="3m">3 Months</option>
          <option value="6m">6 Months</option>
          <option value="12m">12 Months</option>
        </select>
        <button
          @click="refreshForecast"
          :disabled="loading"
          class="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Forecast Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div v-for="metric in forecastSummary" :key="metric.label" class="bg-gradient-to-r from-slate-50 to-slate-100 rounded-lg p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-slate-600">{{ metric.label }}</p>
            <p class="text-2xl font-bold text-slate-900">${{ formatCurrency(metric.value) }}</p>
            <div class="flex items-center mt-1">
              <svg 
                :class="[
                  'h-4 w-4 mr-1',
                  metric.trend === 'up' ? 'text-red-500' : metric.trend === 'down' ? 'text-green-500' : 'text-slate-400'
                ]" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path v-if="metric.trend === 'up'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                <path v-else-if="metric.trend === 'down'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
                <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
              <span 
                :class="[
                  'text-sm font-medium',
                  metric.trend === 'up' ? 'text-red-600' : metric.trend === 'down' ? 'text-green-600' : 'text-slate-600'
                ]"
              >
                {{ metric.change }}%
              </span>
            </div>
          </div>
          <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="metric.icon === 'trend'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              <path v-else-if="metric.icon === 'target'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              <path v-else-if="metric.icon === 'calendar'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Forecast Chart -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-4">
        <h4 class="text-md font-semibold text-slate-900">Cost Forecast Trend</h4>
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span class="text-sm text-slate-600">Historical</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-green-500 rounded-full"></div>
            <span class="text-sm text-slate-600">Predicted</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
            <span class="text-sm text-slate-600">Confidence Band</span>
          </div>
        </div>
      </div>
      <div class="h-64 bg-slate-50 rounded-lg flex items-center justify-center">
        <canvas ref="forecastChart" class="w-full h-full"></canvas>
      </div>
    </div>

    <!-- Seasonal Patterns -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <div class="bg-slate-50 rounded-lg p-4">
        <h4 class="text-md font-semibold text-slate-900 mb-3">Seasonal Patterns</h4>
        <div class="space-y-3">
          <div v-for="pattern in seasonalPatterns" :key="pattern.period" class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div :class="['w-3 h-3 rounded-full', pattern.color]"></div>
              <span class="text-sm font-medium text-slate-700">{{ pattern.period }}</span>
            </div>
            <div class="text-right">
              <span class="text-sm font-semibold text-slate-900">{{ pattern.impact }}%</span>
              <p class="text-xs text-slate-600">{{ pattern.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-slate-50 rounded-lg p-4">
        <h4 class="text-md font-semibold text-slate-900 mb-3">Growth Drivers</h4>
        <div class="space-y-3">
          <div v-for="driver in growthDrivers" :key="driver.metric" class="flex items-center justify-between">
            <div>
              <span class="text-sm font-medium text-slate-700">{{ driver.metric }}</span>
              <p class="text-xs text-slate-600">{{ driver.description }}</p>
            </div>
            <div class="text-right">
              <span :class="['text-sm font-semibold', driver.impact > 0 ? 'text-red-600' : 'text-green-600']">
                {{ driver.impact > 0 ? '+' : '' }}{{ driver.impact }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Insights -->
    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
          </svg>
        </div>
        <div class="flex-1">
          <h4 class="text-md font-semibold text-slate-900 mb-2">AI-Powered Insights</h4>
          <div class="space-y-2">
            <div v-for="insight in aiInsights" :key="insight.id" class="flex items-start space-x-2">
              <div class="flex-shrink-0 mt-1">
                <div :class="['w-2 h-2 rounded-full', insight.priority === 'high' ? 'bg-red-500' : insight.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500']"></div>
              </div>
              <div>
                <p class="text-sm text-slate-700">{{ insight.message }}</p>
                <p class="text-xs text-slate-600 mt-1">{{ insight.recommendation }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const loading = ref(false)
const selectedTimeframe = ref('6m')
const forecastChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

const forecastSummary = ref([
  {
    label: 'Next Month',
    value: 1250.00,
    change: 12.5,
    trend: 'up',
    icon: 'calendar'
  },
  {
    label: 'Quarterly',
    value: 3750.00,
    change: 8.3,
    trend: 'up',
    icon: 'trend'
  },
  {
    label: 'Annual',
    value: 15000.00,
    change: 15.2,
    trend: 'up',
    icon: 'target'
  },
  {
    label: 'Budget Variance',
    value: 500.00,
    change: -5.2,
    trend: 'down',
    icon: 'dollar'
  }
])

const seasonalPatterns = ref([
  {
    period: 'Q1 (Jan-Mar)',
    impact: '+15',
    description: 'High usage period',
    color: 'bg-red-500'
  },
  {
    period: 'Q2 (Apr-Jun)',
    impact: '+8',
    description: 'Moderate growth',
    color: 'bg-yellow-500'
  },
  {
    period: 'Q3 (Jul-Sep)',
    impact: '-5',
    description: 'Summer slowdown',
    color: 'bg-green-500'
  },
  {
    period: 'Q4 (Oct-Dec)',
    impact: '+22',
    description: 'Year-end surge',
    color: 'bg-red-600'
  }
])

const growthDrivers = ref([
  {
    metric: 'API Calls',
    description: 'Increasing automation usage',
    impact: 18.5
  },
  {
    metric: 'LLM Tokens',
    description: 'AI feature adoption',
    impact: 25.3
  },
  {
    metric: 'Storage',
    description: 'Data retention policies',
    impact: 12.1
  },
  {
    metric: 'Workflows',
    description: 'Process optimization',
    impact: -8.2
  }
])

const aiInsights = ref([
  {
    id: 1,
    priority: 'high',
    message: 'API usage is trending 25% above seasonal norms',
    recommendation: 'Consider upgrading to volume discount tier to reduce per-unit costs'
  },
  {
    id: 2,
    priority: 'medium',
    message: 'LLM token consumption shows strong correlation with business hours',
    recommendation: 'Implement caching strategies during peak hours for 15% cost reduction'
  },
  {
    id: 3,
    priority: 'low',
    message: 'Storage growth is linear and predictable',
    recommendation: 'Current storage tier is optimal for projected growth'
  }
])

function formatCurrency(amount: number): string {
  return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function refreshForecast() {
  loading.value = true
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    await updateForecast()
  } finally {
    loading.value = false
  }
}

async function updateForecast() {
  await nextTick()
  if (forecastChart.value) {
    createForecastChart()
  }
}

function createForecastChart() {
  if (!forecastChart.value) return

  // Destroy existing chart
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = forecastChart.value.getContext('2d')
  if (!ctx) return

  // Generate mock data based on timeframe
  const periods = selectedTimeframe.value === '3m' ? 12 : selectedTimeframe.value === '6m' ? 24 : 48
  const labels = []
  const historicalData = []
  const predictedData = []
  const confidenceBandUpper = []
  const confidenceBandLower = []

  for (let i = 0; i < periods; i++) {
    const date = new Date()
    date.setMonth(date.getMonth() - periods + i + 1)
    labels.push(date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }))

    // Historical data (first 60% of periods)
    if (i < periods * 0.6) {
      const baseValue = 1000 + Math.sin(i * 0.5) * 200 + i * 50
      historicalData.push(baseValue + Math.random() * 100 - 50)
      predictedData.push(null)
      confidenceBandUpper.push(null)
      confidenceBandLower.push(null)
    } else {
      // Predicted data (last 40% of periods)
      const baseValue = 1000 + Math.sin(i * 0.5) * 200 + i * 60
      const predicted = baseValue + Math.random() * 100 - 50
      
      historicalData.push(null)
      predictedData.push(predicted)
      confidenceBandUpper.push(predicted * 1.15)
      confidenceBandLower.push(predicted * 0.85)
    }
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Historical',
          data: historicalData,
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.4
        },
        {
          label: 'Predicted',
          data: predictedData,
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0.4
        },
        {
          label: 'Confidence Upper',
          data: confidenceBandUpper,
          borderColor: 'rgba(249, 115, 22, 0.3)',
          backgroundColor: 'rgba(249, 115, 22, 0.1)',
          borderWidth: 1,
          fill: '+1',
          tension: 0.4,
          pointRadius: 0
        },
        {
          label: 'Confidence Lower',
          data: confidenceBandLower,
          borderColor: 'rgba(249, 115, 22, 0.3)',
          backgroundColor: 'rgba(249, 115, 22, 0.1)',
          borderWidth: 1,
          fill: false,
          tension: 0.4,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              if (context.dataset.label?.includes('Confidence')) return ''
              return `${context.dataset.label}: $${context.parsed.y?.toFixed(2) || 0}`
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: false,
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          },
          ticks: {
            callback: function(value) {
              return '$' + value
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  })
}

onMounted(() => {
  updateForecast()
})
</script>
