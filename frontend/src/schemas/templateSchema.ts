import { z } from 'zod'

export const templateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Name is required')
    .max(255, 'Name must be 255 characters or fewer'),
  content: z.string().trim().min(1, 'Content is required'),
})

export type TemplateFormValues = z.infer<typeof templateSchema>
