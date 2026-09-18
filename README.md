# Football Project

> **Work in Progress** - This project is under active development.

## Overview

A Python project for collecting and analyzing football match data from the Premier League. Currently focused on exploratory data analysis (EDA), with future goals of building predictive models for:

- Match outcome prediction
- Player transfer value estimation

## Features

- Fetches match data from the football-data.org API
- Caches API responses
- Stores normalized match and team data in SQLite
- Historical data collection (multiple seasons)

## Installation

1. Clone the repository
2. Create a virtual environment
3. Install dependencies:
   ```bash
   pip install requests
   ```

## Project Structure

```
football_project/
├── football_cache.py   # Main module: API fetching, caching, database operations
├── test_api.py         # Demo script for data collection
└── venv/               # Python virtual environment
```
