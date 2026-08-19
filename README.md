# nowcasting-inflacao

Backtest point-in-time de nowcasting do CPI americano (m/m), usando só o que
era publicamente conhecido em cada data simulada — nunca uma revisão futura.

## O problema

Todo backtest de nowcasting tem o mesmo jeito de mentir: usar, sem perceber,
um dado que só foi publicado depois da data que o backtest finge estar
simulando. Um regressor "atualizado" ou uma revisão do próprio CPI que
vazam para dentro de um mês passado inflam a precisão aparente do modelo —
e é exatamente o erro que separa um resultado de portfólio de um resultado
que sobreviveria em produção. Este repositório fixa a disciplina point-in-time
como a peça central, não como detalhe de rodapé.

## Resultado

```console
$ uv run python -m nowcasting_inflacao backtest --de 2018-01 --ate 2018-12
mes,nowcast,realizado,baseline
2018-01,0.00154,0.00239,0.00234
2018-02,0.00151,-0.00036,0.00239
2018-03,0.00135,-0.00058,-0.00036
2018-04,0.00137,-0.00003,-0.00058
2018-05,0.00148,0.00447,-0.00003
2018-06,0.00119,0.00481,0.00447
2018-07,0.00142,0.00120,0.00481
2018-08,0.00136,0.00269,0.00120
2018-09,0.00160,0.00398,0.00269
2018-10,0.00134,0.00081,0.00398
2018-11,0.00150,-0.00083,0.00081
2018-12,0.00144,0.00307,-0.00083
# MAE nowcast=0.00175 baseline=0.00196
```

`realizado` é o valor que o mercado viu no dia da divulgação (não uma
revisão posterior); `baseline` repete a variação m/m do mês anterior. Esta
transcrição **é real, mas é de dado sintético** (CPI e regressores gerados
por passeio aleatório, 108 meses) rodado contra um Postgres efêmero — não
contra o FRED de verdade, porque a ingestão ao vivo exige uma chave de API
que este ambiente não tem (ver Limitações).

## Problema e escopo

- **Usuário:** eu, e quem revisa o portfólio avaliando para pesquisa
  quantitativa.
- **Decisão:** dá pra medir se um bridge model simples bate um baseline
  ingênuo para o CPI m/m, sem o resultado estar inflado por vazamento.
- **Entrada:** FRED via Postgres do
  [`dados-mercado-publico`](../dados-mercado-publico) —
  `CPIAUCSL` (alvo), `T10YIE`, `DCOILWTICO`, `MICH` (regressores), pela
  interface pública `series_vintage` e a mesma variável
  `DADOS_MERCADO_PUBLICO_POSTGRES_DSN` que o `vol-implicita-spx` já usa.
- **Fora de escopo:** modelo state-space/Kalman multivariado, previsão de
  mais de 1 mês à frente, dashboard, mais de 3 regressores.

## Arquitetura

```
Postgres (dados-mercado-publico, series_vintage)
    │
    ▼
pontual.py        toda leitura filtra por data_publicacao <= corte
    │
    ├─► regressores.py   T10YIE, DCOILWTICO, MICH → vetor de features
    │
    └─► backtest.py       walk-forward: treina OLS só com meses anteriores,
                           prevê o mês corrente, compara a baseline ingênua
                           │
                           ▼
                        cli.py   CSV + MAE
```

Três decisões que valem explicação:

**O corte de cada mês vem do próprio dado, não de um calendário assumido.**
`_corte_de_publicacao` usa a `data_publicacao` real daquele vintage do CPI,
menos um dia — não uma regra tipo "dia 12 do mês seguinte" hardcoded, que
quebraria silenciosamente em qualquer mês que a divulgação atrasasse.

**Toda consulta de regressor e de CPI passa por `pontual.py`.** É esse módulo
—três funções, `data_publicacao <= corte` na cláusula `WHERE`— que impede
vazamento, não uma revisão de código em cada lugar que consome dado. O teste
mais importante do projeto (`test_dado_publicado_depois_do_corte_nao_muda_o_nowcast_do_passado`)
prova isso inserindo um valor "do futuro" depois de já ter calculado o
nowcast, e checando que o resultado não muda.

**OLS com `numpy.linalg.lstsq`, não `statsmodels`.** O corte não precisa de
p-valor nem diagnóstico de resíduo — só do coeficiente pra prever. Trazer
`statsmodels` como dependência só por isso não pagava o custo.

## Executar localmente

Requisitos: Python 3.12, `uv`, Docker (para o Postgres efêmero dos testes),
e o [`dados-mercado-publico`](../dados-mercado-publico) rodando com as
quatro séries ingeridas:

```bash
# no dados-mercado-publico:
docker compose up -d
uv run python -m dados_mercado_publico ingerir --fonte fred --serie CPIAUCSL
uv run python -m dados_mercado_publico ingerir --fonte fred --serie T10YIE
uv run python -m dados_mercado_publico ingerir --fonte fred --serie DCOILWTICO
uv run python -m dados_mercado_publico ingerir --fonte fred --serie MICH
```

```bash
uv sync
cp .env.example .env
uv run python -m nowcasting_inflacao backtest --de 2015-01 --ate 2020-12
```

Sem as quatro séries ingeridas (ou sem meses suficientes de histórico antes
de `--de` para o `--treino-minimo`, padrão 36), o comando orienta e sai com
código 2 em vez de inventar resultado.

## Qualidade

```bash
uv run python scripts/check.py
```

O check executa formatação, lint, tipos e testes com cobertura. É o mesmo
comando que o CI roda, em Windows, Linux e macOS.

## Estrutura

```text
src/nowcasting_inflacao/
    pontual.py       leitura point-in-time — a peça que impede vazamento
    regressores.py    vetor de features a partir dos regressores
    backtest.py       walk-forward: treino, previsão, baseline, MAE
    cli.py             coordenação
```

## Limitações

- **Não validado contra dado real do FRED.** A ingestão ao vivo exige uma
  chave de API gratuita do FRED que este ambiente de desenvolvimento não
  tem. Toda a lógica point-in-time é validada com dado sintético controlado
  (`tests/`) — o comportamento do Postgres real depende só do
  `dados-mercado-publico` já testado separadamente, mas o caminho ponta a
  ponta com CPI real nunca rodou aqui.
- Bridge equation simples (OLS, 3 regressores, sem seleção de variável nem
  regularização) — não é o estado da arte de nowcasting (dynamic factor
  model, MIDAS), é o piso correto antes de complicar.
- Previsão de 1 mês só; sem revisão do próprio nowcast à medida que mais
  dado do mês corrente chega.

## Licença

MIT. Dados de terceiros mantêm suas próprias licenças e termos de uso.
