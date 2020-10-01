import sys
import os
from time import sleep
import configparser
import pendulum
import json
import psycopg2
from psycopg2 import sql
import requests
import pyownet
import smtplib
import socket
from email.message import EmailMessage
from email.headerregistry import Address


class Owtenter:
    # Init by attempting to read config.ini in this folder,
    # save as instance variable
    def __init__(self):
        self.config = configparser.ConfigParser()
        if (os.path.exists(
            os.path.join(os.path.abspath(
                os.path.dirname(__file__)), "config.ini")
        )):
            self.config.read(
                os.path.join(os.path.abspath(
                    os.path.dirname(__file__)), "config.ini")
            )
        else:
            print(
                "Unable to read config.ini, please verify that it resides "
                + "in the same folder as ow-tenter.py."
            )
            sys.exit(1)

    # main
    def run(self):
        if (self.config.has_option("weather", "OpenWeatherMapAPICall")):
            try:
                self.save(*self.read_ow(), self.weather())
            except TypeError as e:
                print("Encountered a problem: " + str(e) + " Ow-tenter is exiting.")
                sys.exit(1)
        else:
            try:
                self.save(*self.read_ow())
            except TypeError as e:
                print("Encountered a problem: " + str(e) + " Ow-tenter is exiting.")
                sys.exit(1)

    def read_ow(self):
        try:
            owproxy = pyownet.protocol.proxy(
                host=self.config["owserver"]["Host"],
                port=self.config["owserver"]["Port"],
                persistent=False,
            )
        except pyownet.protocol.ConnError as e:
            print("An error occurred while trying to establish a connection to the ow network: {}\nThe ow error occurred at: {}\n".format(e, pendulum.now().to_datetime_string()))
            sys.exit(1)

        # Read ow sensors section of config and save as dict
        # id as key and path as value
        sensors_dict = dict(self.config.items("owsensors"))

        # redefine values of dict from sensor path to read value
        for key, value in sensors_dict.items():
            if (key.endswith("_humidity")):  # rh sensor by naming design
                try:
                    sensors_dict[key] = round(
                        float(
                            owproxy.read(self.config["owsensors"][key])
                            .decode("utf-8")
                            .strip()
                        )
                    )
                except pyownet.protocol.OwnetError as e:
                    print("Sensor unreachable: " + str(e) + ", the date is: "
                          + pendulum.now().to_datetime_string())

            elif (key.endswith("_temperature")):
                try:
                    sensors_dict[key] = round(
                        float(
                            owproxy.read(self.config["owsensors"][key])
                            .decode("utf-8")
                            .strip()
                        ),
                        1,
                    )
                except pyownet.protocol.OwnetError as e:
                    print("Sensor unreachable: " + str(e) + ", the date is: "
                          + pendulum.now().to_datetime_string())

        # Don't continue if no sensors were read
        if (not sensors_dict):
            print("No sensors were successfully read, exiting.")
            sys.exit(1)

        # Mark time after all sensors have been read
        timestamp = pendulum.now("UTC")
        # Check whether values are outside of configured limits
        self._thresholds(sensors_dict)
        # Return them for saving in the db either way
        return [sensors_dict, timestamp]

    def _thresholds(self, sensors_dict):
        # Read any thresholds for the given sensors
        thresholds_dict = dict(self.config.items("thresholds"))
        warnings = {}

        for sensor, reading in sensors_dict.items():
            threshold = thresholds_dict.get(sensor + "_upper")
            if (threshold is not None):
                try:
                    if float(reading) > float(threshold):
                        warnings[sensor] = reading
                except ValueError:
                    print("One threshold check failed due to a threshold or sensor reading value format error.")

            threshold = thresholds_dict.get(sensor + "_lower")
            if (threshold is not None):
                try:
                    if float(reading) < float(threshold):
                        warnings[sensor] = reading
                except ValueError:
                    print("One threshold check failed due to a threshold or sensor reading value format error.")

        if (warnings):
            print("Threshold crossed, attempting to email")
            print(warnings)
            self._email(warnings)

    def weather(self):
        # Returns the variable OpenWeatherMap data for a city
        for i in range(2):
            response = requests.get(
                self.config["weather"]["OpenWeatherMapAPICall"])
            if (not response.status_code == 200):
                if i > 0:
                    # second attempt failed, return error as json
                    return json.dumps({"issue": "openweathermap service availability issue"})
                else:
                    print(
                        "First Openweathermap api call attempt failed, making one more attempt in nine seconds. The date is: "
                        + pendulum.now().to_datetime_string()
                        + "\n"
                    )
                    sleep(9)
            else:
                break  # response http status is 200 and the for loop breaks

        response = response.json()
        custom_weather_response = {}

        try:
            custom_weather_response["description"] = response["weather"][0]["description"]
            custom_weather_response["temp"] = response["main"]["temp"]
            custom_weather_response["humidity"] = response["main"]["humidity"]
            custom_weather_response["pressure"] = response["main"]["pressure"]
            custom_weather_response["visibility"] = response["visibility"]
            custom_weather_response["clouds"] = response["clouds"]["all"]
            custom_weather_response["windspeed"] = response["wind"]["speed"]
        except KeyError:
            print(
                "Weather's schema has changed. Local datetime: "
                + pendulum.now().to_datetime_string()
                + "\n"
            )
            return json.dumps({"issue": "openweathermap schema change"})

        return json.dumps(custom_weather_response)

    def save(self, ow_readings, timestamp, weather=None):
        # Saves read values, timestamp and possibly weather
        # in configured db table

        # Remove readings that have not resulted in numerals
        for key, presumed_numeral in list(ow_readings.items()):
            try:
                float(presumed_numeral)
            except ValueError:
                del ow_readings[key]

        try:
            connection = psycopg2.connect(
                dbname=self.config["postgresql"]["DB"],
                user=self.config["postgresql"]["User"],
                host=self.config["postgresql"]["Host"],
                port=self.config["postgresql"]["Port"],
                password=self.config["postgresql"]["Pass"],
            )
        except psycopg2.Error as e:
            print(e)
            sys.exit(1)
        else:
            if (weather is not None):
                ow_readings["weather"] = weather

            ow_readings["timestamp"] = timestamp

            insert_table = self.config["postgresql"]["table"]

            columns = list(ow_readings.keys())
            values = [(tuple(ow_readings.values()))]

            insert_sql = sql.SQL("insert into {} ({}) values {}").format(
                sql.Identifier(insert_table),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(values)))

            cursor = connection.cursor()
            # print(cursor.mogrify(insert_sql, values))
            cursor.execute(insert_sql, values)
            connection.commit()
            connection.close()

    def _email(self, warnings):
        # (try to) email warning with sensor ids and values past thresholds

        if (self.config.has_option("international", "Temperature_scale_symbol")):
            temp_scale = self.config["international"]["Temperature_scale_symbol"]
        else:
            temp_scale = "C"

        warning_string = ""

        for sensor, reading in warnings.items():
            if (sensor.endswith("_temperature")):
                sensor = sensor.rsplit("_", 1)[0]
                warning_string += "The sensor '{}' reports a temperature of {} {}\
                    \n".format(sensor, reading, temp_scale)

            elif (sensor.endswith("_humidity")):
                sensor = sensor.rsplit("_", 2)[0]
                warning_string += "The sensor '{}' reports a relative humidity of {}%\
                    \n".format(sensor, reading)

        email = EmailMessage()

        to_address = Address(
            display_name=self.config["mail"]["ToName"],
            username=self.config["mail"]["ToUserName"],
            domain=self.config["mail"]["ToDomain"],
        )

        email["From"] = self.config["mail"]["FromMailAddress"]
        email["To"] = to_address
        email["Subject"] = self.config["mail"]["Subject"]
        email.set_content(warning_string)

        try:
            s = smtplib.SMTP(host=self.config["mail"]["Host"], port=self.config["mail"]["Port"])
            s.ehlo()
            s.starttls()
            s.login(self.config["mail"]["FromMailAddress"],
                    self.config["mail"]["Pass"])
            s.send_message(email)
            s.quit()
        except socket.error as e:        
            print("An error occurred while attempting to email a sensor alert: {}\nThe email error occurred at: {}\n".format(e, pendulum.now().to_datetime_string()))
            return
        except Exception as e:
            print("Another error of type: ", e.__class__, "occurred while attempting to email a sensor alert.")
            return




if (__name__ == "__main__"):
    ow_tenter = Owtenter()
    ow_tenter.run()
