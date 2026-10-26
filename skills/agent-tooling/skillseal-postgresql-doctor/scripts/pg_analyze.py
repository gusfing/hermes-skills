#!/usr/bin/env python3
"""
pg_analyze.py — Analisador de EXPLAIN do PostgreSQL
Detecta red flags de performance em um plano de execução.
Faz parte da skill "postgresql-doctor".

Uso:
    python3 pg_analyze.py "<texto do EXPLAIN ANALYZE>"

Retorna um veredito com problemas detectados e ordem de correção.
"""
import re
import sys

# Red flags: (padrão regex, problema, severidade, correção)
RED_FLAGS = [
    (r"Seq Scan on (\w+) \(.*rows=(\d+).*actual", "Seq Scan",
     "Scan sequencial", "media"),
    (r"Seq Scan on (\w+)", "Seq Scan (tabela)",
     "Scan sequencial", "media"),
    (r"Nested Loop", "Nested Loop",
     "Possível JOIN sem índice (re-escaneia)", "alta"),
    (r"Hash Join", "Hash Join",
     "Hash grande pode indicar falta de índice no JOIN", "media"),
    (r"Sort\s", "Sort",
     "Ordenação em disco — falta índice que satisfaça ORDER BY", "alta"),
    (r"Materialize", "Materialize",
     "Materialização — pode ser caro em tabelas grandes", "baixa"),
    (r"temp file|Temp File|written to disk", "Temp file",
     "work_mem baixo — sorts/hashes caindo em disco", "alta"),
    (r"Buffers: shared hit=0", "Buffers frios",
     "Cache frio — shared_buffers pode estar baixo", "media"),
    (r"actual rows=(\d+).*actual time=(\d+\.?\d*)", "Custo alto",
     "Tempo de execução real elevado", "media"),
]

# Padrões de performance saudável (ausência de problema)
HEALTHY = [
    (r"Index Scan", "Index Scan"),
    (r"Index Only Scan", "Index Only Scan"),
    (r"Bitmap Index Scan", "Bitmap Index Scan"),
]

def analyze(plan_text):
    """Analisa um EXPLAIN e retorna (problemas, pontos_fortes)."""
    problems = []
    strengths = []
    for pattern, name, desc, sev in RED_FLAGS:
        if re.search(pattern, plan_text, re.IGNORECASE):
            problems.append({"nome": name, "desc": desc, "severidade": sev})
    for pattern, name in HEALTHY:
        if re.search(pattern, plan_text, re.IGNORECASE):
            strengths.append(name)
    return problems, strengths

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 pg_analyze.py '<texto do EXPLAIN>'")
        print("   ou: echo '<texto>' | python3 pg_analyze.py -")
        sys.exit(1)
    if sys.argv[1] == "-":
        plan_text = sys.stdin.read()
    else:
        plan_text = " ".join(sys.argv[1:])

    problems, strengths = analyze(plan_text)

    print("=" * 55)
    print("🔍 PostgreSQL Doctor — Análise de EXPLAIN")
    print("=" * 55)

    if not problems and not strengths:
        print("⚠️  Nenhum padrão reconhecido no plano.")
        print("   Dica: cole o texto completo do EXPLAIN (ANALYZE, BUFFERS).")
        return 2

    if problems:
        # ordenar por severidade
        sev_order = {"alta": 0, "media": 1, "baixa": 2}
        problems.sort(key=lambda p: sev_order.get(p["severidade"], 3))
        print("\n❌ PROBLEMAS DETECTADOS:")
        for p in problems:
            icon = {"alta": "🔴", "media": "🟠", "baixa": "🟡"}.get(p["severidade"], "⚪")
            print(f"  {icon} {p['nome']}: {p['desc']}")
    else:
        print("\n✅ Nenhuma red flag grave detectada.")

    if strengths:
        print("\n✅ PONTOS FORTES (uso de índices):")
        for s in strengths:
            print(f"  🟢 {s}")

    # VEREDITO
    alta = [p for p in problems if p["severidade"] == "alta"]
    if alta:
        print("\n" + "=" * 55)
        print("VEREDITO: 🔴 OTIMIZAÇÃO NECESSÁRIA")
        print("  Corrija primeiro (em ordem):")
        ordem = {"alta": "índices/JOIN", "media": "work_mem/estatísticas", "baixa": "refinar"}
        for i, p in enumerate(problems, 1):
            print(f"   {i}. {p['nome']} — {p['desc']}")
        print("=" * 55)
        return 0
    elif problems:
        print("\n" + "=" * 55)
        print("VEREDITO: 🟠 REVISAR")
        print("  Sem problema crítico, mas há pontos de atenção.")
        print("=" * 55)
        return 0
    else:
        print("\n" + "=" * 55)
        print("VEREDITO: 🟢 PLANO SAUDÁVEL")
        print("  Usa índices corretamente.")
        print("=" * 55)
        return 0

if __name__ == "__main__":
    sys.exit(main())
