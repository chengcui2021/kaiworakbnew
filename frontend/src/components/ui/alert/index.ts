import { cva, type VariantProps } from 'class-variance-authority'

export { default as Alert } from './Alert.vue'
export { default as AlertDescription } from './AlertDescription.vue'
export { default as AlertTitle } from './AlertTitle.vue'

export const alertVariants = cva(
  'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4',
  {
    variants: {
      variant: {
        default: 'bg-muted/50 border-border text-foreground [&>svg]:text-foreground',
        destructive: 'border-error bg-error-muted text-error-muted-foreground [&>svg]:text-error',
        success:
          'border-success bg-success-muted text-success-muted-foreground [&>svg]:text-success',
        warning:
          'border-warning bg-warning-muted text-warning-muted-foreground [&>svg]:text-warning',
        info: 'border-info bg-info-muted text-info-muted-foreground [&>svg]:text-info',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export type AlertVariants = VariantProps<typeof alertVariants>
