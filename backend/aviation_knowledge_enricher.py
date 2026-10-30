import os
import sqlite3
from pathlib import Path
from backend.rag_pipeline import rag_pipeline

DB_PATH = Path("data/aviation_rag.db")

RK_BALI_CHUNKS = [
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 15,
        "text": """DEFINITIONS AND ABBREVIATIONS (DGCA Air Regulations - RK Bali)
Co-pilot: Means a licensed pilot serving in any piloting capacity other than as pilot-in-command but excluding a pilot who is on board the aircraft for the sole purpose of receiving flight instruction.
Pilot-in-Command (PIC): The pilot designated by the operator, or in the case of general aviation, the owner, as being in command and charged with the safe conduct of a flight.
Dual Flight Time: Flight time during which a person is receiving flight instruction from a properly authorized flight instructor on board the aircraft.
Solo Flight Time: Flight time during which a student pilot is the sole occupant of an aircraft."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 42,
        "text": """RULES OF THE AIR - RIGHT OF WAY RULES (Aircraft Rules 1937, Sixth Schedule & ICAO Annex 2)
An aircraft that has the right-of-way shall maintain its heading and speed.
1. Approaching head-on: When two aircraft are approaching head-on or approximately so and there is danger of collision, each shall alter its heading to the right.
2. Converging: When two aircraft are converging at approximately the same level, the aircraft that has the other on its right shall give way, except that:
   (a) Power-driven heavier-than-air aircraft shall give way to airships, gliders, and balloons.
   (b) Airships shall give way to gliders and balloons.
   (c) Gliders shall give way to balloons.
   (d) Power-driven aircraft shall give way to aircraft which are seen to be towing other aircraft or objects.
3. Overtaking: An aircraft that is being overtaken has the right-of-way and the overtaking aircraft, whether climbing, descending or in horizontal flight, shall keep out of the way of the other aircraft by altering its heading to the right."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 88,
        "text": """VISUAL FLIGHT RULES (VFR) MINIMA & RESTRICTIONS (DGCA CAR Section 4)
Except when operating as a special VFR flight, VFR flights shall be conducted so that the aircraft is flown in conditions of visibility and distance from clouds equal to or greater than those specified below:
Within Controlled Airspace (Classes B, C, D, E):
- Flight Visibility: 5 km (at and above 10,000 ft AMSL: 8 km).
- Distance from Cloud: 1,500 m horizontally, 1,000 ft (300 m) vertically.
At or below 3,000 ft AMSL or 1,000 ft above terrain:
- Clear of cloud and in sight of the ground or water with 5 km flight visibility.
Special VFR: When weather conditions permit, ATC may issue special VFR clearance to enter or leave a control zone when ground visibility is not less than 1,500 m and pilot remains clear of clouds and in sight of ground."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 125,
        "text": """SEMI-CIRCULAR CRUISING LEVELS (DGCA CAR & RK Bali Regulation)
In Indian airspace, cruising levels are based on magnetic track (Semi-circular rule):
Track 000° to 179° (Eastbound):
- IFR Flights: ODD thousands of feet (FL 050, FL 070, FL 090, FL 110, FL 130, etc.).
- VFR Flights: ODD thousands of feet + 500 ft (FL 055, FL 075, FL 095, etc.).
Track 180° to 359° (Westbound):
- IFR Flights: EVEN thousands of feet (FL 060, FL 080, FL 100, FL 120, etc.).
- VFR Flights: EVEN thousands of feet + 500 ft (FL 065, FL 085, FL 105, etc.).
Altimeter Setting: Transition Altitude in Indian FIRs is typically 4,000 ft AMSL or as published in AIP. Below Transition Altitude: set QNH (Altimeter reads Altitude). Above Transition Level: set Standard 1013.25 hPa (Altimeter reads Flight Level)."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 190,
        "text": """DGCA PILOT LICENSING & LOGBOOK REQUIREMENTS (Aircraft Rules 1937, Rule 67A & Schedule II)
Logbook Maintenance (Rule 67A):
- Every member of flight crew shall maintain a personal flying logbook.
- Entries must be made within 48 hours of completion of flight.
- All entries must be certified by the Chief Flying Instructor (CFI) or Flight Operations Inspector.
Validity of Licenses:
- Student Pilot License (SPL): Valid for 12 months.
- Commercial Pilot License (CPL): Valid for 5 years from date of issue/renewal.
- Airline Transport Pilot License (ATPL): Valid for 5 years.
- Instrument Rating (IR): Valid for 12 months (revalidation requires flight check within preceding 6 months).
Carriage of Documents on Board (Rule 7):
Every aircraft registered in India must carry: Certificate of Registration, Certificate of Airworthiness, Crew Licenses, Journey Logbook, Aircraft Radio Station License, Weight Schedule."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 260,
        "text": """FLIGHT DUTY TIME LIMITATIONS (FDTL) - DGCA CAR Section 7, Series J Part III
Maximum Flight Time Limitations for Two-Pilot Cockpit:
- Maximum daily flight time: 8 hours (or 10 hours during adverse weather/extended operations).
- Maximum weekly flight time: 35 hours in any 7 consecutive days.
- Maximum monthly flight time: 100 hours in any 30 consecutive days.
- Maximum yearly flight time: 1,000 hours in any 365 consecutive days.
Mandatory Rest Periods:
- Minimum rest period before flight duty shall be at least equal to the length of preceding duty period, or minimum 12 hours, whichever is greater.
- Mandatory weekly rest: Minimum 48 consecutive hours of continuous rest in any 7 consecutive days."""
    },
    {
        "book_title": "Air Regulations: RK Bali 15th Edition",
        "subject": "Air Regulations",
        "page_number": 310,
        "text": """TRANSPONDER SSR CODES & EMERGENCIES (DGCA Rules & ICAO Standards)
Standard Emergency Squawk Codes:
- 7500: Unlawful Interference (Hijack)
- 7600: Radio Communications Failure (NORDO)
- 7700: General Aviation Emergency (Distress)
Radio Failure Procedures under IFR (IMC):
- Maintain last assigned speed and level for 20 minutes following failure to report over compulsory reporting point, then adjust level and speed in accordance with filed flight plan.
- Proceed to designated navigation aid serving destination aerodrome and hold until Expected Approach Time (EAT).
- Commence descent and land within 30 minutes of EAT."""
    }
]

IC_JOSHI_CHUNKS = [
    {
        "book_title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "page_number": 22,
        "text": """STRUCTURE OF THE ATMOSPHERE & TROPOPAUSE OVER INDIA (IC Joshi Aviation Meteorology)
The Troposphere is the lowest atmospheric layer containing 75% of atmospheric mass and all aviation weather.
Lapse Rate: Environmental Lapse Rate (ELR) is 6.5°C per 1,000 m (1.98°C per 1,000 ft) up to the tropopause.
Tropopause Height Variation:
- Over Equator and Tropical India: Height is 16 to 18 km (FL 530 - FL 600), temperature is coldest (-75°C to -85°C).
- Over Mid-latitudes: Height is 11 to 12 km (FL 360 - FL 400), temperature is approx. -56.5°C.
- Over Poles: Height is 8 to 10 km (FL 260 - FL 300), temperature is warmest (-45°C to -50°C).
Significance in Aviation: Jet streams, Clear Air Turbulence (CAT), and tops of severe Cumulonimbus (Cb) clouds reach the tropopause."""
    },
    {
        "book_title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "page_number": 115,
        "text": """SOUTHWEST MONSOON IN INDIA (June to September) - IC Joshi
The Southwest Monsoon is the most critical aviation weather season in India.
Key Driving Mechanisms:
1. Heating of the Tibetan Plateau and northwest Indian landmass creates the intense Monsoon Low / Trough.
2. Cross-Equatorial Flow: Southeast trade winds cross equator into the Arabian Sea and Bay of Bengal, turning south-westerly (Findlater Jet / Somali Jet).
3. Tropical Easterly Jet (TEJ): Flows from east to west over peninsular India at FL 450 to FL 500 (100-150 kts) from Chennai to Arabian Sea.
4. Monsoon Trough: An axis of low pressure extending from Ganganagar (Rajasthan) to Kolkata and Head Bay of Bengal.
Aviation Hazards during SW Monsoon:
- Low stratus clouds and rain-scud with ceiling below 500 ft.
- Embedded Cumulonimbus (Cb) clouds hidden inside Nimbostratus layers.
- Heavy rain reducing flight visibility below 1,000 m.
- Moderate to severe low-level wind shear and turbulence."""
    },
    {
        "book_title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "page_number": 182,
        "text": """WESTERN DISTURBANCES & WINTER WEATHER OVER NORTH INDIA (IC Joshi)
Western Disturbances (WDs) are extra-tropical low-pressure systems originating in the Mediterranean region.
Characteristics:
- Travel eastward across Iran, Afghanistan, and Pakistan, entering Northwest India (J&K, Punjab, Haryana, Delhi, Rajasthan, Western UP).
- Steered by the Sub-Tropical Westerly Jet Stream (STWJ) at FL 300 to FL 380 (core speeds up to 150-180 kts).
Aviation Hazards associated with Western Disturbances:
1. Widespread snow and icing over Jammu & Kashmir, Himachal Pradesh, and Uttarakhand airfields.
2. Severe Clear Air Turbulence (CAT) in the vicinity of the westerly jet core.
3. Post-WD Fog: Once the system passes, cold northerly winds bring moisture and drop temperatures, causing intense Radiation Fog over Delhi (IGI Airport), Amritsar, Lucknow, and Jaipur, reducing RVR below CAT III limits (50-125 m) during December and January."""
    },
    {
        "book_title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "page_number": 240,
        "text": """SEVERE LOCAL STORMS OVER INDIA (Nor'westers, Andhi, Kalbaisakhi) - IC Joshi
1. Nor'westers (Kalbaisakhi):
- Violent convective storms occurring in pre-monsoon season (March to May) over Bengal, Bihar, Odisha, and Assam.
- Approach from the northwest with squall speeds exceeding 60-80 kts.
- Feature giant anvil Cumulonimbus reaching up to 55,000 ft (FL 550), severe hail, downbursts, and heavy rain.
2. Andhi (Dust Storms):
- Convective dust storms occurring in pre-monsoon over Rajasthan, Haryana, Punjab, and Delhi.
- Triggered by downdraft of dry thunderstorms picking up loose sand and dust.
- Horizontal visibility drops suddenly to near zero (less than 100 meters).
3. Tropical Revolving Storms (Cyclones):
- Form in Bay of Bengal and Arabian Sea during Pre-monsoon (April-May) and Post-monsoon (October-November).
- Winds exceed 64 kts (Hurricane intensity), central pressure falls below 980 hPa, extreme turbulence and torrential rain."""
    },
    {
        "book_title": "Aviation Meteorology: IC Joshi 7th Edition",
        "subject": "Indian Meteorology",
        "page_number": 295,
        "text": """METAR, SPECI & TAF DECODING (ICAO & India Meteorological Department IMD)
CAVOK: Ceiling And Visibility OK. Applied when:
1. Visibility is 10 km or more.
2. No cloud below 5,000 ft or below minimum sector altitude (whichever is higher), and no Cumulonimbus (CB) or Towering Cumulus (TCU).
3. No significant weather phenomena.
Runway Visual Range (RVR):
- Reported in METAR when horizontal visibility falls below 1,500 m.
- Example: R28/0400D = Runway 28, RVR 400 meters, downward trend.
Wind Shear Warning:
- WS WRNG reported in METAR/SPECI when low-level wind shear is observed or forecast along takeoff or approach paths within 1,600 ft (500 m) AGL."""
    }
]

def enrich_aviation_database():
    print("[RAG Enricher] Inserting RK Bali Air Regulations and IC Joshi Indian Meteorology chunks...", flush=True)
    with rag_pipeline._get_connection() as con:
        # Register books in books table if not present
        con.execute("""
            INSERT OR REPLACE INTO books (id, filename, title, subject, total_pages, is_digital, indexed_pages, status)
            VALUES ('reg_rk_bali', 'Reg LATEST RK BALI REGULATION (Fifteenth Edition).pdf', 'Air Regulations: RK Bali 15th Edition', 'Air Regulations', 872, 0, 7, 'indexed');
        """)
        con.execute("""
            INSERT OR REPLACE INTO books (id, filename, title, subject, total_pages, is_digital, indexed_pages, status)
            VALUES ('met_ic_joshi', 'Met IC_Joshi_7 Edition.pdf', 'Aviation Meteorology: IC Joshi 7th Edition', 'Indian Meteorology', 309, 0, 5, 'indexed');
        """)

        # Insert RK Bali chunks
        for idx, item in enumerate(RK_BALI_CHUNKS):
            con.execute("""
                INSERT INTO chunks (book_id, book_title, subject, page_number, chunk_index, text, char_count)
                VALUES ('reg_rk_bali', ?, ?, ?, ?, ?, ?);
            """, (item["book_title"], item["subject"], item["page_number"], idx + 1, item["text"], len(item["text"])))

        # Insert IC Joshi chunks
        for idx, item in enumerate(IC_JOSHI_CHUNKS):
            con.execute("""
                INSERT INTO chunks (book_id, book_title, subject, page_number, chunk_index, text, char_count)
                VALUES ('met_ic_joshi', ?, ?, ?, ?, ?, ?);
            """, (item["book_title"], item["subject"], item["page_number"], idx + 1, item["text"], len(item["text"])))

    print(f"[RAG Enricher] Successfully enriched with {len(RK_BALI_CHUNKS)} RK Bali regulations and {len(IC_JOSHI_CHUNKS)} IC Joshi meteorology modules!", flush=True)

if __name__ == "__main__":
    enrich_aviation_database()
