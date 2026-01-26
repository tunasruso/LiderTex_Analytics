# LiderTex Analytics Dashboard

A real-time sales analytics dashboard for LiderTex CRM data.

## Features
- **Real-time Sales Tracking**: Fetches sales data from MySQL CRM database.
- **Dynamic Comparison**: Compares current sales vs yesterday (same hour).
- **Excel-like Interface**: Visual style matches corporate reporting standards.
- **Discrepancy Debugging**: Tools to analyze differences between report and database (`debug_volga.py`, `debug_transactions.py`).

## Setup

1. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configuration**:
   Copy the example config and add your database credentials:
   ```bash
   cp config.example.py config.py
   ```
   Edit `config.py` with your MySQL host, user, and password.

3. **Run Server**:
   ```bash
   python3 app.py
   ```
   Access at: `http://127.0.0.1:8000`

## Debug Tools
- `debug_volga.py`: Detailed manager-level breakdown for Volga region.
- `debug_transactions.py`: Inspect specific transactions causing discrepancies.
