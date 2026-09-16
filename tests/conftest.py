import pytest

from app import main


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    for collection in (
        main.doctors_db,
        main.patients_db,
        main.appointments_db,
        main.prescriptions_db,
    ):
        collection.clear()

    for ownership in main.ownership_db.values():
        ownership.clear()

    main.seed_demo_data()
    yield

    for collection in (
        main.doctors_db,
        main.patients_db,
        main.appointments_db,
        main.prescriptions_db,
    ):
        collection.clear()

    for ownership in main.ownership_db.values():
        ownership.clear()

    main.seed_demo_data()
