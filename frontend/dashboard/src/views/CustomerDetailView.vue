<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4">
      <div class="flex">
        <svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        </svg>
        <div class="ml-3">
          <p class="text-sm text-red-800">{{ error }}</p>
        </div>
      </div>
    </div>

    <!-- Customer Detail Content -->
    <div v-else-if="customer" class="space-y-6">
      <!-- Header -->
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <RouterLink
              to="/customers"
              class="text-gray-400 hover:text-gray-600 mr-4"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
            </RouterLink>
            <div>
              <h1 class="text-2xl font-bold text-gray-900">{{ customer.name }}</h1>
              <p class="text-gray-600">Customer ID: {{ customer.id }}</p>
            </div>
          </div>
          <div class="flex space-x-3">
            <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
              Edit Customer
            </button>
            <button class="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm font-medium">
              Export Data
            </button>
          </div>
        </div>
      </div>

      <!-- Customer Info & Usage Summary -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Customer Information -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Customer Information</h2>
          <dl class="space-y-3">
            <div>
              <dt class="text-sm font-medium text-gray-500">Name</dt>
              <dd class="text-sm text-gray-900">{{ customer.name }}</dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">Lago Customer ID</dt>
              <dd class="text-sm text-gray-900">{{ customer.lago_customer_id }}</dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">Currency</dt>
              <dd class="text-sm text-gray-900">{{ customer.currency }}</dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">Created</dt>
              <dd class="text-sm text-gray-900">{{ formatDate(customer.created_at) }}</dd>
            </div>
          </dl>
        </div>

        <!-- Usage Summary -->
        <div class="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-900">Usage Summary</h2>
            <select
              v-model="selectedPeriod"
              @change="loadUsageData"
              class="border border-gray-300 rounded-md px-3 py-1 text-sm"
            >
              <option value="current_month">Current Month</option>
              <option value="last_month">Last Month</option>
              <option value="last_7_days">Last 7 Days</option>
            </select>
          </div>

          <div v-if="usageLoading" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>

          <div v-else-if="usageSummary" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gray-50 p-4 rounded-lg">
                <div class="text-sm text-gray-500">Total Amount</div>
                <div class="text-xl font-semibold text-gray-900">€{{ usageSummary.total_amount.toFixed(2) }}</div>
              </div>
              <div class="bg-gray-50 p-4 rounded-lg">
                <div class="text-sm text-gray-500">Margin</div>
                <div class="text-xl font-semibold text-green-600">€{{ usageSummary.margin.toFixed(2) }}</div>
              </div>
            </div>

            <!-- Meters breakdown -->
            <div class="mt-6">
              <h3 class="text-sm font-medium text-gray-900 mb-3">Meter Usage</h3>
              <div class="space-y-2">
                <div
                  v-for="(value, meter) in usageSummary.meters"
                  :key="meter"
                  class="flex justify-between items-center py-2 border-b border-gray-100"
                >
                  <span class="text-sm text-gray-600">{{ meter }}</span>
                  <span class="text-sm font-medium text-gray-900">{{ value.toLocaleString() }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Meter Details -->
      <div v-if="meterUsage.length > 0" class="bg-white rounded-lg shadow">
        <div class="p-6 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Detailed Meter Usage</h2>
        </div>
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <UsageCard
              v-for="meter in meterUsage"
              :key="meter.meter_key"
              :title="meter.meter_key"
              :current-value="meter.current_value"
              :max-value="meter.included_allowance + meter.current_value"
              :included-value="meter.included_allowance"
              :unit="getUnitForMeter(meter.meter_key)"
              :cost="meter.overage_amount"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCustomerStore, type Customer, type UsageSummary, type MeterUsage } from '@/stores/customer'
import UsageCard from '@/components/UsageCard.vue'

const route = useRoute()
const customerStore = useCustomerStore()

const loading = ref(true)
const error = ref<string | null>(null)
const usageLoading = ref(false)
const selectedPeriod = ref('current_month')
const usageSummary = ref<UsageSummary | null>(null)
const meterUsage = ref<MeterUsage[]>([])

const customer = computed(() => {
  const customerId = route.params.id as string
  return customerStore.customers.find(c => c.id === customerId)
})

function formatDate(dateString?: string): string {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString()
}

function getUnitForMeter(meterKey: string): string {
  if (meterKey.includes('tokens')) return 'tokens'
  if (meterKey.includes('calls')) return 'calls'
  if (meterKey.includes('workflow')) return 'workflows'
  if (meterKey.includes('storage')) return 'GB-hours'
  return 'units'
}

function getPeriodDates(period: string) {
  const now = new Date()
  let start: Date, end: Date

  switch (period) {
    case 'current_month':
      start = new Date(now.getFullYear(), now.getMonth(), 1)
      end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      break
    case 'last_month':
      start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      end = new Date(now.getFullYear(), now.getMonth(), 0)
      break
    case 'last_7_days':
      start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      end = now
      break
    default:
      start = new Date(now.getFullYear(), now.getMonth(), 1)
      end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  }

  return {
    start: start.toISOString(),
    end: end.toISOString(),
  }
}

async function loadUsageData() {
  if (!customer.value) return

  usageLoading.value = true
  try {
    const { start, end } = getPeriodDates(selectedPeriod.value)

    const [summary, meters] = await Promise.all([
      customerStore.fetchCustomerUsage(customer.value.id, start, end),
      customerStore.fetchCustomerMeters(customer.value.id, start, end),
    ])

    usageSummary.value = summary
    meterUsage.value = meters
  } catch (err) {
    console.error('Failed to load usage data:', err)
  } finally {
    usageLoading.value = false
  }
}

onMounted(async () => {
  try {
    if (customerStore.customers.length === 0) {
      await customerStore.fetchCustomers()
    }

    if (customer.value) {
      await loadUsageData()
    } else {
      error.value = 'Customer not found'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load customer data'
  } finally {
    loading.value = false
  }
})
</script>
