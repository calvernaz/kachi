<template>
  <nav class="bg-white shadow-sm border-b border-gray-200">
    <div class="container mx-auto px-4">
      <div class="flex justify-between items-center h-16">
        <!-- Logo -->
        <div class="flex items-center">
          <h1 class="text-xl font-bold text-gray-900">Kachi Dashboard</h1>
        </div>

        <!-- Navigation Links -->
        <div class="hidden md:block">
          <div class="ml-10 flex items-baseline space-x-4">
            <RouterLink
              to="/"
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="{ 'text-blue-600 bg-blue-50': $route.path === '/' }"
            >
              Dashboard
            </RouterLink>
            <RouterLink
              to="/customers"
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="{ 'text-blue-600 bg-blue-50': $route.path.startsWith('/customers') }"
            >
              Customers
            </RouterLink>
            <RouterLink
              to="/usage"
              class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="{ 'text-blue-600 bg-blue-50': $route.path.startsWith('/usage') }"
            >
              Usage
            </RouterLink>
          </div>
        </div>

        <!-- Mobile menu button -->
        <div class="md:hidden">
          <button
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="text-gray-600 hover:text-gray-900 focus:outline-none focus:text-gray-900"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                v-if="!mobileMenuOpen"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
              <path
                v-else
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <div v-if="mobileMenuOpen" class="md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
          <RouterLink
            to="/"
            class="text-gray-600 hover:text-gray-900 block px-3 py-2 rounded-md text-base font-medium"
            :class="{ 'text-blue-600 bg-blue-50': $route.path === '/' }"
            @click="mobileMenuOpen = false"
          >
            Dashboard
          </RouterLink>
          <RouterLink
            to="/customers"
            class="text-gray-600 hover:text-gray-900 block px-3 py-2 rounded-md text-base font-medium"
            :class="{ 'text-blue-600 bg-blue-50': $route.path.startsWith('/customers') }"
            @click="mobileMenuOpen = false"
          >
            Customers
          </RouterLink>
          <RouterLink
            to="/usage"
            class="text-gray-600 hover:text-gray-900 block px-3 py-2 rounded-md text-base font-medium"
            :class="{ 'text-blue-600 bg-blue-50': $route.path.startsWith('/usage') }"
            @click="mobileMenuOpen = false"
          >
            Usage
          </RouterLink>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const mobileMenuOpen = ref(false)
</script>
