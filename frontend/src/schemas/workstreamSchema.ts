import { z } from 'zod'

export const workstreamSchema = z.object({
  name: z.string().trim().min(1, 'Name is required'),
  description: z.string().optional(),
})

export type WorkstreamFormValues = z.infer<typeof workstreamSchema>
