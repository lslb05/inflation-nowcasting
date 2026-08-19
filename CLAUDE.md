# Contrato do projeto — Nowcasting Inflacao

Leia o `CLAUDE.md` global e use este arquivo para o que é específico deste
repositório.

## Resultado do produto

- **Problema:** nowcasting de CPI é um problema clássico de bridge/mixed-
  frequency, mas fácil de fazer errado com vazamento de informação — usar
  revisão futura ou indicador publicado depois da data simulada de "hoje".
  Provar essa disciplina é o que diferencia isto de um notebook de brinquedo.
- **Usuário:** eu, e quem revisa o portfólio avaliando para pesquisa
  quantitativa.
- **Saída verificável:** para cada mês do período de teste, o nowcast do CPI
  m/m usando só dado com `data_publicacao <=` o corte simulado daquele mês,
  comparado ao valor publicado primeiro (não à revisão), com MAE contra um
  baseline ingênuo (repetir a variação do mês anterior).
- **Fonte de dados permitida:** FRED via Postgres do `dados-mercado-publico`
  (`series_vintage`) — `CPIAUCSL` (alvo), `T10YIE` (breakeven 10a, diário),
  `DCOILWTICO` (WTI, diário), `MICH` (expectativa Michigan, mensal). A data
  de corte de cada mês é a própria `data_publicacao` do CPI naquele vintage,
  não um calendário hardcoded.
- **Menor corte ponta a ponta:** CLI que roda o backtest point-in-time para
  um intervalo de meses e imprime uma tabela (mês, nowcast, publicado,
  baseline, erro nowcast, erro baseline).
- **Fora de escopo:** modelo state-space/Kalman multivariado, previsão de
  mais de 1 mês à frente, dashboard, mais de 3 indicadores auxiliares.

Não implemente enquanto um `PREENCHER` que altere o design continuar em aberto.

## Comandos

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Regras locais

- O pacote é `nowcasting_inflacao` e vive em `src/nowcasting_inflacao`.
- Notebook importa de `src/`; código de produção nunca importa notebook.
- Configuração vem de ambiente por `Settings`.
- Preserve dado bruto e metadados temporais quando houver ingestão.
- Atualize este arquivo quando uma decisão estrutural mudar.

## Estilo

Código público, lido por gente. A regra é contenção — a lista completa está em
`AGENTS.md`, seção "Style", e vale igual para mim e para o Codex.

- Comentário explica *por quê*, nunca *o quê*. Se parafraseia a linha abaixo,
  apague; se a linha precisa de paráfrase, renomeie a variável.
- Docstring só onde a assinatura não basta (unidade, fuso, efeito colateral,
  o que levanta). Helper privado de três linhas não leva.
- Teste afirma comportamento que pode quebrar, não constante. Cobertura é
  consequência de testar o que importa, nunca meta a inflar.
- Não capture exceção que não sabe tratar; não abstraia com um único chamador.

## Autoria dos commits

Autor e committer são um só: o dono do repositório. Nenhum `Co-Authored-By:`,
nenhum trailer de sessão, nenhuma menção a Claude, Codex ou ferramenta. Não
altere `user.name` nem `user.email`.

## Estado da sessão

- **Decidido:** primeiro corte entregue — backtest walk-forward point-in-time
  do CPI m/m (OLS via `numpy.linalg.lstsq`, 3 regressores) contra baseline
  ingênuo, lendo `series_vintage` do `dados-mercado-publico`. O corte de cada
  mês vem da `data_publicacao` real do CPI, não de calendário assumido.
- **Pendente:** nunca rodou contra dado real do FRED — falta chave de API
  pra ingerir `CPIAUCSL`/`T10YIE`/`DCOILWTICO`/`MICH` no projeto vizinho.
  Toda a disciplina point-in-time está validada com dado sintético.
- **Próximo passo:** com a chave do FRED, ingerir as quatro séries e rodar o
  backtest de verdade pra ver se o MAE do nowcast bate o baseline num
  período real — hoje isso é uma pergunta em aberto, não uma afirmação.

