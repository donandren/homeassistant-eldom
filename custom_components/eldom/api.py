from __future__ import annotations
import collections
from dataclasses import dataclass
import datetime
from enum import Enum
import json
from urllib.parse import urlencode, urljoin
import re
from typing import Optional, Type, TypeVar
from requests import Response, Session

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
vtoken_pattern = r'<input\s*name="__RequestVerificationToken".*value="(?P<token>.*)"'
login_request_token_name = "__RequestVerificationToken"


class SessionWithUrlBase(Session):
    def __init__(self, url_base=None, *args, **kwargs):
        super(SessionWithUrlBase, self).__init__(*args, **kwargs)
        self.url_base = url_base

    def request(self, method, url, **kwargs):
        modified_url = urljoin(self.url_base, url)
        return super(SessionWithUrlBase, self).request(method, modified_url, **kwargs)


@dataclass
class User:
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = None
    alert_email: Optional[str] = None
    language: Optional[int] = None
    last_login_date: Optional[datetime.datetime] = None
    last_active_date: Optional[datetime.datetime] = None
    is_active: Optional[bool] = None
    ip: Optional[str] = None


class Mode(Enum):
    OFF = 0
    HEATING = 1
    SMART = 2
    STUDY = 3
    TIMERS = 4


class DeviceType(Enum):
    FLAT_WATER_HEATER = 7


@dataclass
class Device:
    id: int
    real_device_id: str
    device_type: DeviceType
    name: None
    is_owner: Optional[bool] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    hw_version: Optional[int] = None
    sw_version: Optional[int] = None
    users_with_access: Optional[int] = None
    last_data_refresh_date: Optional[datetime.datetime] = None
    time_zone_id: Optional[int] = None
    time_zone_name: Optional[str] = None
    # additional fields
    display_name: Optional[str] = None

    def _init(self):
        if isinstance(self.device_type, int):
            self.device_type = DeviceType(self.device_type)
        self.display_name = (
            data_utils.display_name_from_type(self.device_type)
            if self.name is None or len(self.name) == 0
            else self.name
        )
        if self.display_name is None:
            self.display_name = f"Unknown type:{self.device_type}"


@dataclass
class DeviceState:
    device_id: str
    state: Mode
    type: Optional[DeviceType] = None
    protocol: Optional[int] = None
    manufacturer: Optional[int] = None
    hardware_version: Optional[int] = None
    software_version: Optional[int] = None
    last_refresh_date: Optional[datetime.datetime] = None
    date: Optional[datetime.datetime] = None
    set_temp: Optional[int] = None
    first_cylinder_on: Optional[bool] = None
    second_cylinder_on: Optional[bool] = None
    first_cylinder_active: Optional[bool] = None
    second_cylinder_active: Optional[bool] = None
    first_cylinder_temp: Optional[int] = None
    second_cylinder_temp: Optional[int] = None
    has_boost: Optional[bool] = None
    heater: Optional[bool] = None
    energy_day: Optional[float] = None
    energy_night: Optional[float] = None
    saved_energy: Optional[float] = None
    power_flag: Optional[int] = None
    current_temp: Optional[int] = None
    heating_active: Optional[bool] = None
    energy_total: Optional[float] = None

    def _init(self):
        if isinstance(self.state, int):
            self.state = Mode(self.state)
        if isinstance(self.type, int):
            self.type = DeviceType(self.type)
        match (self.type):
            case DeviceType.FLAT_WATER_HEATER:
                # 0 not active, 4 first, 8 second, 12 both
                self.first_cylinder_active = self.power_flag & 4 > 0
                self.second_cylinder_active = self.power_flag & 8 > 0
        self.heating_active = self.first_cylinder_active or self.second_cylinder_active
        self.energy_total = self.energy_day + self.energy_night
        self.saved_energy_kwh = self.saved_energy / 100.0
        ft = self.first_cylinder_temp
        st = self.second_cylinder_temp
        if ft > 0 and st > 0:
            self.current_temp = (ft + st) / 2
        elif ft > 0:
            self.current_temp = ft
        elif st > 0:
            self.current_temp = st

    def __str__(self):
        return (
            f"State: {self.state.name}\nSet temperature: {self.set_temp}\n"
            + f"Powerful: {data_utils.bool_to_str(self.has_boost)} Heating: {data_utils.bool_to_str(self.heater)}\n"
            + f"Energy Consumption R1:{self.energy_day}kWh, R2:{self.energy_night}kWh\n"
            + f"Total:{self.energy_total}kWh, Saved energy: {self.saved_energy_kwh}kWh\n"
            + f"heater: {self.current_temp}℃  {data_utils.bool_to_str(self.heating_active)}\n"
            + f"first heater: {self.first_cylinder_temp}℃  {data_utils.bool_to_str(self.first_cylinder_active)}\n"
            + f"second heater: {self.second_cylinder_temp}℃  {data_utils.bool_to_str(self.second_cylinder_active)}\n"
            + f"Date:{str(self.date)}"
        )


