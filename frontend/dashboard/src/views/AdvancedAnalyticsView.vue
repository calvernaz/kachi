<template>
  <div class="min-h-screen bg-slate-50 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-slate-900">Advanced Analytics</h1>
            <p class="mt-2 text-slate-600">
              AI-powered predictive analytics, cost forecasting, and intelligent insights
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <button
              @click="refreshAllAnalytics"
              :disabled="refreshing"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center space-x-2 transition-colors"
            >
              <svg v-if="refreshing" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              <span>Refresh Analytics</span>
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
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="tab.icon === 'predictive'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              <path v-else-if="tab.icon === 'forecasting'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              <path v-else-if="tab.icon === 'alerts'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5v-5zM10.5 9.5L9 11l-5-5L9 1l1.5 1.5L13 0l5 5-3 3h-4.5z"></path>
              <path v-else-if="tab.icon === 'insights'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
            </svg>
            <span>{{ tab.name }}</span>
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="space-y-8">
        <!-- Predictive Billing Tab -->
        <div v-if="activeTab === 'predictive'">
          <PredictiveBilling />
        </div>

        <!-- Cost Forecasting Tab -->
        <div v-if="activeTab === 'forecasting'">
          <CostForecastingEngine />
        </div>

        <!-- Smart Alerts Tab -->
        <div v-if="activeTab === 'alerts'" class="space-y-6">
          <!-- Alert Configuration -->
          <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 class="text-lg font-semibold text-slate-900 mb-4">Smart Alert Configuration</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div v-for="alertType in alertTypes" :key="alertType.id" class="border border-slate-200 rounded-lg p-4">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center space-x-3">
                    <div :class="['w-3 h-3 rounded-full', alertType.enabled ? 'bg-green-500' : 'bg-slate-300']"></div>
                    <h4 class="font-medium text-slate-900">{{ alertType.name }}</h4>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input
                      v-model="alertType.enabled"
                      type="checkbox"
                      class="sr-only peer"
                    >
                    <div class="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                <p class="text-sm text-slate-600 mb-3">{{ alertType.description }}</p>
                <div class="space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-slate-600">Threshold</span>
                    <input
                      v-model="alertType.threshold"
                      type="number"
                      :disabled="!alertType.enabled"
                      class="w-20 px-2 py-1 text-sm border border-slate-300 rounded disabled:bg-slate-100"
                    >
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-slate-600">Frequency</span>
                    <select
                      v-model="alertType.frequency"
                      :disabled="!alertType.enabled"
                      class="px-2 py-1 text-sm border border-slate-300 rounded disabled:bg-slate-100"
                    >
                      <option value="immediate">Immediate</option>
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Active Alerts -->
          <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 class="text-lg font-semibold text-slate-900 mb-4">Active Alerts</h3>
            <div class="space-y-3">
              <div v-for="alert in activeAlerts" :key="alert.id" :class="['flex items-start space-x-3 p-4 rounded-lg border-l-4', alert.severity === 'high' ? 'bg-red-50 border-red-500' : alert.severity === 'medium' ? 'bg-yellow-50 border-yellow-500' : 'bg-blue-50 border-blue-500']">
                <div class="flex-shrink-0 mt-1">
                  <svg :class="['h-5 w-5', alert.severity === 'high' ? 'text-red-500' : alert.severity === 'medium' ? 'text-yellow-500' : 'text-blue-500']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path v-if="alert.severity === 'high'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    <path v-else-if="alert.severity === 'medium'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                </div>
                <div class="flex-1">
                  <div class="flex items-center justify-between">
                    <h4 class="font-medium text-slate-900">{{ alert.title }}</h4>
                    <span class="text-sm text-slate-500">{{ alert.timestamp }}</span>
                  </div>
                  <p class="text-sm text-slate-600 mt-1">{{ alert.message }}</p>
                  <div class="flex items-center space-x-3 mt-2">
                    <button class="text-sm text-blue-600 hover:text-blue-800 font-medium">View Details</button>
                    <button class="text-sm text-slate-600 hover:text-slate-800">Dismiss</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI Insights Tab -->
        <div v-if="activeTab === 'insights'" class="space-y-6">
          <!-- Insight Categories -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div v-for="category in insightCategories" :key="category.name" class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
              <div class="flex items-center space-x-3 mb-4">
                <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', category.bgColor]">
                  <svg :class="['h-5 w-5', category.iconColor]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path v-if="category.icon === 'optimization'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    <path v-else-if="category.icon === 'trends'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                  </svg>
                </div>
                <div>
                  <h3 class="font-semibold text-slate-900">{{ category.name }}</h3>
                  <p class="text-sm text-slate-600">{{ category.count }} insights</p>
                </div>
              </div>
              <div class="space-y-3">
                <div v-for="insight in category.insights" :key="insight.id" class="p-3 bg-slate-50 rounded-lg">
                  <p class="text-sm font-medium text-slate-900">{{ insight.title }}</p>
                  <p class="text-xs text-slate-600 mt-1">{{ insight.description }}</p>
                  <div class="flex items-center justify-between mt-2">
                    <span :class="['text-xs px-2 py-1 rounded-full', insight.impact === 'high' ? 'bg-green-100 text-green-800' : insight.impact === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800']">
                      {{ insight.impact }} impact
                    </span>
                    <button class="text-xs text-blue-600 hover:text-blue-800 font-medium">Apply</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Comprehensive Insights Dashboard -->
          <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 class="text-lg font-semibold text-slate-900 mb-4">Comprehensive AI Analysis</h3>
            <div class="prose max-w-none text-slate-600">
              <p class="mb-4">
                Based on your usage patterns over the last 90 days, our AI has identified several key insights and optimization opportunities:
              </p>
              <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-4">
                <h4 class="font-semibold text-slate-900 mb-2">Key Findings</h4>
                <ul class="space-y-2 text-sm">
                  <li>• API usage shows strong correlation with business hours (9 AM - 6 PM)</li>
                  <li>• LLM token consumption peaks on Tuesdays and Wednesdays</li>
                  <li>• Storage growth is linear at 12% monthly rate</li>
                  <li>• Workflow efficiency has improved 23% over the last quarter</li>
                </ul>
              </div>
              <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4">
                <h4 class="font-semibold text-slate-900 mb-2">Recommended Actions</h4>
                <ul class="space-y-2 text-sm">
                  <li>• Implement request batching during peak hours for 15% cost reduction</li>
                  <li>• Consider reserved capacity for predictable workloads</li>
                  <li>• Enable intelligent caching for frequently accessed data</li>
                  <li>• Optimize LLM prompts to reduce token usage by 20%</li>
                </ul>
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
import PredictiveBilling from '@/components/PredictiveBilling.vue'
import CostForecastingEngine from '@/components/CostForecastingEngine.vue'

