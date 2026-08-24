import { z } from 'zod'

export const submitEntrySchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, 'Title is required')
    .max(255, 'Title must be 255 characters or fewer'),
  content: z.string().trim().min(1, 'Content is required'),
  author: z
    .string()
    .trim()
    .min(1, 'Author is required')
    .max(255, 'Author must be 255 characters or fewer'),
})

export type SubmitEntryFormValues = z.infer<typeof submitEntrySchema>

export const editEntrySchema = submitEntrySchema.extend({
  status: z.string().min(1, 'Status is required'),
})

export type EditEntryFormValues = z.infer<typeof editEntrySchema>
