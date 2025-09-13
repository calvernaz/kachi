<template>
  <div class="min-h-screen bg-slate-50 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-slate-900">Billing & Cost Management</h1>
            <p class="mt-2 text-slate-600">
              Interactive billing preview, cost projections, and usage optimization
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <button
              @click="refreshAllData"
              :disabled="refreshing"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2 transition-colors"
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

      <!-- Tab Navigation -->
      <div class="border-b border-slate-200 mb-8">
        <nav class="-mb-px flex space-x-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="tab.icon === 'preview'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              <path v-else-if="tab.icon === 'simulator'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4"></path>
              <path v-else-if="tab.icon === 'plans'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
            <span>{{ tab.name }}</span>
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="space-y-8">
        <!-- Billing Preview Tab -->
        <div v-if="activeTab === 'preview'">
          <BillingPreview />
        </div>

        <!-- Usage Simulator Tab -->
        <div v-if="activeTab === 'simulator'" class="space-y-6">
          <UsageSimulator @usage-changed="handleUsageChange" />

          <!-- Real-time Cost Impact -->
          <div v-if="simulatedUsage" class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 class="text-lg font-semibold text-slate-900 mb-4">Simulated Cost Impact</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div class="text-center p-4 bg-blue-50 rounded-lg">
                <p class="text-2xl font-bold text-blue-600">${{ formatCurrency(simulatedCosts.current) }}</p>
                <p class="text-sm text-slate-600">Current Scenario</p>
              </div>
              <div class="text-center p-4 bg-green-50 rounded-lg">
                <p class="text-2xl font-bold text-green-600">${{ formatCurrency(simulatedCosts.optimistic) }}</p>
                <p class="text-sm text-slate-600">Growth Scenario</p>
              </div>
              <div class="text-center p-4 bg-orange-50 rounded-lg">
                <p class="text-2xl font-bold text-orange-600">${{ formatCurrency(simulatedCosts.conservative) }}</p>
                <p class="text-sm text-slate-600">Conservative Scenario</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Pricing Plans Tab -->
        <div v-if="activeTab === 'plans'" class="space-y-6">
          <!-- Plan Comparison -->
          <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 class="text-lg font-semibold text-slate-900 mb-6">Pricing Plans Comparison</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div v-for="plan in pricingPlans" :key="plan.name" class="border border-slate-200 rounded-lg p-6 relative">
                <div v-if="plan.popular" class="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span class="bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium">Most Popular</span>
                </div>
                <div class="text-center">
                  <h4 class="text-xl font-semibold text-slate-900">{{ plan.name }}</h4>
                  <p class="text-slate-600 mt-2">{{ plan.description }}</p>
                  <div class="mt-4">
                    <span class="text-4xl font-bold text-slate-900">${{ plan.basePrice }}</span>
                    <span class="text-slate-600">/month</span>
                  </div>
                </div>
                <ul class="mt-6 space-y-3">
                  <li v-for="feature in plan.features" :key="feature" class="flex items-center">
                    <svg class="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span class="text-sm text-slate-600">{{ feature }}</span>
                  </li>
                </ul>
                <button
                  :class="[
                    'w-full mt-6 px-4 py-2 rounded-md font-medium transition-colors',
                    plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
                  ]"
                >
                  {{ plan.popular ? 'Get Started' : 'Learn More' }}
                </button>
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
import BillingPreview from '@/components/BillingPreview.vue'
import UsageSimulator from '@/components/UsageSimulator.vue'

const activeTab = ref('preview')
const refreshing = ref(false)
const lastUpdated = ref(new Date().toLocaleTimeString())
const simulatedUsage = ref<Record<string, number> | null>(null)

const tabs = [
  { id: 'preview', name: 'Billing Preview', icon: 'preview' },
  { id: 'simulator', name: 'Usage Simulator', icon: 'simulator' },
  { id: 'plans', name: 'Pricing Plans', icon: 'plans' },
]

const simulatedCosts = ref({
  current: 0,
  optimistic: 0,
  conservative: 0
})

const pricingPlans = ref([
  {
    name: 'Starter',
    description: 'Perfect for small teams and prototypes',
    basePrice: 29,
    popular: false,
    features: [
      '10,000 API calls/month',
      '100 workflow executions',
      '1M LLM tokens',
      '10GB storage',
      'Email support'
    ]
  },
  {
    name: 'Professional',
    description: 'Ideal for growing businesses',
    basePrice: 99,
    popular: true,
    features: [
      '100,000 API calls/month',
      '1,000 workflow executions',
      '10M LLM tokens',
      '100GB storage',
      'Priority support',
      'Advanced analytics'
    ]
  },
  {
    name: 'Enterprise',
    description: 'For large-scale operations',
    basePrice: 299,
    popular: false,
    features: [
      'Unlimited API calls',
      'Unlimited workflows',
      'Unlimited LLM tokens',
      '1TB storage',
      '24/7 dedicated support',
      'Custom integrations',
      'SLA guarantees'
    ]
  }
])

function handleUsageChange(usage: Record<string, number>) {
  simulatedUsage.value = usage

  const baseCost = calculateCost(usage)
  simulatedCosts.value = {
    current: baseCost,
    optimistic: baseCost * 1.5,
    conservative: baseCost * 0.8
  }
}

function calculateCost(usage: Record<string, number>): number {
  const pricing = {
    api_calls: 0.001,
    workflows: 0.05,
    llm_tokens: 0.00002,
    storage: 0.10
  }

  return Object.entries(usage).reduce((total, [key, value]) => {
    const price = pricing[key as keyof typeof pricing] || 0
    return total + (value * price)
  }, 0)
}

function formatCurrency(amount: number): string {
  return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function refreshAllData() {
  refreshing.value = true

  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('Failed to refresh data:', error)
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  handleUsageChange({
    api_calls: 50000,
    workflows: 1000,
    llm_tokens: 1000000,
    storage: 100
  })
})
</script>
