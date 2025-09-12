import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export interface Customer {
  id: string
  name: string
  lago_customer_id: string
  currency: string
  created_at?: string
}

export interface UsageSummary {
  customer_id: string
  customer_name: string
  period_start: string
  period_end: string
  total_amount: number
  cogs: number
  margin: number
  meters: Record<string, number>
}

export interface MeterUsage {
  meter_key: string
  current_value: number
  included_allowance: number
  consumed_percentage: number
  overage_amount: number
  unit_price: number
}

export const useCustomerStore = defineStore('customer', () => {
  const customers = ref<Customer[]>([])
  const selectedCustomer = ref<Customer | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const apiClient = axios.create({
    baseURL: '/api',
    timeout: 10000,
  })

  async function fetchCustomers() {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get<Customer[]>('/customers')
      customers.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch customers'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCustomerUsage(
    customerId: string,
    periodStart: string,
    periodEnd: string
  ): Promise<UsageSummary> {
    const response = await apiClient.get<UsageSummary>(
      `/customers/${customerId}/usage`,
      {
        params: {
          period_start: periodStart,
          period_end: periodEnd,
        },
      }
    )
    return response.data
  }

  async function fetchCustomerMeters(
    customerId: string,
    periodStart: string,
    periodEnd: string
  ): Promise<MeterUsage[]> {
    const response = await apiClient.get<MeterUsage[]>(
      `/customers/${customerId}/meters`,
      {
        params: {
          period_start: periodStart,
          period_end: periodEnd,
        },
      }
    )
    return response.data
  }

  function selectCustomer(customer: Customer) {
    selectedCustomer.value = customer
  }

  return {
    customers,
    selectedCustomer,
    loading,
    error,
    fetchCustomers,
    fetchCustomerUsage,
    fetchCustomerMeters,
    selectCustomer,
  }
})
