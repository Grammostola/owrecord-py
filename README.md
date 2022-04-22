# owrecord-py
Is a Python 3 script to read any number of Onewire temperature and humidity sensors and save as a row in a postgresql table. This updated (April 2022) version is smaller in scope than the original and features less dependencies. 

Concurrent sensor readings? Pyownet's documentation says 
> All methods of a pyownet proxy object are blocking

and the sister script (nodejs 'Owrecord') which works with a callback based Onewire library does not appear to be any faster than this version with ~15m of rj12, two splitters and three circuit boards with two, two and one sensor and no additional power; at best responses from all sensors takes ~2,7s with both scripts, sometimes they both take several seconds longer. (I briefly tested an async aiohttp version that attempted to read the sensors concurrently via the owhttpd webpage, the owhttp service consistently crashed. The owserver is who to talk to for errands like these and it'll answer as quickly as it deems appropriate I guess :) )
 
## Getting Started

### Prerequisites
An *ow-server* (https://www.owfs.org/)  needs be accessible for sensor values to read.


A *PostgreSQL*(13 tested) database table of a similar format is needed to save values:

```sql
create table ow_2022(
    reading_nr bigint generated always as identity primary key,
    timestamp timestamptz,
    southside_rel_humidity numeric(3,0),
    southside_temperature numeric(3,1),
    greenhouse_rel_humidity numeric(3,0),
    greenhouse_temperature numeric(3,1),
    balcony_rel_humidity numeric(3,0),
    balcony_temperature numeric(3,1));
```
The primary key column can be anything suitable (which doesn't ideally include the timestamp column) and the _temperature and _humidity columns need to match sensor designations (and probably function), see below. 

*Python 3.9+* is required for the zoneinfo module (built-in support for timezones)

### Installing
After cloning this repository, init a venv (suggestion) and install dependencies:
```shell
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```
Edit **config.ini** with your environment information 

The script can be tested for ability to read the Onewire network by editing owrecorder like so:
```python
owrecord = Owrecorder()
print(owrecord.read_owsensors())
```
which should print the readings that are meant to go into the database.

To run the script as it comes in order to read sensors and insert a row in the designated db:
```
python owrecorder.py
```
There's no notification on a successful run.


## Deployment
The script makes the most sense running on a schedule in order to save Onewire sensor readings over time.


## Code style
Black ✨ 🍰 ✨

## Contributing
Do create an issue for a feature request, bug report, comment or preceding a PR.

## License
See [LICENSE](LICENSE)

