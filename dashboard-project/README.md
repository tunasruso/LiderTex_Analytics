# Sales Dashboard Project

This is a web dashboard application designed to visualize sales data from a PostgreSQL database. It is pre-configured for deployment on Vercel using a Python FastAPI backend and a vanilla JS frontend.

## Project Structure

- **`api/`**: Contains the Python Backend (FastAPI).
    - `main.py`: Entry point for the API.
    - `database.py`: Database connection logic (SQLAlchemy).
    - `models.py`: Database models.
- **`public/`**: Contains the Frontend static assets (HTML/CSS/JS).
- **`vercel.json`**: Configuration for Vercel deployment (Routes & Builds).

## Local Development

1. **Clone the repository** (if you haven't already).

2. **Setup Backend:**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file in the root `dashboard-project/` directory based on `.env.example`:
   ```ini
   DB_HOST=localhost
   DB_USER=postgres
   DB_PASSWORD=secret
   DB_NAME=sales_db
   ```

4. **Run the API:**
   From the root `dashboard-project/` directory:
   ```bash
   uvicorn api.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000/api/health`.

5. **Run the Frontend:**
   Simply open `public/index.html` in your browser. 
   *Note: For `fetch` to work correctly locally, you may need a simple HTTP server or configure CORS to allow `null` origin if opening file directly, or run:*
   ```bash
   cd public
   python3 -m http.server 3000
   ```
   Then open `http://localhost:3000`.

## Deployment to Vercel

1. **Push to GitHub.**
2. **Import Project** in Vercel.
3. **Environment Variables**: Add the `DB_*` variables in the Vercel Project Settings.
4. **Deploy**. Vercel will automatically detect `vercel.json` and build the Python API.

## Database Schema (Required)
Ensure your PostgreSQL database has the `sales` table:
```sql
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    date DATE,
    product VARCHAR(100),
    amount DECIMAL(10,2),
    region VARCHAR(50)
);
```
