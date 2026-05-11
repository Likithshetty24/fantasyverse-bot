"""
theme_picker.py
Picks the day's story mode and setting for Raat Ki Kahaniyan.
Rotates daily so we get a varied content mix:
  - Pure fiction (twist endings)
  - True-incident framing
  - Folklore (chudail, daayan, bhoot)
"""

import random
from datetime import datetime

MODES = ['fiction', 'true_incident', 'folklore']

SETTINGS = {
    'fiction': [
        'purana ghar (old abandoned house)',
        'sunsaan sadak raat ko (lonely road at night)',
        'lift mein akele (alone in elevator)',
        'hospital ki khaali ward (empty hospital ward)',
        'school ki chhutti ke baad (school after hours)',
        'office mein late night shift',
        'hotel ka kamra 302 (hotel room 302)',
        'metro ki aakhri train (last metro train)',
        'paharon mein homestay (homestay in mountains)',
        'taxi raat ko (taxi at night)',
    ],
    'true_incident': [
        'Mumbai ki ek chawl mein (in a Mumbai chawl)',
        'Delhi ke ek PG mein (in a Delhi PG accommodation)',
        'Banaras ke ghaat par (at Banaras ghat)',
        'Rajasthan ke ek haveli mein (in a Rajasthan haveli)',
        'Kolkata ki ek purani building (old Kolkata building)',
        'Bangalore ke ek flat mein (in a Bangalore flat)',
        'Pune ke hostel mein (in a Pune hostel)',
        'Shimla ke ek resort mein (in a Shimla resort)',
        'Goa ke beach par raat ko (at Goa beach at night)',
        'gaon ke kuein ke paas (near a village well)',
    ],
    'folklore': [
        'chudail jo peepal par rehti hai (witch who lives on peepal tree)',
        'daayan jo bachchon ko bulati hai (daayan who calls children)',
        'churail with backward feet',
        'bhoot of unmarried girl in white saree',
        'pishach in cremation ground',
        'shaitan jo mirror se baat karta hai',
        'banshee-like scream of mohini',
        'aatma of someone who died in well',
        'naagin who takes revenge after 100 years',
        'baba whose grave should never be opened',
    ],
}


def pick_theme():
    """Pick today's mode and setting deterministically based on date."""
    today = datetime.now()
    # Rotate mode by day-of-year so consecutive days are varied
    mode = MODES[today.timetuple().tm_yday % len(MODES)]

    # Use date as seed so setting is consistent within a day but varies day to day
    rng = random.Random(today.strftime('%Y%m%d'))
    setting = rng.choice(SETTINGS[mode])

    print(f"[theme_picker] Mode: {mode}")
    print(f"[theme_picker] Setting: {setting}")

    return {'mode': mode, 'setting': setting}
