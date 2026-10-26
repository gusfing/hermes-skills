---
name: skillseal-postgresql-doctor
description: "Diagnostica e otimiza consultas PostgreSQL: analisa EXPLAIN, detecta problemas de performance (sequential scans, joins ineficientes, índices ausentes) e sugere correções concretas. Especialista em query tuning."
version: 1.0.0
author: Workloop
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [postgresql, sql, performance, tuning, explain, database, index]
    category: database
---

# PostgreSQL Doctor — Otimização de Consultas

Skill especialista em **diagnosticar e otimizar consultas PostgreSQL**. Faz o agente agir como um DBA de performance: lê o plano de execução como um detetive, detecta gargalos e prescreve correções com fundamento técnico.

## Quando Usar

Use esta skill quando a tarefa envolver:
- **Analisar `EXPLAIN` / `EXPLAIN ANALYZE`** e interpretar o plano de execução
- **Detectar queries lentas** — sequential scans, joins N+1, índices ausentes
- **Reescrever consultas** para melhorar performance
- **Escolher o índice certo** (B-tree, GIN, GiST, BRIN, composto, parcial)
- **Configurar `work_mem`, `shared_buffers` e outros parâmetros de tuning**

## Diagnóstico Rápido — Red Flags no EXPLAIN

Ao ler um `EXPLAIN ANALYZE`, procure estes sinais (na ordem de impacto):

| Sinal no plano | Problema | Correção típica |
|---|---|---|
| `Seq Scan` em tabela grande (50k+ linhas) | Índice ausente | Criar índice no WHERE/JOIN |
| `Nested Loop` com re-escaneamento interno | JOIN mal indexado | Índice na coluna do JOIN |
| `Hash Join` + `Hash` grande | Falta índice, hash grande demais | Indexar, aumentar `work_mem` |
| `rows=1` mas `actual rows=N` | Estatísticas desatualizadas | `ANALYZE` / `VACUUM ANALYZE` |
| `Sort` sobre tabela grande | Falta ORDER BY indexado | Índice que satisfaz a ordenação |
| `Buffers: shared hit=0` | Cache frio | Aumentar `shared_buffers` |

## Checklist de Otimização (ordem de impacto)

1. **Estatísticas atualizadas?** → `ANALYZE;`
2. **Índice certo para o WHERE?** → B-tree igualdade/range; GIN arrays/full-text; GiST geo; BRIN séries grandes
3. **Índice cobre o SELECT?** → Índice composto evita voltar à tabela (index-only scan)
4. **JOIN está indexado?** → Índice na coluna FK do lado "many"
5. **Só o que precisa?** → `SELECT *` → colunas necessárias
6. **Subconsulta vira CTE ou JOIN?** → CTEs materializam
7. **`work_mem` suficiente?** → Sorts/hashes em disco indicam work_mem baixo
8. **Índice parcial?** → menor e mais rápido para subconjuntos

## Leitura de EXPLAIN — Método do Detetive

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ...;
```

Leia de **dentro para fora**:
1. Ache os **nós de scan** (Seq Scan, Index Scan)
2. Compare `rows` vs `actual rows` — divergência = stats ruins
3. Ache o **custo total** do nó raiz
4. Procure `Sort` / `Hash` / `Materialize` — caros, elimináveis com índice

## Comandos Úteis do Tester

```bash
python3 pg_analyze.py "EXPLAIN PLAN TEXT AQUI"
```

Retorna veredito com problemas detectados e ordem de correção.

*Conhecimento do ebook PostgreSQL Mastery (Workloop).*
