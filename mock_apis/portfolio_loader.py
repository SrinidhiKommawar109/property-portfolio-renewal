import json
import os

PORTFOLIO_DIR = "data/portfolios"
RESULTS_DIR = "results"
PORTFOLIO_INDEX = {
    "PF-MIDWEST-001": "midwest_office.json",
    "PF-SOUTHEAST-001": "southeast_retail.json",
    "PF-NORTHEAST-001": "northeast_mixed.json",
}

def load_portfolio(portfolio_id_or_path: str) -> dict:
    """
    Load portfolio by ID (from PORTFOLIO_INDEX) OR by file path.
    Return error dict if not found.
    """
    if portfolio_id_or_path in PORTFOLIO_INDEX:
        file_path = os.path.join(PORTFOLIO_DIR, PORTFOLIO_INDEX[portfolio_id_or_path])
    else:
        file_path = portfolio_id_or_path

    if not os.path.exists(file_path):
        return {"error": f"Portfolio file not found: {file_path}"}

    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Error loading portfolio: {str(e)}"}

def list_portfolios() -> list:
    """Return list of available portfolios with id, name, property_count, renewal_date."""
    portfolios = []
    for pid, filename in PORTFOLIO_INDEX.items():
        data = load_portfolio(pid)
        if "error" not in data:
            portfolios.append({
                "id": pid,
                "name": data.get("portfolio_name"),
                "property_count": len(data.get("properties", [])),
                "renewal_date": data.get("renewal_date")
            })
    return portfolios

def save_results(portfolio_id: str, results: dict):
    """Save batch processing results to results/{portfolio_id}.json."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    file_path = os.path.join(RESULTS_DIR, f"{portfolio_id}.json")
    with open(file_path, 'w') as f:
        json.dump(results, f, indent=2)

def load_results(portfolio_id: str) -> dict or None:
    """Load previously saved results for a portfolio."""
    file_path = os.path.join(RESULTS_DIR, f"{portfolio_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return None
