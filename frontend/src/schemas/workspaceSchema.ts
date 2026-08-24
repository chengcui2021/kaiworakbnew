import { z } from 'zod'

export const workspaceSchema = z.object({
  name: z.string().trim().min(1, 'Name is required'),
  description: z.string().optional(),
})

export type WorkspaceFormValues = z.infer<typeof workspaceSchema>
