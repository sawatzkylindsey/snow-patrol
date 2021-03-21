
import datetime as dt
import json


class Config:
    def __init__(self, darksky_key, textbelt_key, location, latitude, longitude, name, phone_number):
        self.darksky_key = darksky_key
        self.textbelt_key = textbelt_key
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
        self.phone_number = phone_number

    def __repr__(self):
        ds = self.darksky_key[:6]
        tb = self.textbelt_key[:6]
        return "Config{ds=%s.., tb=%s.., loc=%s, lat=%.4f, long=%.4f, name=%s, phone=%s}" % \
            (ds, tb, self.location, self.latitude, self.longitude, self.name, self.phone_number)


def load(config_path):
    with open(config_path, "r") as fh:
        return Config(**json.load(fh))


class PrecipitationEvent:
    def __init__(self, time, darksky_point):
        self.time = time
        self.probability = darksky_point.precip_probability
        self.intensity = darksky_point.precip_intensity
        self.type = darksky_point.precip_type
        self.accumulation = darksky_point.precipAccumulation

    def is_snowing(self):
        print(self)
        return (self.probability >= 0.5 \
                or self.intensity >= 0.2 \
                or (self.accumulation is not None and self.accumulation >= 0.15)) \
            and self.type == "snow"

    def __repr__(self):
        precipitation = "none"

        if self.type is not None:
            suffix = "" if self.accumulation is None else "%scm of " % self.accumulation
            precipitation = "%s%s, p=%.4f, i=%.4f" % (suffix, self.type, self.probability, self.intensity)

        return "PrecipitationPoint{%s, %s}" % (self.time.isoformat(timespec="seconds"), precipitation)


class ArtificialPoint:
    def __init__(self, precip_probability, precip_intensity, precip_type, precip_accumulation):
        self.precip_probability = precip_probability
        self.precip_intensity = precip_intensity
        self.precip_type = precip_type
        self.precipAccumulation = precip_accumulation

