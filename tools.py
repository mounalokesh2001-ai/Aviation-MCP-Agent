import requests
import pandas as pd

# Tool 1: Live flight data
def get_live_flights():
    url = "https://opensky-network.org/api/states/all"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        flights = []
        for state in data.get("states", [])[:100]:  # Increased from 10 to 100
            flights.append({
                "icao24": state[0],
                "callsign": state[1],
                "country": state[2],
                "altitude": state[7],
                "velocity": state[9]
            })
        return {"flights": flights}

    except Exception as e:
        return {"error": str(e)}


# Tool 2: Filter by country
def filter_flights_by_country(country: str):
    data = get_live_flights()
    if "flights" not in data:
        return data

    result = [
        f for f in data["flights"]
        if f["country"] and country.lower() in f["country"].lower()
    ]

    return {"filtered_flights": result}



# tool 3
def get_aviation_incidents():
    try:
        df = pd.read_csv("aviation_data.csv")
        return {"incidents": df.to_dict(orient="records")}
    except Exception as e:
        return {"error": str(e)}