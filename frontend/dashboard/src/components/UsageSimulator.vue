<template>
  <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-slate-900">Usage Simulator</h3>
      <div class="flex items-center space-x-2">
        <button
          @click="resetToDefaults"
          class="px-3 py-1 text-sm bg-slate-600 text-white rounded-md hover:bg-slate-700"
        >
          Reset
        </button>
        <button
          @click="applyChanges"
          :disabled="!hasChanges"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          Apply Changes
        </button>
      </div>
    </div>

    <div class="space-y-6">
      <!-- Usage Meters -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div v-for="meter in meters" :key="meter.key" class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="font-medium text-slate-900">{{ meter.name }}</h4>
              <p class="text-sm text-slate-600">{{ meter.description }}</p>
            </div>
            <div class="text-right">
              <p class="text-lg font-semibold text-slate-900">{{ formatNumber(meter.value) }}</p>
              <p class="text-sm text-slate-600">{{ meter.unit }}</p>
            </div>
          </div>

          <!-- Slider -->
          <div class="space-y-2">
            <input
              v-model.number="meter.value"
              type="range"
              :min="meter.min"
              :max="meter.max"
              :step="meter.step"
              class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer slider"
              @input="updateMeter(meter.key, meter.value)"
            >
            <div class="flex justify-between text-xs text-slate-500">
              <span>{{ formatNumber(meter.min) }}</span>
              <span>{{ formatNumber(meter.max) }}</span>
            </div>
          </div>

          <!-- Direct Input -->
          <div class="flex items-center space-x-2">
            <input
              v-model.number="meter.value"
              type="number"
              :min="meter.min"
              :max="meter.max"
              :step="meter.step"
              class="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              @input="updateMeter(meter.key, meter.value)"
            >
            <span class="text-sm text-slate-600">{{ meter.unit }}</span>
          </div>

          <!-- Cost Impact -->
          <div class="bg-slate-50 rounded-lg p-3">
            <div class="flex justify-between items-center">
              <span class="text-sm text-slate-600">Estimated Cost</span>
              <span class="font-semibold text-slate-900">${{ formatCurrency(meter.estimatedCost) }}</span>
            </div>
            <div class="flex justify-between items-center mt-1">
              <span class="text-sm text-slate-600">vs Current</span>
              <span
                :class="[
                  'text-sm font-medium',
                  meter.costChange >= 0 ? 'text-green-600' : 'text-red-600'
                ]"
              >
                {{ meter.costChange >= 0 ? '+' : '' }}${{ formatCurrency(Math.abs(meter.costChange)) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Total Impact Summary -->
      <div class="border-t border-slate-200 pt-6">
        <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
          <h4 class="text-lg font-semibold text-slate-900 mb-4">Total Impact</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="text-center">
              <p class="text-2xl font-bold text-blue-600">${{ formatCurrency(totalEstimatedCost) }}</p>
              <p class="text-sm text-slate-600">Estimated Monthly Cost</p>
            </div>
            <div class="text-center">
              <p
                :class="[
                  'text-2xl font-bold',
                  totalCostChange >= 0 ? 'text-green-600' : 'text-red-600'
                ]"
              >
                {{ totalCostChange >= 0 ? '+' : '' }}${{ formatCurrency(Math.abs(totalCostChange)) }}
              </p>
              <p class="text-sm text-slate-600">Change from Current</p>
            </div>
            <div class="text-center">
              <p
                :class="[
                  'text-2xl font-bold',
                  totalPercentChange >= 0 ? 'text-green-600' : 'text-red-600'
                ]"
              >
                {{ totalPercentChange >= 0 ? '+' : '' }}{{ totalPercentChange.toFixed(1) }}%
              </p>
              <p class="text-sm text-slate-600">Percentage Change</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Preset Scenarios -->
      <div class="border-t border-slate-200 pt-6">
        <h4 class="text-md font-semibold text-slate-900 mb-4">Quick Scenarios</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            v-for="scenario in presetScenarios"
            :key="scenario.name"
            @click="applyScenario(scenario)"
            class="p-4 border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
          >
            <div class="flex items-center space-x-3">
              <div class="flex-shrink-0">
                <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path v-if="scenario.icon === 'growth'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                  <path v-else-if="scenario.icon === 'stable'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                  <path v-else-if="scenario.icon === 'conservative'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
                </svg>
              </div>
              <div>
                <h5 class="font-medium text-slate-900">{{ scenario.name }}</h5>
                <p class="text-sm text-slate-600">{{ scenario.description }}</p>
                <p class="text-sm font-medium text-blue-600 mt-1">${{ formatCurrency(scenario.estimatedCost) }}/month</p>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Meter {
  key: string
  name: string
  description: string
  value: number
  originalValue: number
  min: number
  max: number
  step: number
  unit: string
  unitPrice: number
  estimatedCost: number
  costChange: number
}

