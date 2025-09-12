<template>
  <div class="bg-white rounded-lg shadow">
    <div class="p-6 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
        <span class="text-sm text-gray-500">{{ period }}</span>
      </div>
    </div>
    <div class="p-6">
      <div class="space-y-4">
        <!-- Usage Progress Bar -->
        <div>
          <div class="flex justify-between text-sm text-gray-600 mb-2">
            <span>{{ currentValue.toLocaleString() }} / {{ maxValue.toLocaleString() }} {{ unit }}</span>
            <span>{{ percentage.toFixed(1) }}%</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="h-2 rounded-full transition-all duration-300"
              :class="progressBarColor"
              :style="{ width: `${Math.min(percentage, 100)}%` }"
            ></div>
          </div>
        </div>

        <!-- Usage Details -->
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Included:</span>
            <span class="font-medium text-gray-900 ml-1">{{ includedValue.toLocaleString() }}</span>
          </div>
          <div>
            <span class="text-gray-500">Overage:</span>
            <span class="font-medium text-gray-900 ml-1">{{ overageValue.toLocaleString() }}</span>
          </div>
        </div>

        <!-- Cost Information -->
        <div v-if="cost > 0" class="pt-4 border-t border-gray-100">
          <div class="flex justify-between items-center">
            <span class="text-sm text-gray-500">Current Cost:</span>
            <span class="font-semibold text-gray-900">€{{ cost.toFixed(2) }}</span>
          </div>
        </div>

        <!-- Alert if over limit -->
        <div v-if="percentage > 90" class="p-3 bg-red-50 border border-red-200 rounded-md">
          <div class="flex">
            <svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <div class="ml-3">
              <p class="text-sm text-red-800">
                <strong>High Usage Alert:</strong> You've used {{ percentage.toFixed(1) }}% of your allowance.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  title: string
  currentValue: number
  maxValue: number
  includedValue: number
  unit: string
  cost?: number
  period?: string
}

const props = withDefaults(defineProps<Props>(), {
  cost: 0,
  period: 'This month',
})

const percentage = computed(() => {
  return props.maxValue > 0 ? (props.currentValue / props.maxValue) * 100 : 0
})

const overageValue = computed(() => {
  return Math.max(0, props.currentValue - props.includedValue)
})

const progressBarColor = computed(() => {
  if (percentage.value >= 100) return 'bg-red-500'
  if (percentage.value >= 90) return 'bg-yellow-500'
  if (percentage.value >= 75) return 'bg-orange-500'
  return 'bg-blue-500'
})
</script>
