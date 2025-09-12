<template>
  <div class="bg-white rounded-lg shadow p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Usage Trends</h3>
        <p class="text-sm text-gray-500">{{ formatPeriodDescription() }}</p>
      </div>
      <div class="flex space-x-2">
        <select
          v-model="selectedPeriod"
          @change="fetchData"
          class="rounded-md border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value="daily">Daily (30 days)</option>
          <option value="weekly">Weekly (12 weeks)</option>
          <option value="monthly">Monthly (12 months)</option>
        </select>
        <select
          v-model="selectedMeter"
          @change="fetchData"
          class="rounded-md border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value="">All Meters</option>
          <option value="api.calls">API Calls</option>
          <option value="workflow.completed">Workflows</option>
          <option value="llm.tokens">LLM Tokens</option>
          <option value="storage.gbh">Storage</option>
        </select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Chart -->
    <div v-else-if="chartData" class="relative">
      <canvas ref="chartCanvas" class="w-full h-64"></canvas>

      <!-- Statistics -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-200">
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900">{{ formatNumber(trendData?.total_usage || 0) }}</p>
          <p class="text-sm text-gray-500">Total Usage</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900">{{ formatNumber(trendData?.average_usage || 0) }}</p>
          <p class="text-sm text-gray-500">Average</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900">{{ formatNumber(trendData?.peak_usage || 0) }}</p>
          <p class="text-sm text-gray-500">Peak Usage</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-bold" :class="growthRateColor">
            {{ formatGrowthRate(trendData?.growth_rate || 0) }}
          </p>
          <p class="text-sm text-gray-500">Growth Rate</p>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else class="flex justify-center items-center h-64">
      <div class="text-center">
        <p class="text-gray-500">Failed to load usage data</p>
        <button
          @click="fetchData"
          class="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          Retry
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { format, parseISO } from 'date-fns'

// Register Chart.js components
Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface TimeSeriesPoint {
  timestamp: string
  value: number
  meter_key: string
}

interface UsageTrend {
  period: string
  data_points: TimeSeriesPoint[]
  total_usage: number
  average_usage: number
  peak_usage: number
  growth_rate: number
}

const chartCanvas = ref<HTMLCanvasElement>()
const chart = ref<Chart>()
const loading = ref(true)
const selectedPeriod = ref('daily')
const selectedMeter = ref('')
const trendData = ref<UsageTrend>()
const chartData = ref<any>()

const growthRateColor = computed(() => {
  const rate = trendData.value?.growth_rate || 0
  if (rate > 0) return 'text-green-600'
  if (rate < 0) return 'text-red-600'
  return 'text-gray-900'
})

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString()
}

function formatGrowthRate(rate: number): string {
  const sign = rate > 0 ? '+' : ''
  return `${sign}${rate.toFixed(1)}%`
}

function formatPeriodDescription(): string {
  switch (selectedPeriod.value) {
    case 'daily':
      return 'Daily usage over the last 30 days'
    case 'weekly':
      return 'Weekly usage over the last 12 weeks'
    case 'monthly':
      return 'Monthly usage over the last 12 months'
    default:
      return ''
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      period: selectedPeriod.value,
    })

    if (selectedMeter.value) {
      params.append('meter_key', selectedMeter.value)
    }

    const response = await fetch(`http://localhost:8002/api/usage/trends?${params}`)
    if (!response.ok) throw new Error('Failed to fetch usage trends')

    trendData.value = await response.json()
    updateChart()
  } catch (error) {
    console.error('Error fetching usage trends:', error)
    trendData.value = undefined
    chartData.value = undefined
  } finally {
    loading.value = false
  }
}

function updateChart() {
  if (!trendData.value || !chartCanvas.value) return

  const labels = trendData.value.data_points.map(point => {
    const date = parseISO(point.timestamp)
    switch (selectedPeriod.value) {
      case 'daily':
        return format(date, 'MMM dd')
      case 'weekly':
        return format(date, 'MMM dd')
      case 'monthly':
        return format(date, 'MMM yyyy')
      default:
        return format(date, 'MMM dd')
    }
  })

  const data = trendData.value.data_points.map(point => point.value)

  chartData.value = {
    labels,
    datasets: [
      {
        label: selectedMeter.value || 'Total Usage',
        data,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  }

  // Destroy existing chart
  if (chart.value) {
    chart.value.destroy()
  }

  // Create new chart
  chart.value = new Chart(chartCanvas.value, {
    type: 'line',
    data: chartData.value,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: 'white',
          bodyColor: 'white',
          borderColor: 'rgba(59, 130, 246, 0.8)',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            }
          }
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
          ticks: {
            color: '#6B7280',
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(0, 0, 0, 0.1)',
          },
          ticks: {
            color: '#6B7280',
            callback: function(value) {
              return formatNumber(Number(value))
            }
          },
        },
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
    },
  })
}

onMounted(async () => {
  await fetchData()
})

// Watch for period/meter changes
watch([selectedPeriod, selectedMeter], () => {
  fetchData()
})
</script>
