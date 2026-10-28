import { z } from 'zod';

export const ChatMessageSchema = z.object({
  message: z.string().min(1, 'A pergunta não pode estar vazia').max(2000, 'Mensagem muito longa'),
  thread_id: z.string().default('web-session-default'),
  enable_code_mode: z.boolean().default(true),
});

export type ChatMessageInput = z.infer<typeof ChatMessageSchema>;
