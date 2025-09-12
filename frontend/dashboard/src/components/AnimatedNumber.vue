<template>
  <span>{{ displayValue }}</span>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

interface Props {
  value: number
  duration?: number
  decimals?: number
}

const props = withDefaults(defineProps<Props>(), {
  duration: 1000,
  decimals: 0,
})

const displayValue = ref('0')
const currentValue = ref(0)

function formatNumber(num: number): string {
  if (props.decimals === 0) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return Math.round(num).toLocaleString()
  }
  return num.toFixed(props.decimals)
}

function animateToValue(targetValue: number) {
  const startValue = currentValue.value
  const difference = targetValue - startValue
  const startTime = Date.now()

  function updateValue() {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / props.duration, 1)

    // Easing function (ease-out)
    const easedProgress = 1 - Math.pow(1 - progress, 3)

    currentValue.value = startValue + (difference * easedProgress)
    displayValue.value = formatNumber(currentValue.value)

    if (progress < 1) {
      requestAnimationFrame(updateValue)
    } else {
      currentValue.value = targetValue
      displayValue.value = formatNumber(targetValue)
    }
  }

  requestAnimationFrame(updateValue)
}

watch(() => props.value, (newValue) => {
  animateToValue(newValue)
}, { immediate: true })

onMounted(() => {
  displayValue.value = formatNumber(props.value)
  currentValue.value = props.value
})
</script>
