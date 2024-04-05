# This example shows how to identify a vessel's country and flag
from pyais.util import get_country


# The first 3 digits of any MMSI number are indicative of the vessel's flag
country_code, country_name = get_country(249110000)
assert country_code, country_name == ('MT', 'Malta')
