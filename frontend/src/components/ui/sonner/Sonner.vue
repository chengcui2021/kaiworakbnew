<script lang="ts" setup>
import type { ToasterProps } from 'vue-sonner'
import { Toaster as Sonner } from 'vue-sonner'

import 'vue-sonner/style.css'

const props = defineProps<ToasterProps>()
</script>

<template>
  <Sonner v-bind="props" />
</template>
