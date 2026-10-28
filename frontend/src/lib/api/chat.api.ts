import { ChatMessageInput } from '../../schemas/chat.schema';
import { ChatStreamEvent } from '../../types/chat.types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function sendChatMessageStream(
  input: ChatMessageInput,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(input),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Falha na requisição: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('ReadableStream não suportado na resposta.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(':')) continue;

      if (trimmed.startsWith('data:')) {
        const jsonStr = trimmed.slice(5).trim();
        try {
          const parsed = JSON.parse(jsonStr) as ChatStreamEvent;
          onEvent(parsed);
        } catch {
          // Linha parcial ou não JSON ignorada
        }
      }
    }
  }
}
