import React, { useState } from 'react';

interface CodeExecutionCardProps {
  codeSnippet: string;
  status?: 'running' | 'success' | 'failed';
  durationMs?: number;
}

export const CodeExecutionCard: React.FC<CodeExecutionCardProps> = ({
  codeSnippet,
  status = 'success',
  durationMs,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const statusBadge = {
    running: { label: 'Executando script...', color: 'bg-amber-100 text-amber-800 border-amber-300' },
    success: { label: 'Código Sandbox Executado', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
    failed: { label: 'Erro na Execução', color: 'bg-rose-100 text-rose-800 border-rose-300' },
  }[status];

  return (
    <div className="my-2 rounded-lg border border-slate-700 bg-slate-900/90 text-slate-100 font-mono text-xs overflow-hidden shadow-md">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-3 py-2 bg-slate-800/80 cursor-pointer hover:bg-slate-800 transition"
      >
        <div className="flex items-center gap-2">
          <span className="text-amber-400">⚡ Code Mode</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${statusBadge.color}`}>
            {statusBadge.label}
          </span>
          {durationMs && <span className="text-slate-400 text-[10px]">({durationMs}ms)</span>}
        </div>
        <span className="text-slate-400 text-xs">{isOpen ? '▼ Ocultar' : '▶ Ver Código'}</span>
      </div>

      {isOpen && (
        <pre className="p-3 bg-slate-950 text-slate-200 overflow-x-auto leading-relaxed border-t border-slate-800">
          <code>{codeSnippet}</code>
        </pre>
      )}
    </div>
  );
};