const activeTab = ref('predictive')
const refreshing = ref(false)
const lastUpdated = ref(new Date().toLocaleTimeString())

const tabs = [
  { id: 'predictive', name: 'Predictive Billing', icon: 'predictive' },
  { id: 'forecasting', name: 'Cost Forecasting', icon: 'forecasting' },
  { id: 'alerts', name: 'Smart Alerts', icon: 'alerts' },
  { id: 'insights', name: 'AI Insights', icon: 'insights' },
]

const alertTypes = ref([
  {
    id: 1,
    name: 'Budget Overrun',
    description: 'Alert when costs exceed budget threshold',
    enabled: true,
    threshold: 90,
    frequency: 'immediate'
  },
  {
    id: 2,
    name: 'Usage Anomaly',
    description: 'Detect unusual usage patterns',
    enabled: true,
    threshold: 150,
    frequency: 'hourly'
  },
  {
    id: 3,
    name: 'Cost Spike',
    description: 'Alert on sudden cost increases',
    enabled: false,
    threshold: 200,
    frequency: 'immediate'
  },
  {
    id: 4,
    name: 'Optimization Opportunity',
    description: 'Identify potential cost savings',
    enabled: true,
    threshold: 10,
    frequency: 'daily'
  }
])

const activeAlerts = ref([
  {
    id: 1,
    title: 'Budget Threshold Exceeded',
    message: 'Monthly costs are 15% above budget target. Consider implementing cost optimization measures.',
    severity: 'high',
    timestamp: '2 hours ago'
  },
  {
    id: 2,
    title: 'Unusual API Usage Pattern',
    message: 'API calls increased by 45% compared to last week. This may indicate a new integration or potential issue.',
    severity: 'medium',
    timestamp: '6 hours ago'
  },
  {
    id: 3,
    title: 'Optimization Opportunity',
    message: 'Implementing response caching could reduce costs by $450/month based on current usage patterns.',
    severity: 'low',
    timestamp: '1 day ago'
  }
])

const insightCategories = ref([
  {
    name: 'Cost Optimization',
    count: 5,
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    icon: 'optimization',
    insights: [
      {
        id: 1,
        title: 'API Response Caching',
        description: 'Reduce redundant calls by 30%',
        impact: 'high'
      },
      {
        id: 2,
        title: 'Storage Compression',
        description: 'Compress older data for savings',
        impact: 'medium'
      }
    ]
  },
  {
    name: 'Usage Trends',
    count: 3,
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    icon: 'trends',
    insights: [
      {
        id: 3,
        title: 'Peak Hour Analysis',
        description: 'Usage concentrated in business hours',
        impact: 'medium'
      },
      {
        id: 4,
        title: 'Seasonal Patterns',
        description: 'Q4 shows 22% increase',
        impact: 'high'
      }
    ]
  },
  {
    name: 'Risk Factors',
    count: 2,
    bgColor: 'bg-red-100',
    iconColor: 'text-red-600',
    icon: 'risk',
    insights: [
      {
        id: 5,
        title: 'Budget Overrun Risk',
        description: 'Projected to exceed budget by 12%',
        impact: 'high'
      },
      {
        id: 6,
        title: 'Usage Volatility',
        description: 'High variance in daily usage',
        impact: 'low'
      }
    ]
  }
])

async function refreshAllAnalytics() {
  refreshing.value = true
  try {
    // Simulate API calls to refresh all analytics data
    await new Promise(resolve => setTimeout(resolve, 2000))
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('Failed to refresh analytics:', error)
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  // Initialize analytics data
})
</script>
