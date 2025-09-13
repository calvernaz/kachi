<template>
  <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-slate-900">Billing Preview</h3>
      <div class="flex space-x-2">
        <select
          v-model="selectedCustomer"
          class="text-sm border border-slate-300 rounded-md px-3 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select Customer</option>
          <option v-for="customer in customers" :key="customer.id" :value="customer.id">
            {{ customer.name }}
          </option>
        </select>
        <button
          @click="generatePreview"
          :disabled="loading || !selectedCustomer"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Generate</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <div v-else-if="error" class="text-center text-red-600 py-8">
      {{ error }}
    </div>

    <div v-else-if="billingData" class="space-y-6">
      <!-- Scenario Tabs -->
      <div class="border-b border-slate-200">
        <nav class="-mb-px flex space-x-8">
          <button
            v-for="scenario in scenarios"
            :key="scenario.id"
            @click="activeScenario = scenario.id"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2',
              activeScenario === scenario.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="scenario.id === 'current'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              <path v-else-if="scenario.id === 'optimistic'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              <path v-else-if="scenario.id === 'pessimistic'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
            </svg>
            <span>{{ scenario.name }}</span>
          </button>
        </nav>
      </div>

      <!-- Current Scenario Data -->
      <div v-if="currentScenarioData" class="space-y-6">
        <!-- Cost Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-4 rounded-lg text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm opacity-90">Subtotal</p>
                <p class="text-2xl font-bold">${{ formatCurrency(currentScenarioData.subtotal) }}</p>
                <p class="text-xs opacity-75">Before taxes</p>
              </div>
              <div class="opacity-80">
                <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
                </svg>
              </div>
            </div>
          </div>

          <div class="bg-gradient-to-r from-green-500 to-green-600 p-4 rounded-lg text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm opacity-90">Tax</p>
                <p class="text-2xl font-bold">${{ formatCurrency(currentScenarioData.tax) }}</p>
                <p class="text-xs opacity-75">{{ currentScenarioData.taxRate }}% rate</p>
              </div>
              <div class="opacity-80">
                <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                </svg>
              </div>
            </div>
          </div>

          <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-4 rounded-lg text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm opacity-90">Total</p>
                <p class="text-2xl font-bold">${{ formatCurrency(currentScenarioData.total) }}</p>
                <p class="text-xs opacity-75">Final amount</p>
              </div>
              <div class="opacity-80">
                <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
              </div>
            </div>
          </div>

          <div class="bg-gradient-to-r from-orange-500 to-orange-600 p-4 rounded-lg text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm opacity-90">vs Previous</p>
                <p class="text-2xl font-bold">{{ currentScenarioData.changePercent >= 0 ? '+' : '' }}{{ currentScenarioData.changePercent }}%</p>
                <p class="text-xs opacity-75">Month over month</p>
              </div>
              <div class="opacity-80">
                <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path v-if="currentScenarioData.changePercent >= 0" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Usage Breakdown -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Line Items -->
          <div class="bg-slate-50 rounded-lg p-6">
            <h4 class="text-md font-semibold text-slate-900 mb-4">Usage Breakdown</h4>
            <div class="space-y-3">
              <div v-for="item in currentScenarioData.lineItems" :key="item.meter" class="flex justify-between items-center">
                <div>
                  <p class="font-medium text-slate-900">{{ item.description }}</p>
                  <p class="text-sm text-slate-600">{{ formatNumber(item.quantity) }} {{ item.unit }} × ${{ item.unitPrice }}</p>
                </div>
                <div class="text-right">
                  <p class="font-semibold text-slate-900">${{ formatCurrency(item.amount) }}</p>
                  <p class="text-sm text-slate-600">{{ item.tier }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Tier Visualization -->
          <div class="bg-slate-50 rounded-lg p-6">
            <h4 class="text-md font-semibold text-slate-900 mb-4">Pricing Tiers</h4>
            <div class="space-y-4">
              <div v-for="tier in currentScenarioData.tiers" :key="tier.name" class="relative">
                <div class="flex justify-between items-center mb-2">
                  <span class="text-sm font-medium text-slate-700">{{ tier.name }}</span>
                  <span class="text-sm text-slate-600">${{ tier.unitPrice }}/{{ tier.unit }}</span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-2">
                  <div
                    class="h-2 rounded-full transition-all duration-300"
                    :class="tier.active ? 'bg-blue-600' : 'bg-slate-400'"
                    :style="{ width: tier.utilization + '%' }"
                  ></div>
                </div>
                <div class="flex justify-between text-xs text-slate-500 mt-1">
                  <span>{{ formatNumber(tier.used) }} used</span>
                  <span>{{ formatNumber(tier.limit) }} limit</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-between items-center pt-4 border-t border-slate-200">
          <div class="flex space-x-2">
            <button
              @click="exportPDF"
              class="px-4 py-2 bg-slate-600 text-white rounded-md hover:bg-slate-700 flex items-center space-x-2"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <span>Export PDF</span>
            </button>
            <button
              @click="exportCSV"
              class="px-4 py-2 bg-slate-600 text-white rounded-md hover:bg-slate-700 flex items-center space-x-2"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <span>Export CSV</span>
            </button>
          </div>
          <div class="text-sm text-slate-500">
            Period: {{ formatDate(currentScenarioData.periodStart) }} - {{ formatDate(currentScenarioData.periodEnd) }}
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12">
      <svg class="mx-auto h-12 w-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
      </svg>
      <h3 class="mt-2 text-sm font-medium text-slate-900">No billing preview</h3>
      <p class="mt-1 text-sm text-slate-500">Select a customer and generate a billing preview to get started.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

interface Customer {
  id: string
  name: string
}

interface LineItem {
  meter: string
  description: string
  quantity: number
  unit: string
  unitPrice: number
  amount: number
  tier: string
}

interface Tier {
  name: string
  unitPrice: number
  unit: string
  used: number
  limit: number
  utilization: number
  active: boolean
}

interface ScenarioData {
  subtotal: number
  tax: number
  taxRate: number
  total: number
  changePercent: number
  periodStart: string
  periodEnd: string
  lineItems: LineItem[]
  tiers: Tier[]
}

interface BillingData {
  current: ScenarioData
  optimistic: ScenarioData
  pessimistic: ScenarioData
}

const loading = ref(false)
const error = ref<string | null>(null)
const selectedCustomer = ref('')
const activeScenario = ref('current')
const billingData = ref<BillingData | null>(null)
const customers = ref<Customer[]>([])

const scenarios = [
  { id: 'current', name: 'Current Usage' },
  { id: 'optimistic', name: 'Growth Scenario' },
  { id: 'pessimistic', name: 'Conservative' },
]

const apiClient = axios.create({
  baseURL: 'http://localhost:8002/api',
  timeout: 10000,
})

const currentScenarioData = computed(() => {
  if (!billingData.value) return null
  return billingData.value[activeScenario.value as keyof BillingData]
})

async function fetchCustomers() {
  try {
    const response = await apiClient.get('/customers')
    customers.value = response.data.customers || []
  } catch (err) {
    console.error('Failed to fetch customers:', err)
  }
}

async function generatePreview() {
  if (!selectedCustomer.value) return

  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get('/billing/preview', {
      params: {
        customer_id: selectedCustomer.value,
        period_start: '2024-01-01',
        period_end: '2024-01-31'
      }
    })

    billingData.value = response.data
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to generate billing preview'
  } finally {
    loading.value = false
  }
}

function formatCurrency(amount: number): string {
  return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function exportPDF() {
  // TODO: Implement PDF export
  console.log('Exporting PDF...')
}

function exportCSV() {
  // TODO: Implement CSV export
  console.log('Exporting CSV...')
}

onMounted(() => {
  fetchCustomers()
})
</script>