class data_utils:
    U = TypeVar("U")
    _mappings: dict = {
        User: dict(
            id="id",
            email="email",
            first_name="firstName",
            last_name="lastName",
            is_admin="IsAdmin",
            language="language",
            last_login_date="lastLoginDate",
            last_active_date="lastActiveDate",
            is_active="isActive",
            ip="ip",
        ),
        Device: dict(
            id="id",
            real_device_id="realDeviceId",
            device_type="deviceType",
            name="name",
            is_owner="isOwner",
            owner_id="ownerId",
            owner_name="ownerName",
            hw_version="hwVersion",
            sw_version="swVersion",
            users_with_access="usersWithAccess",
            last_data_refresh_date="lastDataRefreshDate",
            time_zone_id="timeZoneId",
            time_zone_name="timeZoneName",
        ),
        DeviceState: dict(
            device_id="DeviceID",
            state="State",
            type="Type",
            protocol="Protocol",
            manufacturer="Manifactor",
            hardware_version="HardwareVersion",
            software_version="SoftwareVersion",
            last_refresh_date="LastRefreshDate",
            date="Date",
            set_temp="SetTemp",
            first_cylinder_on="FirstCylinderOn",
            second_cylinder_on="SecondCylinderOn",
            first_cylinder_temp="FT_Temp",
            second_cylinder_temp="STL_Temp",
            has_boost="HasBoost",
            heater="Heater",
            energy_day="EnergyD",
            energy_night="EnergyN",
            saved_energy="SavedEnergy",
            power_flag="PowerFlag",
        ),
    }

    _display_names = {DeviceType.FLAT_WATER_HEATER: "Flat water heater"}

    @staticmethod
    def bool_to_str(value: bool):
        if value is None:
            return "Unknown"
        return "ON" if value is True else "OFF"

    @staticmethod
    def display_name_from_type(type: DeviceType) -> str:
        return data_utils._display_names[type]

    @staticmethod
    def _init(obj):
        if hasattr(obj, "_init") and callable(obj._init):
            obj._init()
        return obj

    @staticmethod
    def _value(value):
        if isinstance(value, Enum):
            return value.value
        return value

    @staticmethod
    def from_json(content: str, cls: Type[U]) -> U:
        kvs = json.loads(content)
        if isinstance(kvs, (collections.abc.Sequence)):
            res = []
            if cls.__origin__ == list:
                cls = cls.__args__[0]
            type_mappings = data_utils._mappings[cls]
            for item in kvs:
                p = {}
                for k, v in type_mappings.items():
                    if v in item:
                        p[k] = item[v]
                res.append(data_utils._init(cls(**p)))
            return res
        else:
            p = {}
            type_mappings = data_utils._mappings[cls]
            for k, v in type_mappings.items():
                if v in kvs:
                    p[k] = kvs[v]
            return data_utils._init(cls(**p))

    @staticmethod
    def to_json(obj) -> str:
        if isinstance(obj, (collections.abc.Sequence)):
            type_mappings = None
            res = []
            for item in obj:
                r = {}
                type_mappings = (
                    type_mappings
                    if type_mappings is not None
                    else data_utils._mappings[type(item)]
                )
                for name, value in vars(item).items():
                    if name in type_mappings:
                        r[type_mappings[name]] = data_utils._value(value)
                res.append(r)
            return json.dumps(res)
        else:
            r = {}
            type_mappings = data_utils._mappings[type(obj)]
            for name, value in vars(obj).items():
                if name in type_mappings:
                    r[type_mappings[name]] = data_utils._value(value)
            return json.dumps(r)


