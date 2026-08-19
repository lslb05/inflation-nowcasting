# Decisões

Registre somente decisões que alterem custo de mudança futuro.

## Modelo

### AAAA-MM-DD — Título

- **Contexto:** qual restrição ou problema exigiu decisão.
- **Decisão:** o caminho escolhido.
- **Alternativas:** opções relevantes descartadas.
- **Consequências:** ganhos, custos e gatilho para revisar.

### 2026-08-18 — Manter `CLAUDE.md` e `AGENTS.md` no repositório público

- **Contexto:** os dois arquivos declaram que o repositório é construído com
  apoio de agentes. A alternativa era ignorá-los no git para que o repositório
  público não revelasse o fluxo de trabalho.
- **Decisão:** manter os dois versionados e públicos.
- **Alternativas:** ignorar `AGENTS.md` no `.gitignore`; mantê-lo apenas local.
  Ambas quebram a delegação ao Codex, que lê esse arquivo do repositório — o
  custo é funcional e imediato, o ganho é cosmético.
- **Consequências:** o repositório declara o método em vez de escondê-lo, o que
  também é verificável por quem lê. Rever se algum destino exigir o contrário.

### 2026-08-19 — Corte de cada mês vem da própria `data_publicacao` do CPI

- **Contexto:** simular "hoje" para cada mês do backtest exige saber quando o
  CPI daquele mês foi divulgado. A alternativa óbvia é assumir um calendário
  (ex.: "sempre dia 12 do mês seguinte"), mas a divulgação real do BLS varia
  de data mês a mês.
- **Decisão:** o corte de cada mês é `data_publicacao` da primeira safra do
  CPI daquele mês no vintage (ALFRED), menos um dia. Vem do próprio dado.
- **Alternativas:** calendário fixo hardcoded — mais simples de escrever,
  mas silenciosamente errado em qualquer mês que a divulgação atrase, e não
  detectável sem comparar contra o calendário real do BLS à parte.
- **Consequências:** o corte de cada mês está sempre certo enquanto o
  vintage do CPI estiver correto — sem manutenção de calendário. Custo: um
  mês sem CPI ainda ingerido não entra no backtest (é descartado, não
  aproximado), o que é o comportamento certo, não uma limitação a esconder.

### 2026-08-19 — `numpy.linalg.lstsq` em vez de `statsmodels`

- **Contexto:** o bridge model precisa de uma regressão linear multivariada
  (intercepto + 3 regressores). `statsmodels` é o padrão de mercado para
  regressão em Python, mas traz diagnóstico estatístico (p-valor, R²,
  resíduo) que este corte não usa — só o coeficiente ajustado, pra prever.
- **Decisão:** `numpy.linalg.lstsq` sobre a matriz de desenho com coluna de
  intercepto — mínimos quadrados puro, sem a camada de inferência estatística.
- **Alternativas:** `statsmodels.OLS` — mais completo, mas dependência nova
  pesada pra um projeto que não relata p-valor nem faz teste de hipótese
  sobre os coeficientes neste corte.
- **Consequências:** menos dependência; custo é que se um corte futuro
  precisar de diagnóstico de significância dos regressores (ex.: para
  justificar descartar um deles), a migração para `statsmodels` é o gatilho
  certo — não vale adicionar agora por especulação.
