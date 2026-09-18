# Football Project

> **Work in Progress** - This project is under active development.

## Overview

A Python project for collecting and analyzing football (soccer) match data from the Premier League. Currently focused on exploratory data analysis (EDA), with future goals of building predictive models for:

- Match outcome prediction
- Player transfer value estimation

## Current Features

- Fetches match data from the football-data.org API
- Caches API responses to avoid rate limiting
- Stores normalized match and team data in SQLite
- Supports historical data collection (multiple seasons)
- Provides training data extraction utilities for ML

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install requests
   ```

## Project Structure

```
football_project/
├── football_cache.py   # Main module: API fetching, caching, database operations
├── test_api.py         # Demo script for data collection
├── football_data.db    # SQLite database (generated)
└── venv/               # Python virtual environment
```
