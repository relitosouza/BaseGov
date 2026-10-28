---
name: BaseGov Public Administration Suite
colors:
  primary: "#0F2942"          # Deep Gov Navy - autoridade e clareza institucional
  primary-hover: "#1A3D60"
  secondary: "#10B981"        # Emerald Code - status de execução sandbox e sucesso
  tertiary: "#F59E0B"         # Warm Amber - destaque Code Mode
  neutral-bg: "#0B1320"       # Fundo escuro focado e sem distrações
  surface: "#141E30"          # Painel e cards
  surface-border: "#243247"   # Bordas sutis de separação
  text-primary: "#F8FAFC"     # Branco suave de alto contraste
  text-muted: "#94A3B8"       # Texto secundário e metadados
  error: "#EF4444"
typography:
  fontFamily: "Inter, system-ui, -apple-system, sans-serif"
  fontMono: "'Fira Code', 'JetBrains Mono', monospace"
  h1: { fontSize: "28px", fontWeight: 700, lineHeight: 1.2 }
  h2: { fontSize: "20px", fontWeight: 600, lineHeight: 1.3 }
  body-md: { fontSize: "14px", fontWeight: 400, lineHeight: 1.5 }
  code-sm: { fontSize: "12px", fontWeight: 500, lineHeight: 1.4 }
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
---

# BaseGov - Design System & Visual Specification

## Overview
Interface moderna para consulta aos manuais governamentais com execução interativa em **Code Mode**.
Transmite precisão técnica, confiança e clareza para o servidor público.

## Cores & Semântica
- **Primary (#0F2942 / #141E30):** Tom institucional governamental sóbrio e moderno.
- **Secondary / Code (#10B981):** Verde esmeralda sinalizando sucesso e dados verificados.
- **Amber (#F59E0B):** Indicador visual das chamadas e scripts gerados via Code Mode.
- **Proibição de Roxo/Purple:** Nenhuma interface genérica "AI slop" roxa. Tons primários baseados em Navy & Dark Slate.

## Regras de Interface
- **Transparência de Código:** O código Python executado pelo agente pode ser expandido por padrão ou inspecionado sob demanda.
- **Prevenção de sobrecarga:** Imagens de manuais são exibidas com thumbnails clicáveis e zoom modal.
