<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Customer Segmentation</h3>
      <div class="flex space-x-2">
        <select
          v-model="selectedMetric"
          class="text-sm border border-gray-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="revenue">Revenue</option>
          <option value="usage">Usage Volume</option>
          <option value="frequency">API Frequency</option>
        </select>
        <button
          @click="refreshData"
          :disabled="loading"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span v-else>Refresh</span>
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
      <!-- Segment Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          v-for="segment in segments"
          :key="segment.name"
          class="bg-gradient-to-r p-4 rounded-lg text-white cursor-pointer transition-transform hover:scale-105"
          :class="segment.gradient"
          @click="selectSegment(segment)"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm opacity-90">{{ segment.name }}</p>
              <p class="text-2xl font-bold">{{ segment.count }}</p>
              <p class="text-xs opacity-75">{{ segment.percentage }}% of total</p>
            </div>
            <div class="opacity-80">
              <svg class="h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
                <path v-if="segment.name === 'Enterprise'" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                <path v-else-if="segment.name === 'Growth'" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                <path v-else-if="segment.name === 'Stable'" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"></path>
                <path v-else-if="segment.name === 'At Risk'" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Chart -->
      <div class="bg-gray-50 rounded-lg p-4">
        <canvas ref="segmentChart" class="w-full h-64"></canvas>
      </div>

      <!-- Customer List for Selected Segment -->
      <div v-if="selectedSegmentData" class="border-t pt-6">
        <h4 class="text-md font-semibold text-gray-900 mb-4">
          {{ selectedSegmentData.name }} Customers ({{ selectedSegmentData.customers.length }})
        </h4>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Customer
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Revenue
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usage
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Growth
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Score
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="customer in selectedSegmentData.customers" :key="customer.id">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-8 w-8">
                      <div class="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center text-sm font-medium text-gray-700">
                        {{ customer.name.charAt(0) }}
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{{ customer.name }}</div>
                      <div class="text-sm text-gray-500">{{ customer.id }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${{ customer.revenue.toLocaleString() }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ customer.usage.toLocaleString() }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="customer.growth >= 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                  >
                    {{ customer.growth >= 0 ? '+' : '' }}{{ customer.growth.toFixed(1) }}%
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                      <div
                        class="h-2 rounded-full"
                        :class="getRiskColor(customer.riskScore)"
                        :style="{ width: customer.riskScore + '%' }"
                      ></div>
                    </div>
                    <span class="text-sm text-gray-600">{{ customer.riskScore }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import axios from 'axios'

Chart.register(...registerables)

interface Customer {
  id: string
  name: string
  revenue: number
  usage: number
  growth: number
  riskScore: number
}

interface Segment {
  name: string
  count: number
  percentage: number
  icon: string
  gradient: string
  customers: Customer[]
}

const loading = ref(false)
const error = ref<string | null>(null)
const selectedMetric = ref('revenue')
const segments = ref<Segment[]>([])
const selectedSegmentData = ref<Segment | null>(null)
const segmentChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

const apiClient = axios.create({
  baseURL: 'http://localhost:8002/api',
  timeout: 10000,
})

async function fetchSegmentationData() {
  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get('/analytics/segmentation', {
      params: { metric: selectedMetric.value }
    })

    segments.value = response.data.segments
    await nextTick()
    createChart()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch segmentation data'
  } finally {
    loading.value = false
  }
}

function createChart() {
  if (!segmentChart.value) return

  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = segmentChart.value.getContext('2d')
  if (!ctx) return

  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: segments.value.map(s => s.name),
      datasets: [{
        data: segments.value.map(s => s.count),
        backgroundColor: [
          '#3B82F6', // Blue
          '#10B981', // Green
          '#F59E0B', // Yellow
          '#EF4444', // Red
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            padding: 20,
            usePointStyle: true,
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const segment = segments.value[context.dataIndex]
              return `${segment.name}: ${segment.count} customers (${segment.percentage}%)`
            }
          }
        }
      },
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index
          selectSegment(segments.value[index])
        }
      }
    }
  })
}

function selectSegment(segment: Segment) {
  selectedSegmentData.value = segment
}

function getRiskColor(score: number): string {
  if (score < 30) return 'bg-green-500'
  if (score < 60) return 'bg-yellow-500'
  return 'bg-red-500'
}

function refreshData() {
  fetchSegmentationData()
}

watch(selectedMetric, () => {
  fetchSegmentationData()
})

onMounted(() => {
  fetchSegmentationData()
})
</script>