interface PresetScenario {
  name: string
  description: string
  icon: string
  multipliers: Record<string, number>
  estimatedCost: number
}

const emit = defineEmits<{
  usageChanged: [meters: Record<string, number>]
}>()

const meters = ref<Meter[]>([
  {
    key: 'api_calls',
    name: 'API Calls',
    description: 'Number of API requests per month',
    value: 50000,
    originalValue: 50000,
    min: 0,
    max: 1000000,
    step: 1000,
    unit: 'calls',
    unitPrice: 0.001,
    estimatedCost: 50,
    costChange: 0
  },
  {
    key: 'workflows',
    name: 'Workflow Executions',
    description: 'Number of workflow runs per month',
    value: 1000,
    originalValue: 1000,
    min: 0,
    max: 50000,
    step: 100,
    unit: 'executions',
    unitPrice: 0.05,
    estimatedCost: 50,
    costChange: 0
  },
  {
    key: 'llm_tokens',
    name: 'LLM Tokens',
    description: 'Number of LLM tokens processed per month',
    value: 1000000,
    originalValue: 1000000,
    min: 0,
    max: 100000000,
    step: 10000,
    unit: 'tokens',
    unitPrice: 0.00002,
    estimatedCost: 20,
    costChange: 0
  },
  {
    key: 'storage',
    name: 'Storage Usage',
    description: 'Amount of data stored per month',
    value: 100,
    originalValue: 100,
    min: 0,
    max: 10000,
    step: 10,
    unit: 'GB',
    unitPrice: 0.10,
    estimatedCost: 10,
    costChange: 0
  }
])

const presetScenarios = ref<PresetScenario[]>([
  {
    name: 'High Growth',
    description: '3x current usage across all metrics',
    icon: 'growth',
    multipliers: {
      api_calls: 3,
      workflows: 3,
      llm_tokens: 3,
      storage: 2
    },
    estimatedCost: 390
  },
  {
    name: 'Steady State',
    description: 'Maintain current usage levels',
    icon: 'stable',
    multipliers: {
      api_calls: 1,
      workflows: 1,
      llm_tokens: 1,
      storage: 1
    },
    estimatedCost: 130
  },
  {
    name: 'Cost Optimization',
    description: 'Reduce usage by 50% for cost savings',
    icon: 'conservative',
    multipliers: {
      api_calls: 0.5,
      workflows: 0.5,
      llm_tokens: 0.5,
      storage: 0.7
    },
    estimatedCost: 72
  }
])

const hasChanges = computed(() => {
  return meters.value.some(meter => meter.value !== meter.originalValue)
})

const totalEstimatedCost = computed(() => {
  return meters.value.reduce((total, meter) => total + meter.estimatedCost, 0)
})

const totalCostChange = computed(() => {
  return meters.value.reduce((total, meter) => total + meter.costChange, 0)
})

const totalPercentChange = computed(() => {
  const originalTotal = meters.value.reduce((total, meter) => total + (meter.originalValue * meter.unitPrice), 0)
  if (originalTotal === 0) return 0
  return (totalCostChange.value / originalTotal) * 100
})

function updateMeter(key: string, value: number) {
  const meter = meters.value.find(m => m.key === key)
  if (!meter) return

  meter.value = value
  meter.estimatedCost = value * meter.unitPrice
  meter.costChange = meter.estimatedCost - (meter.originalValue * meter.unitPrice)

  emitUsageChange()
}

function resetToDefaults() {
  meters.value.forEach(meter => {
    meter.value = meter.originalValue
    meter.estimatedCost = meter.originalValue * meter.unitPrice
    meter.costChange = 0
  })
  emitUsageChange()
}

function applyChanges() {
  meters.value.forEach(meter => {
    meter.originalValue = meter.value
    meter.costChange = 0
  })
}

function applyScenario(scenario: PresetScenario) {
  meters.value.forEach(meter => {
    const multiplier = scenario.multipliers[meter.key] || 1
    meter.value = Math.round(meter.originalValue * multiplier)
    meter.estimatedCost = meter.value * meter.unitPrice
    meter.costChange = meter.estimatedCost - (meter.originalValue * meter.unitPrice)
  })
  emitUsageChange()
}

function emitUsageChange() {
  const usageData = meters.value.reduce((acc, meter) => {
    acc[meter.key] = meter.value
    return acc
  }, {} as Record<string, number>)

  emit('usageChanged', usageData)
}

function formatCurrency(amount: number): string {
  return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

// Watch for external changes and recalculate costs
watch(meters, () => {
  emitUsageChange()
}, { deep: true })
</script>

<style scoped>
.slider::-webkit-slider-thumb {
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: #3B82F6;
  cursor: pointer;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider::-moz-range-thumb {
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: #3B82F6;
  cursor: pointer;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
