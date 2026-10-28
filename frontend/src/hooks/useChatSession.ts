import { useState, useCallback, useRef } from 'react';
import { MessageItem, ChatStreamEvent } from '../types/chat.types';
import { sendChatMessageStream } from '../lib/api/chat.api';

export function useChatSession(threadId: string = 'web-session-default') {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string, enableCodeMode: boolean = true) => {
      if (!content.trim() || isLoading) return;

      const userMsg: MessageItem = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: new Date().toLocaleTimeString(),
      };

      const assistantMsgId = crypto.randomUUID();
      const assistantMsg: MessageItem = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toLocaleTimeString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);
      setCurrentStage('Iniciando...');

      abortControllerRef.current = new AbortController();

      try {
        await sendChatMessageStream(
          { message: content, thread_id: threadId, enable_code_mode: enableCodeMode },
          (event: ChatStreamEvent) => {
            if (event.type === 'status') {
              setCurrentStage(event.message);
            } else if (event.type === 'code_generated') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, codeSnippet: event.code, codeStatus: 'running' }
                    : m
                )
              );
            } else if (event.type === 'code_execution') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, codeStatus: event.status === 'success' ? 'success' : 'running' }
                    : m
                )
              );
            } else if (event.type === 'final_result') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: event.text,
                        images: event.images,
                        sources: event.sources,
                        durationMs: event.duration_ms,
                        codeStatus: 'success',
                      }
                    : m
                )
              );
              setCurrentStage(null);
            } else if (event.type === 'error') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, content: `Erro: ${event.message}`, codeStatus: 'failed' }
                    : m
                )
              );
              setCurrentStage(null);
            }
          },
          abortControllerRef.current.signal
        );
      } catch (err: unknown) {
        const error = err as Error;
        if (error.name !== 'AbortError') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: 'Falha na conexão com o assistente.', codeStatus: 'failed' }
                : m
            )
          );
        }
      } finally {
        setIsLoading(false);
        setCurrentStage(null);
      }
    },
    [isLoading, threadId]
  );

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      setCurrentStage(null);
    }
  }, []);

  return {
    messages,
    isLoading,
    currentStage,
    sendMessage,
    stopGeneration,
  };
}
