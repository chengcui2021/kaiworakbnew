export interface BreadcrumbItem {
  label: string
  to: string | null
}

declare module 'vue-router' {
  interface RouteMeta {
    layout?: string
    breadcrumb?: BreadcrumbItem[]
  }
}
