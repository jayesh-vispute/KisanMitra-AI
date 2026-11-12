import httpx
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.retry import with_retry

logger = logging.getLogger(__name__)


@with_retry(max_retries=3, base_delay=2, max_delay=15)
def fetch_nasa_weather_data(lat: float, lon: float, start_date: str, end_date: str):
    """
    Fetches daily meteorological data from NASA POWER API.
    Parameters:
    - T2M: Temperature at 2 Meters (C)
    - PRECTOTCORR: Precipitation Corrected (mm/day)
    - RH2M: Relative Humidity at 2 Meters (%)

    Dates should be in YYYYMMDD format.
    """
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M,PRECTOTCORR,RH2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }

    logger.info(
        f"Fetching NASA POWER data for lat={lat}, lon={lon} from {start_date} to {end_date}"
    )

    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # NASA POWER returns data in a specific nested format under properties.parameter
        # Example: data['properties']['parameter']['T2M']['YYYYMMDD'] = value
        properties = data.get("properties", {}).get("parameter", {})

        if not properties:
            logger.warning(
                f"No valid parameter data returned from NASA for {lat}, {lon}"
            )
            return []

        t2m_data = properties.get("T2M", {})
        prec_data = properties.get("PRECTOTCORR", {})
        rh2m_data = properties.get("RH2M", {})

        # Parse into a daily list
        daily_records = []
        for date_key in t2m_data.keys():
            t2m_val = t2m_data.get(date_key)
            prec_val = prec_data.get(date_key)
            rh2m_val = rh2m_data.get(date_key)

            # NASA uses -999 for missing values. We replace them with None
            t2m_val = None if t2m_val == -999 else t2m_val
            prec_val = None if prec_val == -999 else prec_val
            rh2m_val = None if rh2m_val == -999 else rh2m_val

            # format date_key from YYYYMMDD to YYYY-MM-DD
            formatted_date = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}"

            daily_records.append(
                {
                    "date": formatted_date,
                    "temperature": t2m_val,
                    "rainfall": prec_val,
                    "humidity": rh2m_val,
                    "latitude": lat,
                    "longitude": lon,
                    "source": "NASA_POWER",
                }
            )

        return daily_records
