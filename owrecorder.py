from configparser import ConfigParser
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import pyownet

import psycopg
from psycopg import sql


class Owrecorder:
    def __init__(self):
        self.config = ConfigParser()
        if not self.config.read(
            f'{Path( __file__ ).parent.joinpath("config.ini")}'
        ):
            raise RuntimeError("config.ini not found")

    def read_owsensors(self) -> dict:  # {sensor_name : read_value}
        try:
            owproxy = pyownet.protocol.proxy(
                host=self.config["owserver"]["Host"],
                port=self.config["owserver"]["Port"],
                persistent=False,  # if a sensor is tempor. unavail. when the proxy is created with persistence it seems to remain so
            )
        except pyownet.protocol.ConnError as error:
            raise RuntimeError(
                f"there was a problem connecting to the specified owserver: {error.args}\n"
            ) from error

        sensors = self.config.items("owsensors")
        retry_seconds = int(self.config.items("owretry")[0][1])
        readings = {}
        failures = []

        def format_reading(sensor, reading):
            if sensor[0].endswith("_temperature"):
                readings[sensor[0]] = round(float(reading.decode("utf-8").strip()), 1)
            else:
                readings[sensor[0]] = round(float(reading.decode("utf-8").strip()))

        def read_sensor(sensor):
            reading = None
            try:
                reading = owproxy.read(sensor[1])
            except pyownet.protocol.OwnetError as error:
                print(
                    f"{datetime.now()}: failed to read {sensor[0]}: {error.args}"
                )  # always indicate when sensor failed to be read
            return reading

        def iterate_sensor_reads(sensors, are_failures=False):
            for sensor in sensors:
                reading = read_sensor(sensor)
                if reading is not None:
                    format_reading(sensor, reading)
                if reading is None and not are_failures:
                    failures.append((sensor[0], sensor[1]))

        for times in range(2):
            if times == 0:
                iterate_sensor_reads(sensors)
                if not failures:
                    break

                time.sleep(retry_seconds)

            elif (
                times == 1
            ):  # will only happen if failure to read a sensor has happened
                iterate_sensor_reads(failures, True)

        return [
            readings,
            str(datetime.now(ZoneInfo("UTC"))),
        ]  # for a timezone-aware datetime object rather than UTC specifically

    def save_readings(self, readings) -> None:

        host = self.config["postgresql"]["host"]
        port = self.config["postgresql"]["port"]
        database = self.config["postgresql"]["db"]
        table = self.config["postgresql"]["table"]
        user = self.config["postgresql"]["user"]
        passw = self.config["postgresql"]["pass"]

        with psycopg.connect(
            f"host={host} port={port} dbname={database} user={user} password={passw} connect_timeout=10"
        ) as conn:
            with conn.cursor() as cur:
                mapped_values = readings[0]
                mapped_values["timestamp"] = readings[1]
                columns = mapped_values.keys()

                insert_sql = sql.SQL(
                    "INSERT INTO {table} ({columns}) VALUES ({values})"
                ).format(
                    table=sql.Identifier(table),
                    columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                    values=sql.SQL(", ").join(map(sql.Placeholder, columns)),
                )
                cur.execute(insert_sql, mapped_values)
                conn.commit()


if __name__ == "__main__":
    owrecord = Owrecorder()
    owrecord.save_readings(owrecord.read_owsensors())
