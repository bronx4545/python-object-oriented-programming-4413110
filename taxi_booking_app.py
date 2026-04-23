"""Simple OOP taxi booking application (Uber/Yandex style).

This module demonstrates an object-oriented design for a taxi-hailing platform.
Run directly to see a full demo flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from math import sqrt
from typing import Dict, List, Optional


class RideStatus(Enum):
    REQUESTED = auto()
    ACCEPTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class Location:
    x: float
    y: float

    def distance_to(self, other: "Location") -> float:
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class User:
    user_id: str
    name: str
    phone: str


@dataclass
class Rider(User):
    wallet_balance: float = 0.0

    def add_funds(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.wallet_balance += amount


@dataclass
class Driver(User):
    car_model: str
    car_number: str
    current_location: Location
    is_available: bool = True
    rating: float = 5.0


@dataclass
class Ride:
    ride_id: str
    rider: Rider
    pickup: Location
    dropoff: Location
    requested_at: datetime = field(default_factory=datetime.utcnow)
    driver: Optional[Driver] = None
    status: RideStatus = RideStatus.REQUESTED
    fare: float = 0.0

    @property
    def distance_km(self) -> float:
        return self.pickup.distance_to(self.dropoff)


class FareCalculator:
    """Dynamic fare model using base + distance + surge pricing."""

    def __init__(self, base_fare: float = 2.0, per_km_rate: float = 1.2) -> None:
        self.base_fare = base_fare
        self.per_km_rate = per_km_rate

    def calculate(self, distance_km: float, active_rides: int, available_drivers: int) -> float:
        if distance_km <= 0:
            return 0.0

        demand_supply_ratio = (
            active_rides / available_drivers if available_drivers > 0 else 3.0
        )
        surge = 1.0 if demand_supply_ratio <= 1 else min(2.5, 1 + demand_supply_ratio / 3)

        fare = (self.base_fare + (distance_km * self.per_km_rate)) * surge
        return round(fare, 2)


class BookingSystem:
    def __init__(self) -> None:
        self.riders: Dict[str, Rider] = {}
        self.drivers: Dict[str, Driver] = {}
        self.rides: Dict[str, Ride] = {}
        self._ride_counter = 1000
        self.fare_calculator = FareCalculator()

    def register_rider(self, rider: Rider) -> None:
        self.riders[rider.user_id] = rider

    def register_driver(self, driver: Driver) -> None:
        self.drivers[driver.user_id] = driver

    def _generate_ride_id(self) -> str:
        self._ride_counter += 1
        return f"RIDE-{self._ride_counter}"

    def _available_drivers(self) -> List[Driver]:
        return [driver for driver in self.drivers.values() if driver.is_available]

    def _find_nearest_driver(self, pickup: Location) -> Optional[Driver]:
        available = self._available_drivers()
        if not available:
            return None
        return min(available, key=lambda d: d.current_location.distance_to(pickup))

    def request_ride(self, rider_id: str, pickup: Location, dropoff: Location) -> Ride:
        if rider_id not in self.riders:
            raise KeyError("Rider not found")

        rider = self.riders[rider_id]
        driver = self._find_nearest_driver(pickup)
        if not driver:
            raise RuntimeError("No drivers available right now")

        active_rides = sum(
            1 for ride in self.rides.values() if ride.status in {RideStatus.ACCEPTED, RideStatus.IN_PROGRESS}
        )
        fare = self.fare_calculator.calculate(
            distance_km=pickup.distance_to(dropoff),
            active_rides=active_rides,
            available_drivers=len(self._available_drivers()),
        )

        ride = Ride(
            ride_id=self._generate_ride_id(),
            rider=rider,
            pickup=pickup,
            dropoff=dropoff,
            driver=driver,
            status=RideStatus.ACCEPTED,
            fare=fare,
        )

        driver.is_available = False
        self.rides[ride.ride_id] = ride
        return ride

    def start_ride(self, ride_id: str) -> None:
        ride = self.rides[ride_id]
        if ride.status != RideStatus.ACCEPTED:
            raise RuntimeError("Ride must be accepted before starting")
        ride.status = RideStatus.IN_PROGRESS

    def complete_ride(self, ride_id: str) -> None:
        ride = self.rides[ride_id]
        if ride.status != RideStatus.IN_PROGRESS:
            raise RuntimeError("Ride must be in progress before completing")

        if ride.rider.wallet_balance < ride.fare:
            raise RuntimeError("Insufficient wallet balance")

        ride.rider.wallet_balance = round(ride.rider.wallet_balance - ride.fare, 2)
        ride.status = RideStatus.COMPLETED

        if ride.driver:
            ride.driver.is_available = True
            ride.driver.current_location = ride.dropoff


if __name__ == "__main__":
    app = BookingSystem()

    rider = Rider(user_id="U1", name="Alice", phone="+1-555-1001", wallet_balance=50)
    app.register_rider(rider)

    app.register_driver(
        Driver(
            user_id="D1",
            name="Bob",
            phone="+1-555-2001",
            car_model="Toyota Camry",
            car_number="XYZ-123",
            current_location=Location(2, 3),
        )
    )
    app.register_driver(
        Driver(
            user_id="D2",
            name="Eve",
            phone="+1-555-2002",
            car_model="Honda Civic",
            car_number="ABC-456",
            current_location=Location(8, 9),
        )
    )

    ride = app.request_ride("U1", pickup=Location(1, 1), dropoff=Location(10, 10))
    print(f"Ride booked: {ride.ride_id}")
    print(f"Driver: {ride.driver.name if ride.driver else 'N/A'}")
    print(f"Estimated fare: ${ride.fare}")

    app.start_ride(ride.ride_id)
    app.complete_ride(ride.ride_id)

    print(f"Ride status: {ride.status.name}")
    print(f"Remaining rider wallet balance: ${ride.rider.wallet_balance:.2f}")
