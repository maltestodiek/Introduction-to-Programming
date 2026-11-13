"""Live ROR v2 university search. No account details are sent to ROR."""
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

class UniversitySearchError(Exception):
    pass

def search_universities(query):
    query=" ".join(query.split())
    if not 2<=len(query)<=120:
        raise ValueError("Enter 2–120 characters to search for a university.")
    # Escape search syntax while allowing normal multi-word name searches.
    escaped=re.sub(r'([+\-=><!(){}\[\]^"~*?:\\/|&])',r'\\\1',query)
    url="https://api.ror.org/v2/organizations?"+urlencode(
        {"query":escaped,"filter":"types:education"})
    request=Request(url,headers={"User-Agent":"StudyDuel/0.1 (university profile search)","Accept":"application/json"})
    try:
        with urlopen(request,timeout=8) as response:
            payload=json.load(response)
        records=[]
        for item in payload.get("items",[]):
            if "education" not in item.get("types",[]) or item.get("status","active")!="active":
                continue
            names=item.get("names",[])
            preferred=next((n["value"] for n in names if "ror_display" in n.get("types",[])),None)
            if not preferred:continue
            countries=[loc.get("geonames_details",{}).get("country_name","") for loc in item.get("locations",[])]
            country=next((c for c in countries if c),"")
            identifier=item.get("id","")
            if not re.fullmatch(r"https://ror.org/[a-z0-9]+",identifier):continue
            label=f"{preferred} — {country}" if country else preferred
            records.append({"name":preferred,"country":country,"label":label,"id":identifier})
        return records
    except (URLError,TimeoutError,OSError,ValueError,KeyError,TypeError) as exc:
        raise UniversitySearchError("University search is unavailable right now. You can still type your university below.") from exc
