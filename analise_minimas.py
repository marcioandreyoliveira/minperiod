#!/usr/bin/env python3
"""
Analisa os CSVs gerados por pricepermin.py e calcula em quais
faixas de horário a mínima do dia ocorreu com mais frequência.
Salva o resultado em resultado_analise.json para consumo externo.
"""

import glob
import json
import sys
from pathlib import Path

import pandas as pd


COLUNAS_ESPERADAS = {"Data", "Hora", "Low"}
ARQUIVO_SAIDA = "resultado_analise.json"


def analisar_minimas(pasta=".", faixa_min=30, verbose=True):
    arquivos = sorted(glob.glob(f"{pasta}/*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {pasta}")

    frames = []
    usados = 0
    pulados = 0

    for arq in arquivos:
        try:
            df = pd.read_csv(arq, sep=";", decimal=",")
        except Exception as e:
            if verbose:
                print(f"Pulando {Path(arq).name}: erro ao ler ({e})")
            pulados += 1
            continue

        faltando = COLUNAS_ESPERADAS - set(df.columns)
        if faltando:
            if verbose:
                print(f"Pulando {Path(arq).name}: "
                      f"colunas faltando {sorted(faltando)}")
            pulados += 1
            continue

        df["Data"] = df["Data"].astype(str)
        df["Hora"] = df["Hora"].astype(str)
        df["Low"]  = pd.to_numeric(df["Low"], errors="coerce")
        df["Hora_td"] = pd.to_timedelta(df["Hora"], errors="coerce")
        df = df.dropna(subset=["Low", "Hora_td"])

        if df.empty:
            if verbose:
                print(f"Pulando {Path(arq).name}: sem linhas válidas")
            pulados += 1
            continue

        df = df[["Data", "Hora", "Hora_td", "Low"]].copy()
        df["_arquivo"] = Path(arq).name
        frames.append(df)
        usados += 1

    if not frames:
        raise RuntimeError(
            "Nenhum arquivo válido encontrado. "
            "Confira se os CSVs têm as colunas Data;Hora;...;Low;..."
        )

    tudo = pd.concat(frames, ignore_index=True)

    antes = len(tudo)
    tudo = (
        tudo.sort_values("Low")
            .drop_duplicates(subset=["Data", "Hora"], keep="first")
            .reset_index(drop=True)
    )
    removidas = antes - len(tudo)

    if verbose and removidas:
        print(f"Duplicatas (Data,Hora) removidas: {removidas}")

    registros = []
    for dia, grupo in tudo.groupby("Data"):
        idx = grupo["Low"].idxmin()
        linha = grupo.loc[idx]
        registros.append({
            "Data":     dia,
            "Hora_min": linha["Hora_td"],
            "Low_min":  linha["Low"],
        })

    res = pd.DataFrame(registros).sort_values("Data").reset_index(drop=True)

    def faixa(td, minutos):
        total = int(td.total_seconds() // 60)
        inicio = (total // minutos) * minutos
        fim = inicio + minutos
        return f"{inicio//60:02d}:{inicio%60:02d}-{fim//60:02d}:{fim%60:02d}"

    res["Faixa"] = res["Hora_min"].apply(lambda td: faixa(td, faixa_min))
    contagem = res["Faixa"].value_counts().sort_index()

    if verbose:
        total = len(res)
        print(f"\nAnálise de {total} dias "
              f"({usados} arquivos usados, {pulados} pulados)\n")
        print(f"{'Faixa':<15} {'Dias':>5} {'%':>7}")
        print("-" * 55)
        for f, c in contagem.items():
            pct = c / total * 100
            barra = "█" * int(pct / 2)
            print(f"{f:<15} {c:>5} {pct:>6.1f}%   {barra}")

        print(f"\nFaixa mais provável: {contagem.idxmax()} "
              f"({contagem.max()} dias, "
              f"{contagem.max()/total*100:.1f}%)")

    # --- Salva o resultado em JSON ---
    resultado = {
        "faixa_mais_provavel": str(contagem.idxmax()),
        "dias_na_faixa": int(contagem.max()),
        "total_dias": int(len(res)),
        "percentual": round(contagem.max() / len(res) * 100, 1),
        "data_analise": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "faixas": {str(k): int(v) for k, v in contagem.items()},
    }

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"\nResultado salvo em {ARQUIVO_SAIDA}")

    return res, contagem


if __name__ == "__main__":
    pasta = sys.argv[1] if len(sys.argv) > 1 else "."
    faixa = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    analisar_minimas(pasta, faixa)
