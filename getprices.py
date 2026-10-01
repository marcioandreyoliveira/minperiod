#!/usr/bin/env python3

import sys
from datetime import datetime

import yfinance as yf
import pandas as pd


def main():
    # Validação dos argumentos
    if len(sys.argv) != 4:
        print("Uso: python pricepermin.py <ticker> <intervalo_min> <periodo_dias>")
        print("Exemplo: python pricepermin.py CMIG4 1 60")
        sys.exit(1)

    ticker_input  = sys.argv[1].upper()
    intervalo_min = int(sys.argv[2])
    periodo_dias  = int(sys.argv[3])

    # Monta o ticker no padrão do Yahoo Finance
    ticker_yf = f"{ticker_input}.SA"

    # Strings aceitas pelo yfinance
    interval_str = f"{intervalo_min}m"   # 1m, 5m, 15m, 30m...
    period_str   = f"{periodo_dias}d"    # 7d, 60d, ...

    # Download
    ###dados = yf.download(ticker_yf, period=period_str, interval=interval_str)
    dados = yf.Ticker(ticker_yf).history(period=period_str, interval=interval_str)

    if dados.empty:
        print(f"Nenhum dado retornado para {ticker_yf} "
              f"(intervalo={interval_str}, período={period_str}).")
        sys.exit(1)

    # Achata colunas MultiIndex, se necessário
    if isinstance(dados.columns, pd.MultiIndex):
        dados.columns = dados.columns.get_level_values(0)

    # Traz o índice (Datetime) para coluna
    dados = dados.reset_index()

    # Extrai tudo antes de dropar o Datetime
    dados["Data"] = dados["Datetime"].dt.strftime("%Y-%m-%d")
    dados["Hora"] = dados["Datetime"].dt.strftime("%H:%M:%S")
    dados["Fuso"] = (
        dados["Datetime"].dt.strftime("%z")
        .str.replace(r"([+-]\d{2})(\d{2})", r"\1:\2", regex=True)
    )

    # Remove a coluna original e reordena
    dados = dados.drop(columns=["Datetime"])
    dados = dados[["Data", "Hora", "Fuso",
                   "Open", "High", "Low", "Close", "Volume"]]

    # Nome do arquivo: <ticker>_<intervalo>m_<yyyy-mm-dd_HHMM>.csv
    agora = datetime.now().strftime("%Y-%m-%d_%H%M")
    nome_arquivo = f"{ticker_input}_{intervalo_min}m_{agora}.csv"

    # Salva com ; como separador e vírgula como decimal
    dados.to_csv(
        nome_arquivo,
        index=False,
        sep=";",
        decimal=",",
        encoding="utf-8-sig"
    )

    print(f"Salvo: {nome_arquivo} ({len(dados)} linhas)")
    print(dados.head())


if __name__ == "__main__":
    main()
