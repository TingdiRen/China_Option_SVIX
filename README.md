# China Market SVIX Calculator

This project provides a Python-based toolkit to calculate the SVIX (Synthetic Volatility Index) for major Chinese market ETFs, based on the methodology outlined in the academic paper **"WHAT IS THE EXPECTED RETURN ON THE MARKET?"** by Ian Martin.

The tool automates the process by first fetching real-time option chain data from East Money (东方财富网) and then applying the SVIX calculation formula to the collected data.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

- [Theoretical Background](#theoretical-background)
- [Features](#features)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [How It Works](#how-it-works)
  - [Data Acquisition (`get_data.py`)](#data-acquisition-get_datapy)
  - [SVIX Calculation (`cal_SVIX.py`)](#svix-calculation-cal_svixpy)
- [Acknowledgments](#acknowledgments)

## Theoretical Background

The **SVIX** is a volatility index proposed by Ian Martin. Unlike the CBOE's VIX, which measures the market's expectation of volatility under a "risk-neutral" measure, the SVIX aims to measure the expected market variance under the "physical" or "real-world" measure.

It is derived from a cross-section of option prices and is theoretically simpler to calculate than the VIX. The formula essentially involves a weighted sum of out-of-the-money (OTM) option prices. This project implements a simplified version of this calculation using publicly available option data.

## Features

- **Automated Data Fetching**: Scrapes real-time option chain data for major Chinese ETFs (e.g., 50ETF, 300ETF) from East Money.
- **SVIX Calculation**: Implements the core SVIX formula for each available expiration date.
- **Data Persistence**: Saves the raw fetched data into `.csv` files for further analysis or reuse.

## Project Structure
```
.
├── data/                 # Directory to store the fetched CSV data (created automatically)
│   ├── etf_510050_data.csv
│   ├── etf_510300_data.csv
│   └── ...
├── get_data.py           # Script to fetch option data from East Money
├── cal_SVIX.py           # Script to calculate SVIX from the fetched data
└── README.md             # This file
```

## Usage

#### Step 1: Fetch the Option Data

Run the data acquisition script. This will connect to the East Money API, download the option data for the pre-configured ETFs, and save them as `.csv` files inside the `data/` directory.

```bash
python get_data.py
```

#### Step 2: Calculate the SVIX

Once the data is downloaded, run the calculation script. It will automatically find the `.csv` files in the `data/` directory, process them, and print the calculated SVIX term structure to the console.

```bash
python cal_SVIX.py
```

The output will be a formatted table for each ETF:

```
--- SVIX 计算结果 ---
基于假设：计算日 = 2025-08-04, 无风险利率 = 2.00%

到期日             SVIX (%)        远期价格 (F)       
-----------------------------------------------
2025-08-27      15.70           4.2789         
2025-09-24      16.45           4.2718         
2025-12-24      16.35           4.2577         
2026-03-25      14.07           4.2464         
-----------------------------------------------
```


## How It Works

### Data Acquisition (`get_data.py`)

- Connects to East Money's public JSONP API endpoint for option chains.
- Iteratively requests data page by page for each target ETF until the API returns no more data.
- Parses the JSONP response, extracts relevant fields (price, strike, expiry, etc.), and maps them to readable column names.
- Saves the cleaned data into a pandas DataFrame and exports it to a `.csv` file in the `data/` directory.

### SVIX Calculation (`cal_SVIX.py`)

The script processes each `.csv` file and, for each expiration date, performs the following steps:

1.  **Data Preprocessing**: Loads the data, converts columns to the correct numeric/datetime formats, and calculates the time to expiration (`T`) in years.
2.  **Calculate Forward Price (F)**: Determines the forward price of the underlying ETF using put-call parity. It identifies the strike price `K*` where the absolute difference between the call and put price is minimal and applies the formula: `F = K* + e^(rT) * (C - P)`.
3.  **Select OTM Options**: Filters for out-of-the-money (OTM) options based on the calculated forward price `F`.
    - Puts with strike `< F`
    - Calls with strike `>= F`
4.  **Calculate Strike Intervals (ΔK)**: Computes the interval `ΔK` around each strike price, which is needed for the integral approximation. It uses the average of the distances to the adjacent strikes.
5.  **Approximate the Integral**: Calculates the core component of the SVIX formula by summing the product of OTM option prices and their corresponding `ΔK`.
6.  **Compute Final SVIX**: Plugs all the components into the SVIX² formula and takes the square root, scaling the result by 100 to present it as a percentage.
    `SVIX² = (2 / T) * (1/R_f) * (integral_sum / S²)`


## Acknowledgments

-   **Ian Martin** for the foundational research in his paper "WHAT IS THE EXPECTED RETURN ON THE MARKET?".
-   **East Money (东方财富网)** for providing the public data API that makes this project possible.