class EldomAPI:
    """
    Eldom API client need to have success login to be able to operate with devices
    """

    _session: Session
    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        """init"""
        self._endpoint = endpoint
        self._session = SessionWithUrlBase(url_base=endpoint)

    def login(self, user: str, password: str) -> bool:
        self._session.headers.update(
            {"User-Agent": user_agent, "Referer": self._endpoint + "/"}
        )
        res = self._session.get("/Account/Login")
        content = str(res.content)

        result = re.search(vtoken_pattern, content)

        if not result or not result.groupdict().get("token"):
            raise RuntimeError("Failed to start login procedure ...")

        token = result.groupdict().get("token")

        login_data = urlencode(
            {"Email": user, "Password": password, "__RequestVerificationToken": token}
        )

        self._session.headers.update({"Referer": res.request.url})

        res = self._session.post(
            "/Account/Login",
            data=login_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        # valid login should return cookie
        auth_cookie = self._session.cookies.get(".AspNetCore.cookieath")

        self._session.headers.update(
            {"Referer": res.headers.get("Location", res.request.url)}
        )
        next_res = self._session.get("/")

        self._session.headers.update({"Referer": next_res.request.url})

        return res.ok and auth_cookie is not None

    def get_user(self) -> User:
        res = self._session.get("/api/user/get")
        return data_utils.from_json(res.content, User)

    def get_devices(self):
        res = self._session.get("/api/device/getmy")
        return data_utils.from_json(res.content, list[Device])

    def get_device(self, id):
        res = self._session.post(
            "/api/device/getmydevice", json.dumps({"deviceId": id})
        )
        return data_utils.from_json(res.content, Device)

    def get_state(self, device: Device):
        res = self._session.get(f"/api/flatboiler/{device.id}")
        return data_utils.from_json(json.loads(res.content)["objectJson"], DeviceState)

    def set_temperature(self, device: Device, temperature: int):
        """set temperature 35-75"""
        if temperature < 35:
            raise ValueError(f"temperature is too low (<35):{temperature}")
        if temperature > 75:
            raise ValueError(f"temperature is too high (>75):{temperature}")

        res = self._session.post(
            "/api/flatboiler/setTemperature",
            data=json.dumps(
                {"deviceId": device.real_device_id, "temperature": temperature}
            ),
            headers={
                "Content-Type": "application/json",
            },
        )
        self._ensure_success(res, f"Failed to set temperature to {temperature}!")

    def set_power_boost(self, device: Device, boost: bool):
        res = self._session.post(
            "/api/flatboiler/setHeater",
            data=json.dumps({"deviceId": device.real_device_id, "heater": boost}),
            headers={
                "Content-Type": "application/json",
            },
        )
        self._ensure_success(res, f"Failed to set power boost to {boost}!")

    def set_state(self, device: Device, state: Mode):
        res = self._session.post(
            "/api/flatboiler/setState",
            data=json.dumps({"deviceId": device.real_device_id, "state": state.value}),
            headers={
                "Content-Type": "application/json",
            },
        )
        self._ensure_success(res, f"Failed to set state to {state.name}!")

    def _ensure_success(self, res: Response, message: str):
        content = json.loads(res.content)
        if content["status"] is not True:
            status = content["statusMessage"]
            error = f"{message}{status if status is not None else ''}"
            raise RuntimeError(error)
