from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# -------------------------------
# Data Storage
# -------------------------------

doctors = [
    {"id": 1, "name": "Dr. Sharma", "specialization": "Cardiology", "fees": 500, "is_available": True},
    {"id": 2, "name": "Dr. Khan", "specialization": "Dermatology", "fees": 300, "is_available": True},
    {"id": 3, "name": "Dr. Mehta", "specialization": "Neurology", "fees": 700, "is_available": True},
]

appointments = []
appointment_counter = 1

queue = []

# -------------------------------
# Helper Functions
# -------------------------------

def find_doctor(doctor_id: int):
    for doctor in doctors:
        if doctor["id"] == doctor_id:
            return doctor
    return None

def calculate_fee(fees: int, appointment_type: str):
    if appointment_type == "offline":
        return fees + 100
    return fees

def filter_doctors_logic(specialization, max_fees, is_available):
    result = doctors
    if specialization is not None:
        result = [d for d in result if d["specialization"].lower() == specialization.lower()]
    if max_fees is not None:
        result = [d for d in result if d["fees"] <= max_fees]
    if is_available is not None:
        result = [d for d in result if d["is_available"] == is_available]
    return result

# -------------------------------
# Pydantic Models
# -------------------------------

class AppointmentRequest(BaseModel):
    patient_name: str = Field(min_length=2)
    doctor_id: int = Field(gt=0)
    symptoms: str = Field(min_length=5)
    appointment_time: str
    appointment_type: str = "online"

class NewDoctor(BaseModel):
    name: str = Field(min_length=2)
    specialization: str = Field(min_length=2)
    fees: int = Field(gt=0)
    is_available: bool = True

# -------------------------------
# Day 1 - GET APIs
# -------------------------------

@app.get("/")
def home():
    return {"message": "Welcome to Medical Appointment System"}

@app.get("/doctors")
def get_doctors():
    return {"total": len(doctors), "data": doctors}

@app.get("/appointments")
def get_appointments():
    return {"total": len(appointments), "data": appointments}

@app.get("/doctors/summary")
def doctors_summary():
    available = [d for d in doctors if d["is_available"]]
    unavailable = [d for d in doctors if not d["is_available"]]
    specializations = list(set([d["specialization"] for d in doctors]))
    return {
        "total": len(doctors),
        "available": len(available),
        "unavailable": len(unavailable),
        "specializations": specializations
    }

@app.get("/doctors/filter")
def filter_doctors(
    specialization: Optional[str] = None,
    max_fees: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = filter_doctors_logic(specialization, max_fees, is_available)
    return {"total": len(result), "data": result}

@app.get("/doctors/search")
def search_doctors(keyword: str):
    result = [
        d for d in doctors
        if keyword.lower() in d["name"].lower()
        or keyword.lower() in d["specialization"].lower()
    ]
    if not result:
        return {"message": "No doctors found"}
    return {"total_found": len(result), "data": result}

@app.get("/doctors/sort")
def sort_doctors(sort_by: str = "fees", order: str = "asc"):
    if sort_by not in ["fees", "name"]:
        raise HTTPException(status_code=400, detail="Invalid sort field")
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    reverse = True if order == "desc" else False
    sorted_data = sorted(doctors, key=lambda x: x[sort_by], reverse=reverse)

    return {"data": sorted_data}

@app.get("/doctors/page")
def paginate_doctors(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    end = start + limit
    total = len(doctors)
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "data": doctors[start:end]
    }

@app.get("/doctors/browse")
def browse_doctors(
    keyword: Optional[str] = None,
    sort_by: str = "fees",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = doctors

    if keyword:
        result = [
            d for d in result
            if keyword.lower() in d["name"].lower()
            or keyword.lower() in d["specialization"].lower()
        ]

    reverse = True if order == "desc" else False
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    start = (page - 1) * limit
    return {
        "total": len(result),
        "page": page,
        "data": result[start:start + limit]
    }

# -------------------------------
# GET by ID (keep last)
# -------------------------------

@app.get("/doctors/{doctor_id}")
def get_doctor(doctor_id: int):
    doctor = find_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

# -------------------------------
# Day 2 & 3 - POST + Helpers
# -------------------------------

@app.post("/appointments", status_code=201)
def book_appointment(request: AppointmentRequest):
    global appointment_counter

    doctor = find_doctor(request.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if not doctor["is_available"]:
        queue.append(request.dict())
        return {"message": "Doctor not available, added to queue"}

    total_fee = calculate_fee(doctor["fees"], request.appointment_type)

    appointment = {
        "id": appointment_counter,
        "patient_name": request.patient_name,
        "doctor_id": request.doctor_id,
        "symptoms": request.symptoms,
        "time": request.appointment_time,
        "type": request.appointment_type,
        "total_fee": total_fee
    }

    appointments.append(appointment)
    doctor["is_available"] = False
    appointment_counter += 1

    return appointment

# -------------------------------
# Day 4 - CRUD
# -------------------------------

@app.post("/doctors", status_code=201)
def add_doctor(new_doc: NewDoctor):
    for d in doctors:
        if d["name"].lower() == new_doc.name.lower():
            raise HTTPException(status_code=400, detail="Doctor already exists")

    new_id = max([d["id"] for d in doctors]) + 1
    doctor = {"id": new_id, **new_doc.dict()}
    doctors.append(doctor)
    return doctor

@app.put("/doctors/{doctor_id}")
def update_doctor(
    doctor_id: int,
    fees: Optional[int] = None,
    is_available: Optional[bool] = None
):
    doctor = find_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if fees is not None:
        doctor["fees"] = fees
    if is_available is not None:
        doctor["is_available"] = is_available

    return doctor

@app.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int):
    doctor = find_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctors.remove(doctor)
    return {"message": "Doctor deleted"}

# -------------------------------
# Day 5 - Workflow
# -------------------------------

@app.post("/queue/add")
def add_to_queue(patient_name: str, doctor_id: int):
    doctor = find_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if doctor["is_available"]:
        return {"message": "Doctor is available, no need to queue"}

    queue.append({"patient_name": patient_name, "doctor_id": doctor_id})
    return {"message": "Added to queue"}

@app.get("/queue")
def get_queue():
    return {"queue": queue}

@app.post("/appointments/complete/{appointment_id}")
def complete_appointment(appointment_id: int):
    for appt in appointments:
        if appt["id"] == appointment_id:
            doctor = find_doctor(appt["doctor_id"])
            doctor["is_available"] = True

            for q in queue:
                if q["doctor_id"] == doctor["id"]:
                    queue.remove(q)
                    return {"message": "Appointment completed and next patient assigned"}

            return {"message": "Appointment completed"}

    raise HTTPException(status_code=404, detail="Appointment not found")

# -------------------------------
# Day 6 - Advanced
# -------------------------------

@app.get("/appointments/search")
def search_appointments(patient_name: str):
    result = [
        a for a in appointments
        if patient_name.lower() in a["patient_name"].lower()
    ]
    return {"total": len(result), "data": result}