<template>
  <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-lg font-semibold text-slate-900">Cost Forecasting Engine</h3>
        <p class="text-sm text-slate-600">Advanced ML-powered cost predictions and budget planning</p>
      </div>
      <div class="flex items-center space-x-3">
        <select
          v-model="selectedModel"
          @change="updateForecast"
          class="px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="linear">Linear Regression</option>
          <option value="polynomial">Polynomial Fit</option>
          <option value="seasonal">Seasonal ARIMA</option>
          <option value="neural">Neural Network</option>
        </select>
        <button
          @click="runForecast"
          :disabled="loading"
          class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <svg v-if="loading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
          </svg>
          <span>Run Forecast</span>
        </button>
      </div>
    </div>

    <!-- Model Performance Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div v-for="metric in modelMetrics" :key="metric.name" class="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-slate-600">{{ metric.name }}</p>
            <p class="text-xl font-bold text-slate-900">{{ metric.value }}</p>
            <p class="text-xs text-slate-500 mt-1">{{ metric.description }}</p>
          </div>
          <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
            <svg class="h-5 w-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="metric.icon === 'accuracy'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              <path v-else-if="metric.icon === 'error'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              <path v-else-if="metric.icon === 'confidence'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Forecast Scenarios -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      <div v-for="scenario in forecastScenarios" :key="scenario.name" class="border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between mb-3">
          <h4 class="font-semibold text-slate-900">{{ scenario.name }}</h4>
          <span :class="['px-2 py-1 rounded-full text-xs font-medium', scenario.badgeClass]">
            {{ scenario.probability }}% likely
          </span>
        </div>
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-sm text-slate-600">Next Month</span>
            <span class="font-semibold text-slate-900">${{ formatCurrency(scenario.nextMonth) }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-slate-600">Next Quarter</span>
            <span class="font-semibold text-slate-900">${{ formatCurrency(scenario.nextQuarter) }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-sm text-slate-600">Annual Projection</span>
            <span class="font-semibold text-slate-900">${{ formatCurrency(scenario.annual) }}</span>
          </div>
          <div class="pt-2 border-t border-slate-200">
            <p class="text-xs text-slate-600">{{ scenario.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Budget Planning -->
    <div class="bg-slate-50 rounded-lg p-6 mb-6">
      <h4 class="text-md font-semibold text-slate-900 mb-4">Budget Planning Assistant</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">Monthly Budget Target</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500">$</span>
            <input
              v-model.number="budgetTarget"
              type="number"
              class="pl-8 pr-3 py-2 w-full border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="5000"
              @input="updateBudgetAnalysis"
            >
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">Planning Horizon</label>
          <select
            v-model="planningHorizon"
            @change="updateBudgetAnalysis"
            class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="3">3 Months</option>
            <option value="6">6 Months</option>
            <option value="12">12 Months</option>
            <option value="24">24 Months</option>
          </select>
        </div>
      </div>
      
      <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="text-center p-3 bg-white rounded-lg">
          <p class="text-sm text-slate-600">Budget Utilization</p>
          <p class="text-xl font-bold text-slate-900">{{ budgetUtilization }}%</p>
          <div class="w-full bg-slate-200 rounded-full h-2 mt-2">
            <div 
              :class="['h-2 rounded-full', budgetUtilization > 90 ? 'bg-red-500' : budgetUtilization > 75 ? 'bg-yellow-500' : 'bg-green-500']"
              :style="{ width: Math.min(budgetUtilization, 100) + '%' }"
            ></div>
          </div>
        </div>
        <div class="text-center p-3 bg-white rounded-lg">
          <p class="text-sm text-slate-600">Projected Variance</p>
          <p :class="['text-xl font-bold', budgetVariance > 0 ? 'text-red-600' : 'text-green-600']">
            {{ budgetVariance > 0 ? '+' : '' }}${{ formatCurrency(Math.abs(budgetVariance)) }}
          </p>
          <p class="text-xs text-slate-500 mt-1">vs target budget</p>
        </div>
        <div class="text-center p-3 bg-white rounded-lg">
          <p class="text-sm text-slate-600">Runway</p>
          <p class="text-xl font-bold text-slate-900">{{ budgetRunway }} months</p>
          <p class="text-xs text-slate-500 mt-1">at current rate</p>
        </div>
      </div>
    </div>

    <!-- Cost Optimization Recommendations -->
    <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-6">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <div class="flex-1">
          <h4 class="text-md font-semibold text-slate-900 mb-3">Cost Optimization Recommendations</h4>
          <div class="space-y-3">
            <div v-for="recommendation in optimizationRecommendations" :key="recommendation.id" class="flex items-start space-x-3 p-3 bg-white rounded-lg">
              <div class="flex-shrink-0 mt-1">
                <div :class="['w-2 h-2 rounded-full', recommendation.impact === 'high' ? 'bg-green-500' : recommendation.impact === 'medium' ? 'bg-yellow-500' : 'bg-blue-500']"></div>
              </div>
              <div class="flex-1">
                <div class="flex items-center justify-between">
                  <p class="text-sm font-medium text-slate-900">{{ recommendation.title }}</p>
                  <span class="text-sm font-semibold text-green-600">Save ${{ formatCurrency(recommendation.savings) }}/mo</span>
                </div>
                <p class="text-sm text-slate-600 mt-1">{{ recommendation.description }}</p>
                <div class="flex items-center justify-between mt-2">
                  <span class="text-xs text-slate-500">Implementation: {{ recommendation.effort }}</span>
                  <button class="text-xs text-blue-600 hover:text-blue-800 font-medium">Learn More</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const loading = ref(false)
const selectedModel = ref('seasonal')
const budgetTarget = ref(5000)
const planningHorizon = ref(6)

const modelMetrics = ref([
  {
    name: 'Accuracy',
    value: '94.2%',
    description: 'Prediction accuracy',
    icon: 'accuracy'
  },
  {
    name: 'MAPE',
    value: '5.8%',
    description: 'Mean absolute error',
    icon: 'error'
  },
  {
    name: 'Confidence',
    value: '92%',
    description: 'Model confidence',
    icon: 'confidence'
  },
  {
    name: 'R²',
    value: '0.89',
    description: 'Goodness of fit',
    icon: 'trend'
  }
])

const forecastScenarios = ref([
  {
    name: 'Conservative',
    probability: 75,
    nextMonth: 1150.00,
    nextQuarter: 3600.00,
    annual: 14400.00,
    description: 'Based on current usage patterns with minimal growth',
    badgeClass: 'bg-green-100 text-green-800'
  },
  {
    name: 'Most Likely',
    probability: 85,
    nextMonth: 1350.00,
    nextQuarter: 4200.00,
    annual: 16800.00,
    description: 'Expected scenario considering seasonal trends and growth',
    badgeClass: 'bg-blue-100 text-blue-800'
  },
  {
    name: 'Aggressive',
    probability: 45,
    nextMonth: 1650.00,
    nextQuarter: 5100.00,
    annual: 20400.00,
    description: 'High growth scenario with increased feature adoption',
    badgeClass: 'bg-orange-100 text-orange-800'
  }
])

const optimizationRecommendations = ref([
  {
    id: 1,
    title: 'Implement API Response Caching',
    description: 'Cache frequently requested API responses to reduce redundant calls by 30%',
    savings: 450.00,
    effort: 'Medium',
    impact: 'high'
  },
  {
    id: 2,
    title: 'Optimize LLM Token Usage',
    description: 'Use prompt engineering and context compression to reduce token consumption',
    savings: 320.00,
    effort: 'Low',
    impact: 'high'
  },
  {
    id: 3,
    title: 'Storage Lifecycle Management',
    description: 'Implement automated data archiving for older, less-accessed data',
    savings: 180.00,
    effort: 'High',
    impact: 'medium'
  },
  {
    id: 4,
    title: 'Workflow Optimization',
    description: 'Consolidate similar workflows to reduce execution overhead',
    savings: 125.00,
    effort: 'Medium',
    impact: 'medium'
  }
])

const budgetUtilization = computed(() => {
  const currentProjected = 1350.00 // Most likely scenario
  return Math.round((currentProjected / budgetTarget.value) * 100)
})

const budgetVariance = computed(() => {
  const currentProjected = 1350.00
  return currentProjected - budgetTarget.value
})

const budgetRunway = computed(() => {
  const totalBudget = budgetTarget.value * planningHorizon.value
  const currentProjected = 1350.00
  return Math.floor(totalBudget / currentProjected)
})

function formatCurrency(amount: number): string {
  return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function runForecast() {
  loading.value = true
  try {
    // Simulate ML model execution
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Update model metrics based on selected model
    const modelAccuracy = {
      linear: { accuracy: '87.3%', mape: '12.7%', confidence: '78%', r2: '0.76' },
      polynomial: { accuracy: '91.8%', mape: '8.2%', confidence: '85%', r2: '0.84' },
      seasonal: { accuracy: '94.2%', mape: '5.8%', confidence: '92%', r2: '0.89' },
      neural: { accuracy: '96.1%', mape: '3.9%', confidence: '95%', r2: '0.92' }
    }
    
    const metrics = modelAccuracy[selectedModel.value as keyof typeof modelAccuracy]
    modelMetrics.value[0].value = metrics.accuracy
    modelMetrics.value[1].value = metrics.mape
    modelMetrics.value[2].value = metrics.confidence
    modelMetrics.value[3].value = metrics.r2
    
  } finally {
    loading.value = false
  }
}

function updateForecast() {
  // Update forecast based on selected model
  runForecast()
}

function updateBudgetAnalysis() {
  // Trigger reactive computations
  // The computed properties will automatically update
}

onMounted(() => {
  runForecast()
})
</script>
