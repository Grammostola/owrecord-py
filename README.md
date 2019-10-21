# Ow-tenter
Is a Python 3 script to read any number of Onewire temperature and humidity sensors and save as a row in a postgresql table. Threshold values can be defined for email alerts and weather data can be fetched via openweathermap and saved as well.

## Getting Started

### Prerequisites
An ow-server(https://www.owfs.org/)  needs be accessible for sensor values to read.

An Openweathermap (https://openweathermap.org/api) API key is optional.

A PostgreSQL(9.6 tested) database table of this format is needed to save values:
```
create table ow_tenter_test(reading_nr serial PRIMARY KEY, timestamp timestamptz, Larger_tent_relative_humidity numeric(3,0), Larger_tent_temperature numeric(3,1), Littler_tent_relative_humidity numeric(3,0), Littler_tent_temperature numeric(3,1), Greenhouse_relative_humidity numeric(3,0), Greenhouse_temperature numeric(3,1), weather jsonb);
```
Reading_nr is optional, as is weather. There's one column per sensor and the names need to match sensor names in config.ini. 

There's a timezone aware timestamp column as ow-tenter will include a UTC timestamp to mark the time of the readings. UTC avoids any ambiguity about the locale/timezone ow-tenter runs in. 

### Installing
After cloning this repository, in a venv or not, to install dependencies:
```
pip install -r requirements.txt

```
Edit **config.ini** with your environment information.


Therafter the script can be run:
```
python3 ow-tenter.py
```
or
```
python ow-tenter.py
```
if that invokes Python3. If there's no visible output then it has probably run successfully : ) 
You can check your db table.




## Deployment

The script makes the most sense running on a schedule in order to save a time series of data.
Cron or systemd or Windows scheduler can be employed. I found https://jeetblogs.org/post/scheduling-jobs-with-systemd/ useful for Raspbian.


Something to visualize the collected data might be constructed, I've employed a tiny c3 js page querying the database via a small flask api running via mod_wsgi in an apache2 instance.


## Code style

The code mostly follows pep8 except 'line too long' and 'line break before binary operator'. I typically write on a standard desktop wide screen and think that line breaks before binary operators looks nice : )

## Contributing
Do create an issue for a feature request, bug report, comment or preceding a PR.

## License
See [LICENSE](LICENSE)

## Credits
Two stackoverflow threads with working answers on how to create a dynamic insert into(any number of values/columns) with psycopg2:

https://stackoverflow.com/questions/55814077/psycopg2-dynamic-table-columns-and-values 
https://stackoverflow.com/questions/41999354/inserting-rows-into-db-from-a-list-of-tuples-using-cursor-mogrify-gives-error/41999884#41999884
